"""Canonical relationship endpoints and descriptions for validation and export."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RelationshipRule:
    source_types: tuple[str, ...]
    target_types: tuple[str, ...]
    description: str


RELATIONSHIPS = {
    "IN_SOURCE": RelationshipRule(
        ("Evidence",), ("SourceDocument",), "Locates original evidence in its captured source."
    ),
    "DERIVED_FROM": RelationshipRule(
        ("Signal", "Trend"),
        ("Evidence", "Signal"),
        "Traces an interpretation or trend to its inputs. Signals derive directly from Evidence.",
    ),
    "CONCERNS": RelationshipRule(
        ("Signal", "CustomerNeed", "Trend", "Requirement"),
        ("Feature",),
        "Associates an interpretation or proposal with a canonical feature.",
    ),
    "SUPPORTS": RelationshipRule(
        ("Signal", "Trend"),
        ("CustomerNeed", "Requirement", "Assumption"),
        "Provides supporting evidence, with an explicit rationale and scope-transfer explanation.",
    ),
    "CHALLENGES": RelationshipRule(
        ("Signal", "Trend"),
        ("CustomerNeed", "Requirement", "Assumption"),
        "Provides opposing or limiting evidence; sentiment alone does not determine this relationship.",
    ),
    "ADDRESSES": RelationshipRule(
        ("Requirement",),
        ("CustomerNeed",),
        "States the customer outcome a requirement is intended to deliver.",
    ),
    "JUSTIFIED_BY": RelationshipRule(
        ("Requirement",),
        ("Signal", "Trend"),
        "Provides the evidence chain and rationale for a proposed requirement.",
    ),
    "DEPENDS_ON": RelationshipRule(
        ("Requirement", "CustomerNeed", "Trend"),
        ("Assumption",),
        "Makes a forward-looking or inferential premise explicit.",
    ),
    "REVIEWS": RelationshipRule(
        ("Decision",),
        ("Requirement",),
        "Targets one requirement revision without mutating the proposal or source evidence.",
    ),
    "COMPETES_WITH": RelationshipRule(
        ("VehicleModel",),
        ("VehicleModel",),
        "A scoped competitive comparison chosen for a market and segment, not assumed from brand alone.",
    ),
    "SUPERSEDES": RelationshipRule(
        ("Signal", "CustomerNeed", "Trend", "Assumption", "Requirement"),
        ("Signal", "CustomerNeed", "Trend", "Assumption", "Requirement"),
        "Links a newer revision to an older revision of the same entity type.",
    ),
}
