"""Fast, non-authoritative JSON schema dispatch for large immutable models.

A version tag only selects which existing Pydantic JSON validator gets the raw
bytes. This function MUST NOT be used as a content-integrity proof, and does
not replace complete model validation, content hashes or Saved replay.
"""
from __future__ import annotations

import json

from pydantic_core import SchemaValidator, core_schema


_SCHEMA_VERSION = SchemaValidator(
    core_schema.typed_dict_schema(
        {"schema_version": core_schema.typed_dict_field(
            core_schema.any_schema(), required=False,
        )},
        extra_behavior="ignore",
    ),
    config=core_schema.CoreConfig(cache_strings=False),
)


def schema_version_for_json(raw):
    """Extract only the top-level tag without allocating the entire JSON tree.

    On unfamiliar top-level shapes or parse failure, preserve the existing
    standard-library decode behavior. A non-object root still routes to the
    ordinary legacy model validator, which rejects it as before.
    """
    try:
        return _SCHEMA_VERSION.validate_json(raw).get("schema_version")
    except (TypeError, ValueError):
        value = json.loads(raw)
        return value.get("schema_version") if isinstance(value, dict) else None
