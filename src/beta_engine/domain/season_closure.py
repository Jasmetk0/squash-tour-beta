"""Immutable Season Summary and Closure Marker staging contracts.

Master fixes the Season Transition order but deliberately leaves the final Closure
Marker schema and the complete season-scoped statistic catalogue open.  This module
therefore provides only a minimal technical envelope:

- registered season-scoped statistic payloads can be frozen canonically;
- the Season Summary binds those payloads to the archived Closing Ranking;
- a lightweight Closure Marker candidate binds the summary, Closing Ranking and
  rule versions used by the implemented closing step;
- the final Saved Revision identity is bound only by the atomic transition writer.

Nothing here copies the whole sporting world or invents season statistics.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.rankings.season_closing import SeasonClosingRankingSnapshot


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _canonical_json(payload_json: str) -> str:
    try:
        value = json.loads(payload_json)
    except json.JSONDecodeError as exc:  # pragma: no cover - pydantic surfaces message
        raise ValueError("Season statistic payload must be valid JSON") from exc
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class SeasonScopedStatisticSnapshot(FrozenInput):
    """One explicitly registered season-scoped statistic component.

    The component catalogue is intentionally not hard-coded here. Callers may freeze
    only components that already have an authoritative producer; this envelope does
    not make an unknown statistic authoritative.
    """

    schema_version: Literal["season_scoped_statistic_snapshot.v1"] = (
        "season_scoped_statistic_snapshot.v1"
    )
    component_id: str = Field(min_length=1)
    component_schema_version: str = Field(min_length=1)
    payload_json: str = Field(min_length=2)

    @model_validator(mode="after")
    def canonical_payload(self):
        if self.payload_json != _canonical_json(self.payload_json):
            raise ValueError("Season statistic payload JSON must be canonical")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


class SeasonSummarySnapshot(FrozenInput):
    """Frozen season-scoped summary produced before any seasonal reset."""

    schema_version: Literal["season_summary.v1"] = "season_summary.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    completed_week: RankingWeek
    closing_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    statistics_catalog_version: Literal["season_scoped_statistics_registry.v1"] = (
        "season_scoped_statistics_registry.v1"
    )
    season_scoped_statistics: tuple[SeasonScopedStatisticSnapshot, ...] = ()

    @model_validator(mode="after")
    def validate_summary(self):
        if self.completed_week.week != 61:
            raise ValueError("Season Summary requires completed Week 61")
        ids = [item.component_id for item in self.season_scoped_statistics]
        if ids != sorted(set(ids)):
            raise ValueError(
                "Season Summary statistic components must be canonical and unique"
            )
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


class ClosureRuleVersionRef(FrozenInput):
    """Fingerprint-bound rule identity actually used by the closure slice."""

    rule_kind: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class SeasonClosureMarkerCandidate(FrozenInput):
    """Lightweight closure marker before the final Saved Revision exists."""

    schema_version: Literal["season_closure_marker_candidate.v1"] = (
        "season_closure_marker_candidate.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    completed_week: RankingWeek
    season_summary_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    closing_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    rule_versions: tuple[ClosureRuleVersionRef, ...]

    @model_validator(mode="after")
    def validate_marker(self):
        if self.completed_week.week != 61:
            raise ValueError("Season Closure Marker requires completed Week 61")
        keys = [item.rule_kind for item in self.rule_versions]
        if keys != sorted(set(keys)):
            raise ValueError("Closure rule versions must be canonical and unique")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


class SeasonClosureMarker(FrozenInput):
    """Committed marker identity; persistence belongs to atomic Season Transition."""

    schema_version: Literal["season_closure_marker.v1"] = "season_closure_marker.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    completed_week: RankingWeek
    season_summary_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    closing_ranking_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    rule_versions: tuple[ClosureRuleVersionRef, ...]
    final_saved_revision_id: str = Field(min_length=1)

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


class SeasonClosurePackage(FrozenInput):
    """Step-3 Season Transition candidate, still uncommitted."""

    schema_version: Literal["season_closure_package.v1"] = "season_closure_package.v1"
    summary: SeasonSummarySnapshot
    marker: SeasonClosureMarkerCandidate

    @model_validator(mode="after")
    def validate_package(self):
        if (
            self.summary.run_id,
            self.summary.branch_id,
            self.summary.completed_week,
            self.summary.fingerprint,
            self.summary.closing_ranking_fingerprint,
        ) != (
            self.marker.run_id,
            self.marker.branch_id,
            self.marker.completed_week,
            self.marker.season_summary_fingerprint,
            self.marker.closing_ranking_fingerprint,
        ):
            raise ValueError("Season closure package references are inconsistent")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def freeze_season_summary(
    *,
    closing_ranking: SeasonClosingRankingSnapshot,
    season_scoped_statistics: tuple[SeasonScopedStatisticSnapshot, ...] = (),
) -> SeasonSummarySnapshot:
    """Freeze only explicitly supplied authoritative season-scoped components."""

    closing = SeasonClosingRankingSnapshot.model_validate_json(
        closing_ranking.model_dump_json()
    )
    return SeasonSummarySnapshot(
        run_id=closing.run_id,
        branch_id=closing.branch_id,
        completed_week=closing.completed_week,
        closing_ranking_fingerprint=closing.fingerprint,
        season_scoped_statistics=tuple(
            sorted(season_scoped_statistics, key=lambda item: item.component_id)
        ),
    )


def build_season_closure_package(
    *,
    closing_ranking: SeasonClosingRankingSnapshot,
    season_scoped_statistics: tuple[SeasonScopedStatisticSnapshot, ...] = (),
) -> SeasonClosurePackage:
    """Build the summary + marker candidate from already staged Closing Ranking."""

    closing = SeasonClosingRankingSnapshot.model_validate_json(
        closing_ranking.model_dump_json()
    )
    summary = freeze_season_summary(
        closing_ranking=closing,
        season_scoped_statistics=season_scoped_statistics,
    )
    ranking_policy_ref = ClosureRuleVersionRef(
        rule_kind="official_ranking_policy",
        rule_id=closing.policy.policy_id,
        fingerprint=_hash(closing.policy.model_dump(mode="json")),
    )
    marker = SeasonClosureMarkerCandidate(
        run_id=closing.run_id,
        branch_id=closing.branch_id,
        completed_week=closing.completed_week,
        season_summary_fingerprint=summary.fingerprint,
        closing_ranking_fingerprint=closing.fingerprint,
        rule_versions=(ranking_policy_ref,),
    )
    return SeasonClosurePackage(summary=summary, marker=marker)


def bind_season_closure_marker(
    candidate: SeasonClosureMarkerCandidate,
    *,
    final_saved_revision_id: str,
) -> SeasonClosureMarker:
    """Bind a staged marker only after the atomic writer has a Saved Revision ID."""

    return SeasonClosureMarker(
        run_id=candidate.run_id,
        branch_id=candidate.branch_id,
        completed_week=candidate.completed_week,
        season_summary_fingerprint=candidate.season_summary_fingerprint,
        closing_ranking_fingerprint=candidate.closing_ranking_fingerprint,
        rule_versions=candidate.rule_versions,
        final_saved_revision_id=final_saved_revision_id,
    )
