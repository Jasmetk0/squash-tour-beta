"""Run-calendar knockout ranking input witnessed by completed MatchEngine results.

Unlike calendar_knockout_ranking_evidence.v1 (manually supplied outcomes),
this versioned preparation evidence binds the entire bracket to serialized
MatchResult objects with complete rally logs and externally frozen match-input
fingerprints. It validates all match completion and score accounting without
running RNG, and derives (never independently supplies) each winner.

NOTE: an internally consistent MatchResult is NOT proof that it was produced
by a *particular Run's* authoritative sporting writer. Only a future Saved
Match/Slot authority reader can attest the external expected witness hash.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.matches.models import MatchResult, MatchTerminationReason
from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.calendar_knockout_ranking_evidence import (
    CalendarKnockoutRankingEvidence,
    prepare_calendar_knockout_ranking_versions,
)


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


class CalendarEngineMatchWitness(FrozenInput):
    schema_version: Literal["calendar_engine_match_witness.v1"] = (
        "calendar_engine_match_witness.v1"
    )
    match_input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    authoritative_result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    result: MatchResult

    @model_validator(mode="after")
    def validate_complete_match(self):
        r = MatchResult.model_validate_json(self.result.model_dump_json())
        if (
            r.termination_reason != MatchTerminationReason.COMPLETED
            or r.retired_player_id is not None
            or r.retired_at_set_start is not None
            or r.rally_log is None
            or not r.rally_log.events
        ):
            raise ValueError("Engine witness needs a completed, rally-logged, non-RET result")
        if (
            r.best_of < 1 or r.best_of % 2 != 1
            or r.games_to < 1 or r.win_by < 1
            or r.player_a_id == r.player_b_id
            or {r.winner_player_id, r.loser_player_id}
            != {r.player_a_id, r.player_b_id}
        ):
            raise ValueError("Engine witness has invalid match format or player identities")
        required_wins = r.best_of // 2 + 1
        if (
            len(r.sets) < required_wins
            or len(r.sets) > r.best_of
            or set(r.sets_won) != {r.player_a_id, r.player_b_id}
        ):
            raise ValueError("Engine witness has incomplete set accounting")
        counts = {r.player_a_id: 0, r.player_b_id: 0}
        for i, item in enumerate(r.sets, 1):
            if (
                item.set_number != i
                or item.ended_by_retirement
                or {item.winner_player_id, item.loser_player_id}
                != {r.player_a_id, r.player_b_id}
                or item.winner_games < r.games_to
                or item.winner_games - item.loser_games < r.win_by
                or max(counts.values()) >= required_wins
            ):
                raise ValueError("Engine witness contains invalid or post-terminal games")
            counts[item.winner_player_id] += 1
        if (
            counts != r.sets_won
            or counts[r.winner_player_id] != required_wins
            or counts[r.loser_player_id] >= required_wins
            or r.sets[-1].winner_player_id != r.winner_player_id
        ):
            raise ValueError("Engine witness match winner disagrees with played sets")
        if self.authoritative_result_fingerprint != _hash({
            "input": self.match_input_fingerprint,
            "result": r.model_dump(mode="json"),
        }):
            raise ValueError("Engine witness input/result receipt fingerprint mismatch")
        return self

    @property
    def scoreline(self) -> str:
        r = self.result
        return f"{r.sets_won[r.winner_player_id]}-{r.sets_won[r.loser_player_id]}"


class CalendarEngineKnockoutEvidence(FrozenInput):
    schema_version: Literal["calendar_engine_knockout_evidence.v1"] = (
        "calendar_engine_knockout_evidence.v1"
    )
    bracket: CalendarKnockoutRankingEvidence
    # One completed, engine-logged match per canonical bracket position/order.
    witnesses: tuple[CalendarEngineMatchWitness, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_witnesses(self):
        b = CalendarKnockoutRankingEvidence.model_validate_json(
            self.bracket.model_dump_json()
        )
        if len(self.witnesses) != len(b.matches):
            raise ValueError("Engine witnesses must cover every bracket match")
        if len({w.result.match_id for w in self.witnesses}) != len(self.witnesses):
            raise ValueError("Engine witnesses have duplicate Match identity")
        if len({w.authoritative_result_fingerprint for w in self.witnesses}) != len(self.witnesses):
            raise ValueError("Engine witnesses cannot reuse one result receipt")
        for expected, witness in zip(b.matches, self.witnesses, strict=True):
            r = witness.result
            if (
                r.match_id != expected.match_id
                or r.winner_player_id != expected.winner_player_id
                or r.loser_player_id != expected.loser_player_id
                or witness.scoreline != expected.scoreline
            ):
                raise ValueError("Engine match result contradicts the knockout bracket")
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def prepare_calendar_engine_knockout_versions(
    evidence: CalendarEngineKnockoutEvidence,
    *,
    run_calendar: RunCalendar,
    expected_evidence_fingerprint: str,
) -> tuple[CalendarRankingResultVersion, ...]:
    """Project all ranking rows with the *engine-witnessed* root provenance.

    The supplied expected fingerprint is an externally trusted hash of a
    frozen witness, not an authority decision by this function. Neither this
    function nor its caller may unlock sporting writes or promote to Saved.
    """
    if (
        len(expected_evidence_fingerprint) != 64
        or any(c not in "0123456789abcdef" for c in expected_evidence_fingerprint)
    ):
        raise ValueError("An externally trusted engine evidence hash is required")
    evidence = CalendarEngineKnockoutEvidence.model_validate_json(
        evidence.model_dump_json()
    )
    if evidence.fingerprint != expected_evidence_fingerprint:
        raise ValueError("Engine knockout evidence fingerprint mismatch")
    underlying = prepare_calendar_knockout_ranking_versions(
        evidence.bracket,
        run_calendar=run_calendar,
        expected_evidence_fingerprint=evidence.bracket.fingerprint,
    )
    return tuple(
        version.model_copy(update={
            "result": version.result.model_copy(update={
                # The authoritative input fingerprint, full rally-logged
                # results and entire bracket are now one source identity.
                "source_fingerprint": evidence.fingerprint,
            }),
        })
        for version in underlying
    )
