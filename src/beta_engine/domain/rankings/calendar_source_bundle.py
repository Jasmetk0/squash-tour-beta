"""Immutable, externally hash-verifiable bundle of *unpublished* ranking sources.

A portable staging checkpoint only; NOT a Saved Revision, an authoritative
match outcome, a Viewer publication, or an operation that reassigns a Branch.
Its Saved HEAD identity/hash and complete RunCalendar are exact, not inferred
from current defaults. Callers must independently obtain the expected bundle
fingerprint rather than trusting the JSON's own contents.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import CalendarRankingWeek
from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion,
    CalendarRankingZeroVersion,
    resolve_calendar_ranking_sources,
)
from beta_engine.domain.rankings.official import FrozenInput


class CalendarRankingSourceBundle(FrozenInput):
    schema_version: Literal["calendar_ranking_source_staging_bundle.v1"] = (
        "calendar_ranking_source_staging_bundle.v1"
    )
    run_id: str = Field(min_length=1, max_length=128)
    branch_id: str = Field(min_length=1, max_length=128)
    saved_head_revision_id: str = Field(min_length=1, max_length=128)
    saved_head_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_calendar: dict[str, int | str]
    results: tuple[CalendarRankingResultVersion, ...] = ()
    zeros: tuple[CalendarRankingZeroVersion, ...] = ()

    @model_validator(mode="after")
    def validate_complete_staging(self):
        calendar = RunCalendar.from_metadata(self.run_calendar)
        if calendar.schema_version != "run_calendar.v1":
            raise ValueError("Calendar staging bundle requires an explicit Run clock")
        ordinals = [
            calendar.ordinal(item.effective_week.season_index, item.effective_week.week)
            for item in (*self.results, *self.zeros)
        ]
        clock = calendar.position_at_ordinal(max(ordinals, default=0))
        resolve_calendar_ranking_sources(
            run_calendar=calendar, run_id=self.run_id, branch_id=self.branch_id,
            week=CalendarRankingWeek(
                season_index=clock.season_index, week=clock.season_week,
            ),
            result_versions=self.results, zero_versions=self.zeros,
        )
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True, separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()


def load_calendar_ranking_source_bundle(
    payload_json: str,
    *,
    expected_fingerprint: str,
    run_id: str,
    branch_id: str,
    saved_head_revision_id: str,
    saved_head_content_hash: str,
    run_calendar: RunCalendar,
) -> CalendarRankingSourceBundle:
    """Fail closed on independent fingerprint, scope, exact origin and calendar.

    The bundle does not sign itself; the expected fingerprint must be obtained
    from independently trusted checkpoint metadata.
    """
    if (
        len(expected_fingerprint) != 64
        or any(c not in "0123456789abcdef" for c in expected_fingerprint)
    ):
        raise ValueError("Valid external bundle fingerprint is required")
    bundle = CalendarRankingSourceBundle.model_validate_json(payload_json)
    if (
        bundle.run_id != run_id
        or bundle.branch_id != branch_id
        or bundle.saved_head_revision_id != saved_head_revision_id
        or bundle.saved_head_content_hash != saved_head_content_hash
        or bundle.run_calendar != run_calendar.to_metadata()
    ):
        raise ValueError("Calendar source bundle Saved origin/scope/clock mismatch")
    if bundle.fingerprint != expected_fingerprint:
        raise ValueError("Calendar source bundle fingerprint mismatch")
    return bundle
