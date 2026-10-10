# BMW product decision ontology

Version 0.1.0 is a portable vocabulary and property-graph contract for deriving customer-facing requirements for a successor BMW vehicle. Python Pydantic models define payloads and generate the JSON Schema; Python relationship rules generate the vocabulary; the validator checks evidence chains and review rules.

This is a practical typed ontology for the hackathon. It is not an OWL/RDF ontology or an implementation of formal logical inference. It can be represented in SQL tables and join tables, a NetworkX graph, or a service's JSON responses.

## Start here

- [JSON Schema](../contracts/ontology/schema.json): generated JSON Schema Draft 2020-12 for closed graph bundles; do not edit manually.
- [Vocabulary](../contracts/ontology/vocabulary.json): generated entity definitions, relationships, and controlled domains; do not edit manually.
- [Source mappings](../contracts/ontology/source-mappings.json): hand-maintained mappings from the inspected BMW files and requirements for a future CSV/SQL adapter.
- [Web research guide](web-research.md): collection and extraction contract for external research.
- [Synthetic example](../contracts/ontology/examples/synthetic.json): shareable fictional examples of all three web research modes. Every source is explicitly synthetic; reserved `example.invalid` URLs are never fetched.
- `../raw_data/ontology_examples/feedback-and-sales.json`: local examples mapped from the supplied BMW files. This file stays inside the existing ignored raw-data folder.
- `../backend/bmwow/ontology/models.py`: canonical Pydantic models and field constraints.
- `../backend/bmwow/ontology/relationships.py`: canonical relationship rules.
- `../backend/bmwow/ontology/validation.py`: structural and graph validation.
- `../backend/bmwow/ontology/schema.py`: JSON contract generation and drift checks.

All Python work shares the root uv project. There is no ontology-specific environment
or requirements file. See the [repository README](../README.md) for setup, package
layout, Python usage, and team handoff. From the repository root:

```sh
uv sync --locked
uv run bmwow-schema --check
uv run bmwow-validate contracts/ontology/examples/synthetic.json
uv run bmwow-validate raw_data/ontology_examples/feedback-and-sales.json
uv run pytest
```

The local BMW example and its 90% usability criterion are illustrative mappings and author proposals. The threshold is labeled `proposed_target`; it was not observed in the data or approved by BMW. The sample is intended to validate the contract, not establish a market-wide priority.

## Questions the ontology must answer

1. Which original records justify a requirement, and where can a reviewer find them?
2. Which customer outcome does it address, for which baseline model and market?
3. Which evidence challenges the proposal or suggests a different implementation?
4. Which competitor capability is being compared, on which model, variant, and market? Is it announced, standard, or optional?
5. Which future-facing assumptions must hold, and how would we validate them?
6. Which person reviewed which exact requirement revision, and why?
7. Are apparent frequencies counting feedback records, classification rows, people, or a defined survey population?

These questions define the boundaries of v0.1. Add a concept when it enables a concrete question the team needs to answer.

## Entity meanings

**SourceDocument** identifies a file, SQL source, or captured web page. Preserve origin, publication date when known, retrieval timestamp, source role, content hash when available, and independence group. A manufacturer's claim and an owner's opinion remain different source types.

**Evidence** identifies a specific original record, excerpt, or statistic and its source locator. It contains original text or a typed measurement. A feedback record may preserve several raw classifications. Evidence does not include generated interpretations or customer requirements.

**Signal** is one interpretation of evidence. Its kind is `customer_feedback`, `public_sentiment`, `competitor_capability`, or `trend_indicator`. Distinguish reported experience, opinion, publisher claim, inference, and forecast. Extraction confidence describes the mapping, not the truth of a claim or its importance to customers.

**CustomerNeed** is a customer outcome synthesized from signals. A positive comment can support preserving a valuable experience. A negative comment can motivate improving it. Sentiment and importance are separate.

**Feature** provides canonical names for capabilities and experiences across files and web sources. Preserve original VFC categories and use them as mapping inputs. VFC classifications are a source taxonomy, not a complete substitute for the ontology.

**VehicleModel** identifies a BMW or competitor model. Generation, model year, and variant remain explicit when known. G60 and G68 remain distinct models even when a source combines their sales. A Requirement's model references identify its existing BMW baseline; they do not assert facts about a future model.

**Market** records the intended market group and its explicitly configured country membership. The sales label `EU` is labeled Europe in the provided file; the study uses `EU`. Exact country coverage is not supplied. Do not silently equate Europe with EU membership or assign feedback countries to a market without a team mapping.

**Trend** synthesizes scoped indicators into an observed direction, forecast, or mixture. A forecast records its horizon, uncertainty, and assumptions. A single article may motivate a candidate trend; it does not establish widespread adoption.

**Assumption** records an unproven premise, its rationale, its impact if false, and a validation plan. It remains distinguishable from original evidence.

**Requirement** records a customer-facing proposal, baseline/market scope, customer value, acceptance criteria, justification, and assumptions. The horizon is three to five years. Numerical criteria state whether they are proposed, evidence-supported, or set by a human. Prioritization rationale is inspectable prose; no scoring weights or market-volume multipliers are prescribed.

**Decision** is an immutable human review event: approve, reject, request changes, set priority, or comment. It targets one exact requirement revision. Review state and priority are derived from decisions; they are not fields an extraction agent can set on a Requirement.

## Relationship direction

- `Evidence IN_SOURCE SourceDocument`: original location.
- `Signal DERIVED_FROM Evidence`: interpretation with source traceability.
- `Trend DERIVED_FROM Signal/Evidence`: indicator inputs.
- `Signal/Trend SUPPORTS CustomerNeed/Requirement/Assumption`: positive justification with a rationale.
- `Signal/Trend CHALLENGES CustomerNeed/Requirement/Assumption`: opposing evidence or a limitation.
- `Requirement ADDRESSES CustomerNeed`: intended customer outcome.
- `Requirement JUSTIFIED_BY Signal/Trend`: supporting evidence chain.
- `Requirement/CustomerNeed/Trend DEPENDS_ON Assumption`: explicit inferential premise.
- `Signal/CustomerNeed/Trend/Requirement CONCERNS Feature`: canonical subject.
- `Decision REVIEWS Requirement`: human review of an exact revision.
- `VehicleModel COMPETES_WITH VehicleModel`: explained competitive selection. Market/variant claims remain on the supporting capability signals; this edge alone does not prove equivalence.
- `new revision SUPERSEDES old revision`: revision history for the same logical entity and type.

Edges have IDs, rationale, and an optional `context_transfer`. An inference across different vehicles or markets must explain that transfer. A competitor offering may be relevant to a BMW proposal without proving BMW customer demand. Keep opposing evidence alongside a proposal rather than removing it during synthesis.

## Identity and revisions

All nodes have an immutable `id`, a stable logical `entity_key`, and a positive `revision`. Use IDs such as `requirement:parking-usability:v1` and `requirement:parking-usability:v2` with a shared `entity_key` of `requirement:parking-usability`.

Original Evidence is immutable. Identify a feedback record by its source/version plus original ID. One ID can have several classification rows; preserve those rows within `raw_classifications`, with their own locators. Distinct Signals can derive from the same Evidence. Count distinct evidence keys for feedback-record frequency; respondent frequency requires a real respondent identifier that these files do not provide.

Changing a requirement creates a new node revision linked through `SUPERSEDES`. Approval of revision 1 does not approve revision 2. Keep previous review events. The application must authenticate and authorize the human issuing a Decision: a JSON field saying `human` is not authentication.

Treat a bundle as a closed snapshot: every referenced node, including context and criterion references, must be present. Agent retrieval can return a smaller closed subgraph. Validate against the merged snapshot when submitting a patch. This is an interchange contract, not a final HTTP endpoint design.

## Quantitative evidence

Keep measurement value, unit, statistic, period, temporal status, scale, sample size, denominator, population, and comparison basis separate. Unknown metadata is `null`, never guessed. Preserve a real zero as zero.

Means, response proportions, counts, and percentages have different semantics. A source's normalized `Sample total = 1` is not a sample size of one respondent. Cross-market study comparisons need compatible question wording, scales, methodology, and populations. WLTP and EPA vehicle measurements require an explicit compatible comparison basis before ranking.

The sales file includes 2030 values without an inspected forecasting method. They are `source_reported_future` in the local example, not historical actuals. A 2025 study is evidence about the reported 2025 population, not a prediction of successor preferences.

## Ontology development factors

- **Decision usefulness:** start from the questions above and customer outcomes.
- **Granularity:** distinguish source documents, original records, extracted signals, needs, and proposed solutions.
- **Scope and time:** preserve market, country, model generation, variant, observation period, publication date, and future horizon.
- **Provenance:** preserve exact locators, source versions, transformation method, and author/agent attribution.
- **Epistemic status:** separate opinions, reported experiences, publisher claims, inferences, forecasts, and assumptions.
- **Comparability and independence:** track units, survey bases, deduplication, syndication, and missing population information.
- **Conflicting evidence:** model challenge links and competing implementations explicitly.
- **Human control:** retain decisions and revision history independently of agent proposals.
- **Team interoperability:** agree on IDs and payloads; adapt the raw SQL layer rather than requiring it to mirror the entire ontology.
- **Small initial scope:** begin with a vehicle, market, and a few themes, then expand against real retrieval needs.

## Integration ownership

The SQL teammate can preserve the current raw field structure. An adapter groups repeated feedback rows and converts statistics into typed Evidence. Derived nodes and relationships can be persisted in additional tables, a graph snapshot, or another service chosen by the team. Do not create a second conflicting copy of raw data.

The orchestration teammate retrieves a scoped subgraph and proposes Signals, Needs, Trends, Assumptions, and Requirements. Evidence must be captured by retrieval tools; generated text must not be inserted as original Evidence. Web research uses the separate collection contract.

The frontend teammate displays the requirement, customer need, supporting/challenging paths, source locators, assumptions, criterion basis, and revision-specific decisions. A first integration can use the synthetic fixture while the raw-data adapter is being built.

## Validation and limits

The validator checks JSON types/formats, IDs, references, relationship endpoint types, feedback deduplication, evidence paths, context-transfer explanations, quantitative bounds, future-value labels, requirement grounding, assumptions, and human/revision-specific decisions. It does not determine whether sources are truthful, survey samples are representative, inferred scope transfers are justified, or a target is realistic. Those remain research and product-review responsibilities.

The contract borrows the provenance idea of entities, derivations, and actor attribution from [W3C PROV-O](https://www.w3.org/TR/prov-o/). It does not claim PROV-O conformance. Structural validation follows [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation). A directed multigraph such as [NetworkX MultiDiGraph](https://networkx.org/documentation/stable/reference/classes/multidigraph.html) can preserve differently typed relationships between the same nodes.
