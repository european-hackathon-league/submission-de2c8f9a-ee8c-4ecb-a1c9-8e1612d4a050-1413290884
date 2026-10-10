"""Typed ontology contract and validation, independent of storage and orchestration."""

from .models import GraphBundle
from .validation import validate_bundle

__all__ = ["GraphBundle", "validate_bundle"]
