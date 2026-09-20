"""Saved Revision component for immutable Season Summary / Closure Marker evidence."""

from __future__ import annotations

import hashlib
from typing import Literal

from beta_engine.domain.run_revisions import canonical_json
from beta_engine.domain.season_closure import (
    SeasonClosureMarker,
    SeasonClosurePackage,
)
from beta_engine.domain.rankings.official import FrozenInput

SEASON_CLOSURE_COMPONENT_KEY = "season_closure"


class SavedRevisionSeasonClosure(FrozenInput):
    """Closure evidence embedded in the exact Saved Revision it names."""

    schema_version: Literal["saved_revision_season_closure.v1"] = (
        "saved_revision_season_closure.v1"
    )
    summary: object
    marker: object

    @classmethod
    def build(
        cls,
        *,
        package: SeasonClosurePackage,
        marker: SeasonClosureMarker,
    ) -> "SavedRevisionSeasonClosure":
        if (
            marker.run_id,
            marker.branch_id,
            marker.completed_week,
            marker.season_summary_fingerprint,
            marker.closing_ranking_fingerprint,
        ) != (
            package.summary.run_id,
            package.summary.branch_id,
            package.summary.completed_week,
            package.summary.fingerprint,
            package.summary.closing_ranking_fingerprint,
        ):
            raise ValueError("Saved Revision season closure references are inconsistent")
        return cls(
            summary=package.summary.model_dump(mode="json"),
            marker=marker.model_dump(mode="json"),
        )

    @property
    def parsed_summary(self):
        from beta_engine.domain.season_closure import SeasonSummarySnapshot

        return SeasonSummarySnapshot.model_validate_json(canonical_json(self.summary))

    @property
    def parsed_marker(self):
        return SeasonClosureMarker.model_validate_json(canonical_json(self.marker))

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            canonical_json(self.model_dump(mode="json")).encode("utf-8")
        ).hexdigest()


def install_saved_revision_season_closure(
    payload: dict,
    *,
    package: SeasonClosurePackage,
    marker: SeasonClosureMarker,
) -> SavedRevisionSeasonClosure:
    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")
    if marker.final_saved_revision_id.strip() == "":
        raise ValueError("Season Closure Marker requires a Saved Revision identity")
    component = SavedRevisionSeasonClosure.build(package=package, marker=marker)
    content[SEASON_CLOSURE_COMPONENT_KEY] = {
        "fingerprint": component.fingerprint,
        "state": component.model_dump(mode="json"),
    }
    return component


def load_saved_revision_season_closure(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
    revision_id: str,
) -> SavedRevisionSeasonClosure | None:
    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValueError("Saved Revision content must be an object")
    raw = content.get(SEASON_CLOSURE_COMPONENT_KEY)
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != {"fingerprint", "state"}:
        raise ValueError("Invalid Saved Revision season closure component")
    component = SavedRevisionSeasonClosure.model_validate(raw["state"])
    if component.fingerprint != raw["fingerprint"]:
        raise ValueError("Saved Revision season closure fingerprint mismatch")
    summary = component.parsed_summary
    marker = component.parsed_marker
    if (summary.run_id, summary.branch_id) != (run_id, branch_id):
        raise ValueError("Saved Revision season closure scope mismatch")
    if (
        marker.run_id,
        marker.branch_id,
        marker.final_saved_revision_id,
        marker.season_summary_fingerprint,
        marker.closing_ranking_fingerprint,
    ) != (
        run_id,
        branch_id,
        revision_id,
        summary.fingerprint,
        summary.closing_ranking_fingerprint,
    ) or marker.completed_week != summary.completed_week:
        raise ValueError("Saved Revision season closure identity mismatch")
    return component
