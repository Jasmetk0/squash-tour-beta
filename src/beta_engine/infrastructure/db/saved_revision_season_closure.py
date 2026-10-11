"""Saved Revision component for immutable Season Summary / Closure Marker evidence."""

from __future__ import annotations

import hashlib
from typing import Literal

from beta_engine.domain.run_revisions import canonical_json
from beta_engine.domain.season_closure import (
    SeasonClosureMarker,
    SeasonClosureMarkerCandidate,
    SeasonClosurePackage,
    bind_season_closure_marker,
    build_season_closure_package,
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


def rebind_saved_revision_season_closure(
    payload: dict,
    *,
    run_id: str,
    branch_id: str,
    source_revision_id: str,
    target_revision_id: str,
) -> SavedRevisionSeasonClosure | None:
    """Validate a copied closure component and bind it to a new Saved Revision id.

    Restore creates a new immutable revision rather than mutating the historical
    target. The embedded closure marker therefore cannot retain the historical
    target revision id: doing so would make the new revision fail its own
    load-time identity validation.
    """

    component = load_saved_revision_season_closure(
        payload,
        run_id=run_id,
        branch_id=branch_id,
        revision_id=source_revision_id,
    )
    if component is None:
        return None

    summary = component.parsed_summary
    marker = component.parsed_marker
    candidate = SeasonClosureMarkerCandidate(
        run_id=marker.run_id,
        branch_id=marker.branch_id,
        completed_week=marker.completed_week,
        season_summary_fingerprint=marker.season_summary_fingerprint,
        closing_ranking_fingerprint=marker.closing_ranking_fingerprint,
        rule_versions=marker.rule_versions,
    )
    package = SeasonClosurePackage(summary=summary, marker=candidate)
    rebound_marker = bind_season_closure_marker(
        candidate,
        final_saved_revision_id=target_revision_id,
    )
    return install_saved_revision_season_closure(
        payload,
        package=package,
        marker=rebound_marker,
    )


def rebind_cross_branch_season_closure(
    source_payload: dict,
    target_payload: dict,
    *,
    run_id: str,
    source_branch_id: str,
    source_revision_id: str,
    target_branch_id: str,
    target_revision_id: str,
    source_closing,
    target_closing,
) -> SavedRevisionSeasonClosure:
    """Rebuild the committed closure envelope for a *different* Branch.

    The caller must first prove both closing archives from their complete,
    independently remapped ranking ledgers. This function binds the verified
    target archive, summary, policy and new Saved Revision identity; it never
    copies a source Branch fingerprint or mutates the original revision.
    Existing production fork guards must remain until rollover events and
    transaction installation are integrated.
    """
    if (
        not source_branch_id or not target_branch_id
        or source_branch_id == target_branch_id
        or not source_revision_id or not target_revision_id
        or (source_closing.run_id, source_closing.branch_id)
        != (run_id, source_branch_id)
        or (target_closing.run_id, target_closing.branch_id)
        != (run_id, target_branch_id)
        or source_closing.completed_week != target_closing.completed_week
        or source_closing.policy != target_closing.policy
    ):
        raise ValueError("Cross-Branch Season Closure scope or boundary differs")

    original = load_saved_revision_season_closure(
        source_payload,
        run_id=run_id,
        branch_id=source_branch_id,
        revision_id=source_revision_id,
    )
    if original is None:
        raise ValueError("Cross-Branch Season Closure source component is missing")

    old_summary = original.parsed_summary
    old_marker = original.parsed_marker
    if old_summary.season_scoped_statistics:
        # No season-statistic transfer adapter is authoritative in V1.
        raise ValueError(
            "Cross-Branch Season Closure requires remapping season-scoped statistics"
        )
    original_package = build_season_closure_package(
        closing_ranking=source_closing,
        season_scoped_statistics=old_summary.season_scoped_statistics,
    )
    if (
        original_package.summary != old_summary
        or original_package.marker.rule_versions != old_marker.rule_versions
    ):
        raise ValueError("Cross-Branch Season Closure original package differs from archive")
    source_rows = tuple((row.rank, row.player_id, row.points) for row in source_closing.rows)
    target_rows = tuple((row.rank, row.player_id, row.points) for row in target_closing.rows)
    if source_rows != target_rows or source_closing.fingerprint == target_closing.fingerprint:
        raise ValueError("Cross-Branch Season Closure sporting result or ownership differs")

    package = build_season_closure_package(closing_ranking=target_closing)
    marker = bind_season_closure_marker(
        package.marker,
        final_saved_revision_id=target_revision_id,
    )
    # Only the target payload is modified, and its canonical component is
    # verified immediately against the new Branch and Saved Revision.
    installed = install_saved_revision_season_closure(
        target_payload,
        package=package,
        marker=marker,
    )
    if load_saved_revision_season_closure(
        target_payload,
        run_id=run_id,
        branch_id=target_branch_id,
        revision_id=target_revision_id,
    ) != installed:
        raise ValueError("Cross-Branch Season Closure could not be verified")
    return installed
