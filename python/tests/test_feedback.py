import pytest

from bmwow.agent.config import get_settings
from bmwow.agent.models.evidence import AnalysisRequest
from bmwow.agent.nodes import feedback
from bmwow.agent.nodes.common import AgentContext
from bmwow.agent.resolve import resolve_request
from bmwow.agent.rules import feature_for_term, is_generic_term
from bmwow.agent.stats import wilson_interval
from bmwow.agent.taxonomy import load_taxonomy
from bmwow.agent.tools.feedback_stats import exact_dedupe
from bmwow.knowledge import KnowledgeUnavailableError
from tests.fakes import ontology as fake_ontology
from tests.fakes.data import OPEN_TOPIC, REF_CODE
from tests.fakes.data import feedback as fake_feedback


async def run_feedback(regions=("EU", "CN")):
    brief = await resolve_request(AnalysisRequest(model_code=REF_CODE, regions=list(regions)))
    ctx = AgentContext("feedback", brief, await load_taxonomy())
    await feedback.run(ctx)
    return ctx.build_report(), brief


def items_by_id():
    return {i.item_id: i for i in exact_dedupe(fake_feedback())}


def find(report, attribute, direction, region):
    return next(
        (
            f
            for f in report.findings
            if f.attribute == attribute and f.direction == direction and f.region == region
        ),
        None,
    )


def test_interim_feature_mapping():
    assert feature_for_term("Electric Range") == "real_world_range"
    assert feature_for_term("Seating, ventilate / heat") == "seat_ventilation"
    assert feature_for_term("Level 2 charging speed") == "fast_charging"
    assert feature_for_term("Seats") is None and is_generic_term("Seats")
    assert is_generic_term("Body equipment, overall technology")
    assert feature_for_term("Appearance") is None  # "app" matches whole words only


async def test_counts_distinct_items_against_the_relevant_population():
    report, brief = await run_feedback()
    items = items_by_id()
    eu = set(brief.region_markets["EU"])
    electrified = [i for i in items.values() if i.market in eu and i.engine_type in {"BEV", "PHEV"}]
    complaining = [
        i
        for i in electrified
        if any(a.aspect_term in {"Electric Range", "Range in winter"} for a in i.aspects)
    ]
    f = find(report, "real_world_range", "problem", "EU")
    assert f.stats.n == len(electrified) and f.stats.k == len(complaining)
    assert "BEV+PHEV" in f.stats.denominator_label
    assert f.quantity.value == pytest.approx(f.stats.k / f.stats.n, abs=1e-4)
    assert f.quantity.origin == "computed" and f.weight == pytest.approx(f.stats.k / f.stats.n)
    low, high = wilson_interval(f.stats.k, f.stats.n)
    assert (f.stats.ci_low, f.stats.ci_high) == (round(low, 4), round(high, 4))
    assert f"{f.stats.k} of {f.stats.n}" in f.claim and f.polarity == "negative"
    # all feedback numbers come from code: every source is a feedback item that resolves
    ids = {s.id for s in report.sources}
    assert all(
        sid in ids and sid.startswith("fb:") for g in report.findings for sid in g.source_ids
    )
    assert report.stats["n_after_dedupe"] == report.stats["n_items"] - 5  # planted reposts


async def test_regional_split_and_test_keep_a_cn_only_theme_visible():
    report, _ = await run_feedback()
    cn = find(report, "seat_ventilation", "request", "CN")
    assert cn is not None and find(report, "seat_ventilation", "request", "EU") is None
    assert cn.stats.region_test.other == "EU" and cn.stats.region_test.other_k == 0
    assert cn.stats.region_test.p_value < 0.01
    combined = find(report, "seat_ventilation", "request", None)
    assert combined.stats.k == cn.stats.k and combined.weight < cn.weight
    items = items_by_id()
    assert all(items[sid[3:]].market == "CN" for sid in cn.source_ids)


async def test_single_region_has_no_combined_scope_or_test():
    report, _ = await run_feedback(["EU"])
    assert report.findings and all(f.region == "EU" for f in report.findings)
    assert all(f.stats.region_test is None for f in report.findings)
    assert "seat_ventilation" not in {f.attribute for f in report.findings}


async def test_thin_samples_are_flagged():
    report, _ = await run_feedback()
    for f in report.findings:
        assert f.stats.thin == (f.stats.n < 30 or f.stats.k < 5)
        if f.stats.thin:
            assert f.confidence != "high"


async def test_sub_themes_from_specific_terms_and_from_texts():
    report, _ = await run_feedback()
    by_name = {(t.attribute, t.name): t for t in report.sub_themes}
    vent = by_name[("seat_ventilation", "Seating, ventilate / heat")]
    assert vent.method == "aspect_term" and vent.direction == "request" and vent.k <= vent.of
    # rear-space complaints only carry the generic term "Seats": the LLM groups their texts
    legroom = by_name[("unmapped:seats_comfort", "Rear legroom for passengers")]
    assert legroom.method == "llm" and legroom.direction == "problem"
    assert 2 <= legroom.k <= legroom.of  # counted by code; the digit in the LLM name is stripped
    assert not any(t.name == "Single text" for t in report.sub_themes)  # < 2 texts: dropped
    ids = {s.id for s in report.sources}
    assert all(sid in ids for t in report.sub_themes for sid in t.source_ids)


async def test_llm_sub_themes_stay_off_without_clearance(monkeypatch, fake_env):
    monkeypatch.setenv("ALLOW_LLM_ON_INTERNAL_DATA", "false")
    get_settings.cache_clear()
    report, _ = await run_feedback()
    assert not any(t.method == "llm" for t in report.sub_themes)
    gate = next(a for a in report.availability if a.source == "feedback:sub_themes_llm")
    assert gate.status == "unavailable" and "ALLOW_LLM_ON_INTERNAL_DATA" in gate.reason
    assert not any("what exactly" in p for p in fake_env["analyst"].prompts)
    assert report.status == "ok"


async def test_unclassified_recurring_topic_becomes_a_candidate():
    report, _ = await run_feedback()
    candidate = next(c for c in report.candidates if c.name == OPEN_TOPIC)
    assert candidate.k == 4 and candidate.source_ids
    assert all(c.k >= 3 for c in report.candidates)  # one-off noise is not a candidate
    assert not any("overall" in c.name.lower() for c in report.candidates)


async def test_missing_region_and_missing_backend_are_reported(monkeypatch):
    original = fake_ontology.get_feedback_items
    monkeypatch.setattr(
        fake_ontology,
        "get_feedback_items",
        lambda filters: [i for i in original(filters) if i.market != "CN"],
    )
    report, _ = await run_feedback()
    cn = next(a for a in report.availability if a.source == "feedback:CN")
    assert cn.status == "unavailable" and report.status == "ok"

    def unavailable(filters):
        raise KnowledgeUnavailableError("feedback is not connected")

    monkeypatch.setattr(fake_ontology, "get_feedback_items", unavailable)
    report, _ = await run_feedback()
    assert report.status == "partial" and not report.errors and not report.findings
    assert report.availability[0].source == "feedback"
    assert report.availability[0].status == "unavailable"
