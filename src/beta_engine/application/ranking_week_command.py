"""Validated request for atomic ranking preparation, not full week advancement."""

import hashlib
import json

from pydantic import Field, model_validator

from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.ranking_tournament_ingestion import (
    TournamentRankingBinding,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.rankings.result_history import RankingResultVersion


class RankingWeekCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    context: RankingTransitionContext
    tournaments: tuple[TournamentRankingBinding, ...]
    corrections: tuple[RankingResultVersion, ...] = ()

    @model_validator(mode="after")
    def validate_batch(self):
        context = self.context
        if (
            not context.run_id
            or not context.branch_id
            or context.target_week.ordinal != context.completed_week.ordinal + 1
        ):
            raise ValueError(
                "Ranking command requires a scoped consecutive week boundary"
            )
        editions = [t.edition_id for t in self.tournaments]
        events = [t.event_id for t in self.tournaments]
        if len(set(editions)) != len(editions) or len(set(events)) != len(events):
            raise ValueError("Duplicate tournament in ranking command")
        for tournament in self.tournaments:
            if (tournament.run_id, tournament.branch_id) != (
                context.run_id,
                context.branch_id,
            ):
                raise ValueError("Tournament and ranking command scope mismatch")
            if (
                tournament.first_publication_week != context.target_week
                or tournament.completed_week.ordinal > context.completed_week.ordinal
            ):
                raise ValueError("Tournament lies outside ranking command boundary")
        keys = [(v.result.edition_id, v.result.player_id) for v in self.corrections]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate result correction in ranking command")
        for correction in self.corrections:
            if (correction.run_id, correction.branch_id) != (
                context.run_id, context.branch_id
            ):
                raise ValueError("Correction and ranking command scope mismatch")
            if (
                correction.effective_week != context.target_week
                or correction.result.first_publication_week.ordinal
                >= context.target_week.ordinal
                or correction.previous_fingerprint is None
            ):
                raise ValueError("Correction must update an earlier result at the target boundary")
            if correction.result.edition_id in editions:
                raise ValueError("Cannot ingest and correct the same Edition in one command")
        return self

    @property
    def fingerprint(self):
        payload = self.model_dump(mode="json")
        if payload["corrections"]:
            payload["corrections"].sort(
                key=lambda v: (v["result"]["edition_id"], v["result"]["player_id"])
            )
        else:
            # Preserve receipt compatibility with commands persisted before corrections.
            del payload["corrections"]
        if "disciplinary_zeros" in payload["context"]:
            payload["context"]["disciplinary_zeros"].sort(key=lambda z: z["zero_id"])
        payload["context"]["players"].sort(key=lambda p: p["player_id"])
        payload["tournaments"].sort(key=lambda t: t["edition_id"])
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
