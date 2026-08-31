"""Atomic effective match-format resolution and immutable snapshots."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

MatchFormatSourceScope = Literal[
    "official_default",
    "tournament_edition_override",
    "phase_override",
    "round_override",
]


class MatchFormat(BaseModel):
    """One indivisible sporting format; fields never inherit separately."""

    best_of: int = Field(ge=1)
    games_to: int = Field(ge=1)
    win_by: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_best_of(self) -> MatchFormat:
        if self.best_of % 2 == 0:
            raise ValueError("best_of must be odd so a match cannot end tied")
        return self


OFFICIAL_MATCH_FORMAT = MatchFormat(best_of=5, games_to=11, win_by=2)


class EffectiveMatchFormatSnapshot(BaseModel):
    """Hash-protected format and provenance stored when a match is materialized."""

    schema_version: str = "effective_match_format.v1"
    format: MatchFormat
    source_scope: MatchFormatSourceScope
    source_key: str
    snapshot_hash_algorithm: Literal["sha256"] = "sha256"
    snapshot_hash: str

    @classmethod
    def create(
        cls,
        *,
        format: MatchFormat,
        source_scope: MatchFormatSourceScope,
        source_key: str,
    ) -> EffectiveMatchFormatSnapshot:
        normalized_key = source_key.strip()
        if not normalized_key:
            raise ValueError("match format source_key must not be blank")
        payload = cls._hash_payload(
            schema_version="effective_match_format.v1",
            format=format,
            source_scope=source_scope,
            source_key=normalized_key,
        )
        return cls(
            format=format,
            source_scope=source_scope,
            source_key=normalized_key,
            snapshot_hash=cls._content_hash(payload),
        )

    @model_validator(mode="after")
    def validate_snapshot_hash(self) -> EffectiveMatchFormatSnapshot:
        expected = self._content_hash(
            self._hash_payload(
                schema_version=self.schema_version,
                format=self.format,
                source_scope=self.source_scope,
                source_key=self.source_key,
            )
        )
        if self.snapshot_hash != expected:
            raise ValueError("effective match format snapshot hash mismatch")
        return self

    @staticmethod
    def _hash_payload(
        *,
        schema_version: str,
        format: MatchFormat,
        source_scope: MatchFormatSourceScope,
        source_key: str,
    ) -> dict[str, object]:
        return {
            "schema_version": schema_version,
            "format": format.model_dump(mode="json"),
            "source_scope": source_scope,
            "source_key": source_key,
        }

    @staticmethod
    def _content_hash(payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def official_match_format_snapshot() -> EffectiveMatchFormatSnapshot:
    return EffectiveMatchFormatSnapshot.create(
        format=OFFICIAL_MATCH_FORMAT,
        source_scope="official_default",
        source_key="official:individual-match",
    )


def resolve_effective_match_format(
    *,
    draw_type: Literal["qualification", "main"],
    round_number: int,
    tournament_edition_override: MatchFormat | None = None,
    phase_overrides: dict[str, MatchFormat] | None = None,
    round_overrides: dict[str, MatchFormat] | None = None,
) -> EffectiveMatchFormatSnapshot:
    """Resolve nearest permitted whole-format override without hidden levels."""

    if round_number < 1:
        raise ValueError("round_number must be at least 1")
    phase_overrides = phase_overrides or {}
    round_overrides = round_overrides or {}
    unknown_phases = set(phase_overrides) - {"qualification", "main"}
    if unknown_phases:
        raise ValueError(
            f"unsupported match format phase override(s): {', '.join(sorted(unknown_phases))}"
        )

    round_key = f"{draw_type}:{round_number}"
    unknown_round_keys = [key for key in round_overrides if not _valid_round_key(key)]
    if unknown_round_keys:
        raise ValueError(
            f"invalid match format round override key(s): {', '.join(sorted(unknown_round_keys))}"
        )

    if round_key in round_overrides:
        return EffectiveMatchFormatSnapshot.create(
            format=round_overrides[round_key],
            source_scope="round_override",
            source_key=round_key,
        )
    if draw_type in phase_overrides:
        return EffectiveMatchFormatSnapshot.create(
            format=phase_overrides[draw_type],
            source_scope="phase_override",
            source_key=draw_type,
        )
    if tournament_edition_override is not None:
        return EffectiveMatchFormatSnapshot.create(
            format=tournament_edition_override,
            source_scope="tournament_edition_override",
            source_key="tournament-edition",
        )
    return official_match_format_snapshot()


def _valid_round_key(value: str) -> bool:
    phase, separator, round_value = value.partition(":")
    return (
        separator == ":"
        and phase in {"qualification", "main"}
        and round_value.isdigit()
        and int(round_value) >= 1
    )
