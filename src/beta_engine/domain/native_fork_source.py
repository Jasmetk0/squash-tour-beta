"""Immutable references to a native fork's historical authorities.

These references describe original owners, never rewritten match inputs. A valid
model/hash alone is not authority: the persistence adapter must resolve it against
the actual authenticated Saved lineage before a writer may use it.
"""

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class NativeForkSavedSource(FrozenInput):
    revision_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class NativeForkComponentSource(FrozenInput):
    key: str = Field(min_length=1)
    # Hash the COMPLETE component, not just its self-declared fingerprint.
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class NativeForkSourceBinding(FrozenInput):
    schema_version: Literal["native_fork_source_binding.v1"] = (
        "native_fork_source_binding.v1"
    )
    run_id: str = Field(min_length=1)
    source: NativeForkSavedSource
    components: tuple[NativeForkComponentSource, ...] = Field(min_length=1)
    historical_sources: tuple[NativeForkSavedSource, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_canonical_sources(self):
        keys = tuple(c.key for c in self.components)
        revisions = tuple(s.revision_id for s in self.historical_sources)
        if keys != tuple(sorted(set(keys))) or revisions != tuple(
            sorted(set(revisions))
        ):
            raise ValueError(
                "Native fork sources must be distinct and canonically ordered"
            )
        if self.source.revision_id in revisions:
            raise ValueError(
                "A native fork source cannot authorize its own past execution"
            )
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))
