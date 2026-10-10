"""Validate a closed ontology bundle, including evidence and review invariants."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from pydantic import ValidationError

from .models import GraphBundle
from .relationships import RELATIONSHIPS


def validate_bundle(bundle: dict | GraphBundle) -> list[str]:
    """Check structure and graph rules; errors contain locations, never source text."""
    try:
        data = bundle.model_dump(mode="json") if isinstance(bundle, GraphBundle) else bundle
        payload = json.dumps(data, allow_nan=False)
        parsed = GraphBundle.model_validate_json(payload)
    except ValidationError as error:
        return [
            f"schema/{'/'.join(map(str, detail['loc']))}: violates {detail['type']}"
            for detail in error.errors(include_input=False, include_context=False)
        ]
    except (TypeError, ValueError):
        return ["schema/: input must be a finite JSON object"]

    bundle = parsed.model_dump(mode="json")
    relations = RELATIONSHIPS
    errors = []
    nodes = {}
    entity_revisions = set()
    entity_types = {}
    outgoing = defaultdict(list)
    incoming = defaultdict(list)
    edge_ids = set()
    edge_triples = set()
    dedup_keys = set()

    for node in bundle["nodes"]:
        node_id = node["id"]
        if node_id in nodes:
            errors.append(f"{node_id}: duplicate node id")
        nodes[node_id] = node
        key = (node["entity_key"], node["revision"])
        if key in entity_revisions:
            errors.append(f"{node_id}: duplicate logical entity revision")
        entity_revisions.add(key)
        previous_type = entity_types.setdefault(node["entity_key"], node["type"])
        if previous_type != node["type"]:
            errors.append(f"{node_id}: a logical entity cannot change type")

    for edge in bundle["edges"]:
        if edge["id"] in edge_ids:
            errors.append(f"{edge['id']}: duplicate edge id")
        edge_ids.add(edge["id"])
        triple = (edge["type"], edge["source_id"], edge["target_id"])
        if triple in edge_triples:
            errors.append(f"{edge['id']}: duplicate relationship between the same revisions")
        edge_triples.add(triple)
        source = nodes.get(edge["source_id"])
        target = nodes.get(edge["target_id"])
        if source is None or target is None:
            errors.append(f"{edge['id']}: dangling relationship endpoint")
            continue
        outgoing[source["id"]].append(edge)
        incoming[target["id"]].append(edge)
        rule = relations[edge["type"]]
        if source["type"] not in rule.source_types or target["type"] not in rule.target_types:
            errors.append(
                f"{edge['id']}: invalid {source['type']} -> {target['type']} relationship"
            )
        if (
            edge["type"] == "DERIVED_FROM"
            and source["type"] == "Signal"
            and target["type"] != "Evidence"
        ):
            errors.append(f"{edge['id']}: a Signal must derive directly from Evidence")
        if edge["type"] == "SUPERSEDES":
            if source["type"] != target["type"] or source["entity_key"] != target["entity_key"]:
                errors.append(f"{edge['id']}: SUPERSEDES must preserve the logical entity and type")
            if source["revision"] <= target["revision"]:
                errors.append(f"{edge['id']}: SUPERSEDES must point to an older revision")
        if edge["type"] == "COMPETES_WITH" and source["id"] == target["id"]:
            errors.append(f"{edge['id']}: a model cannot compete with itself")
        if edge["type"] in {"DERIVED_FROM", "SUPPORTS", "CHALLENGES", "JUSTIFIED_BY", "ADDRESSES"}:
            source_context = source["properties"].get("context")
            target_context = target["properties"].get("context")
            if source_context and target_context:
                transferred = any(
                    set(source_context[key]) != set(target_context[key])
                    for key in ("vehicle_model_ids", "market_ids")
                )
                if transferred and not edge["context_transfer"]:
                    errors.append(f"{edge['id']}: scope transfer requires an explicit explanation")

    def targets(node_id, relation):
        return [
            nodes[e["target_id"]]
            for e in outgoing[node_id]
            if e["type"] == relation and e["target_id"] in nodes
        ]

    def sources(node_id, relation):
        return [
            nodes[e["source_id"]]
            for e in incoming[node_id]
            if e["type"] == relation and e["source_id"] in nodes
        ]

    def reaches_evidence(node_id, active=None):
        active = set() if active is None else active
        if node_id in active:
            return False
        node = nodes[node_id]
        if node["type"] == "Evidence":
            return len(targets(node_id, "IN_SOURCE")) == 1
        if node["type"] == "Signal":
            inputs = targets(node_id, "DERIVED_FROM")
        elif node["type"] == "Trend":
            inputs = targets(node_id, "DERIVED_FROM")
        elif node["type"] == "CustomerNeed":
            inputs = sources(node_id, "SUPPORTS")
        else:
            return False
        return bool(inputs) and all(reaches_evidence(n["id"], active | {node_id}) for n in inputs)

    for node in nodes.values():
        node_id, kind, props = node["id"], node["type"], node["properties"]
        context = props.get("context")
        if context:
            for field, expected_type in (
                ("vehicle_model_ids", "VehicleModel"),
                ("market_ids", "Market"),
            ):
                for reference in context[field]:
                    if reference not in nodes or nodes[reference]["type"] != expected_type:
                        errors.append(f"{node_id}: invalid {field} reference {reference}")
            if context["as_of"] and context["as_of"] > bundle["as_of"]:
                errors.append(f"{node_id}: context date is after bundle as_of")

        if kind == "SourceDocument":
            if bundle["purpose"] != "fixture" and props["origin"] == "synthetic":
                errors.append(f"{node_id}: synthetic sources are allowed only in fixtures")
            if props["publication_date"]:
                try:
                    value = props["publication_date"]
                    suffix = {4: "-01-01", 7: "-01", 10: ""}[len(value)]
                    date.fromisoformat(value + suffix)
                except ValueError:
                    errors.append(f"{node_id}: invalid publication date")

        if kind == "Evidence":
            if len(targets(node_id, "IN_SOURCE")) != 1:
                errors.append(f"{node_id}: Evidence needs exactly one IN_SOURCE relationship")
            if props["dedup_key"] in dedup_keys:
                errors.append(
                    f"{node_id}: duplicate Evidence dedup_key; preserve classifications on one record"
                )
            dedup_keys.add(props["dedup_key"])
            measurement = props["measurement"]
            if measurement:
                statistic, value = measurement["statistic"], measurement["value"]
                if statistic == "proportion" and not 0 <= value <= 1:
                    errors.append(f"{node_id}: proportion must be in [0, 1]")
                if statistic == "percent" and not 0 <= value <= 100:
                    errors.append(f"{node_id}: percent must be in [0, 100]")
                if statistic == "count" and (value < 0 or int(value) != value):
                    errors.append(f"{node_id}: count must be a nonnegative integer")
                scale = measurement["scale"]
                if scale and (
                    scale["minimum"] >= scale["maximum"]
                    or not scale["minimum"] <= value <= scale["maximum"]
                ):
                    errors.append(f"{node_id}: invalid measurement scale or value outside scale")
                period = measurement["period"]
                if period:
                    if period["start"] and period["end"] and period["start"] > period["end"]:
                        errors.append(f"{node_id}: period starts after it ends")
                    future = (period["start"] and period["start"] > bundle["as_of"]) or (
                        period["label"].isdigit()
                        and len(period["label"]) == 4
                        and int(period["label"]) > int(bundle["as_of"][:4])
                    )
                    if future and measurement["temporal_status"] == "historical":
                        errors.append(f"{node_id}: future measurements cannot be historical")

        if kind in {"Signal", "Trend", "CustomerNeed"} and not reaches_evidence(node_id):
            errors.append(f"{node_id}: missing or cyclic evidence chain")

        if kind == "Signal":
            allowed_sources = {
                "customer_feedback": {"feedback_dataset"},
                "public_sentiment": {"public_discussion", "editorial_review"},
                "competitor_capability": {
                    "competitor_official",
                    "editorial_review",
                    "product_catalog",
                },
                "trend_indicator": {"industry_report", "global_indicator", "editorial_review"},
            }
            for evidence in targets(node_id, "DERIVED_FROM"):
                if evidence["type"] != "Evidence":
                    continue
                for source in targets(evidence["id"], "IN_SOURCE"):
                    if (
                        source["type"] == "SourceDocument"
                        and source["properties"]["source_kind"]
                        not in allowed_sources[props["signal_kind"]]
                    ):
                        errors.append(f"{node_id}: source kind does not match signal kind")
            if props["signal_kind"] == "competitor_capability" and not context["vehicle_model_ids"]:
                errors.append(f"{node_id}: competitor capability needs a model reference")

        if kind == "Trend":
            if props["horizon"]["from_year"] > props["horizon"]["to_year"]:
                errors.append(f"{node_id}: invalid trend horizon")
            if props["temporal_status"] in {"forecast", "mixed"} and not targets(
                node_id, "DEPENDS_ON"
            ):
                errors.append(f"{node_id}: projected Trend needs an explicit Assumption")

        if kind == "Requirement":
            if not context["vehicle_model_ids"] or not context["market_ids"]:
                errors.append(f"{node_id}: Requirement needs baseline models and target markets")
            for model_id in context["vehicle_model_ids"]:
                model = nodes.get(model_id)
                if (
                    model
                    and model["type"] == "VehicleModel"
                    and model["properties"]["brand"].casefold() != "bmw"
                ):
                    errors.append(f"{node_id}: successor baseline must be a BMW model")
            needs, justifications = targets(node_id, "ADDRESSES"), targets(node_id, "JUSTIFIED_BY")
            if not needs or not all(reaches_evidence(n["id"]) for n in needs):
                errors.append(f"{node_id}: Requirement must address an evidenced CustomerNeed")
            if not justifications or not all(reaches_evidence(n["id"]) for n in justifications):
                errors.append(f"{node_id}: Requirement needs traceable justifications")
            if not targets(node_id, "DEPENDS_ON"):
                errors.append(f"{node_id}: successor proposal needs a forward-looking Assumption")
            for criterion in props["acceptance_criteria"]:
                if criterion["target"] is not None and any(
                    criterion[field] is None for field in ("metric", "operator", "unit")
                ):
                    errors.append(f"{node_id}: numeric criterion needs metric, operator, and unit")
                if (
                    criterion["basis"] == "evidence_supported_target"
                    and not criterion["supporting_evidence_ids"]
                ):
                    errors.append(f"{node_id}: evidence-supported target needs explicit evidence")
                for evidence_id in criterion["supporting_evidence_ids"]:
                    if evidence_id not in nodes or nodes[evidence_id]["type"] != "Evidence":
                        errors.append(f"{node_id}: invalid criterion evidence reference")
                if (
                    criterion["basis"] == "human_set_target"
                    and props["provenance"]["actor_type"] != "human"
                ):
                    errors.append(f"{node_id}: human-set target requires recorded human authorship")

        if kind == "Decision":
            reviewed = targets(node_id, "REVIEWS")
            if len(reviewed) != 1:
                errors.append(f"{node_id}: Decision must review exactly one Requirement")
            elif props["requirement_revision"] != reviewed[0]["revision"]:
                errors.append(f"{node_id}: Decision targets the wrong requirement revision")
            elif reviewed[0]["type"] == "Requirement" and datetime.fromisoformat(
                props["decided_at"].replace("Z", "+00:00")
            ) < datetime.fromisoformat(
                reviewed[0]["properties"]["provenance"]["created_at"].replace("Z", "+00:00")
            ):
                errors.append(f"{node_id}: Decision predates the requirement revision")
            if (props["action"] == "set_priority") != (props["priority"] is not None):
                errors.append(f"{node_id}: priority is required only for set_priority")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundles", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.bundles:
        try:
            bundle = json.loads(path.read_text(encoding="utf-8"))
            errors = validate_bundle(bundle)
        except (OSError, ValueError) as error:
            errors = [f"{type(error).__name__}: could not read a JSON bundle"]
        if errors:
            failed = True
            print(f"INVALID {path}")
            for error in errors:
                print(f"  {error}")
        else:
            print(
                f"VALID {path}: {len(bundle['nodes'])} nodes, {len(bundle['edges'])} relationships"
            )
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
