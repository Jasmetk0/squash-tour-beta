from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.domain.matches import (
    EffectiveMatchFormatSnapshot,
    MatchFormat,
    resolve_effective_match_format,
)


def test_match_format_requires_an_odd_best_of() -> None:
    with pytest.raises(ValidationError, match="best_of must be odd"):
        MatchFormat(best_of=4, games_to=11, win_by=2)


def test_override_requires_the_complete_atomic_format() -> None:
    with pytest.raises(ValidationError, match="games_to"):
        MatchFormat.model_validate({"best_of": 3})


def test_effective_format_uses_only_the_nearest_whole_override() -> None:
    snapshot = resolve_effective_match_format(
        draw_type="main",
        round_number=2,
        tournament_edition_override=MatchFormat(best_of=1, games_to=7, win_by=1),
        phase_overrides={"main": MatchFormat(best_of=3, games_to=9, win_by=2)},
        round_overrides={"main:2": MatchFormat(best_of=5, games_to=15, win_by=2)},
    )

    assert snapshot.format == MatchFormat(best_of=5, games_to=15, win_by=2)
    assert snapshot.source_scope == "round_override"
    assert snapshot.source_key == "main:2"


def test_effective_format_falls_back_directly_to_official_bo5() -> None:
    snapshot = resolve_effective_match_format(draw_type="qualification", round_number=1)

    assert snapshot.format == MatchFormat(best_of=5, games_to=11, win_by=2)
    assert snapshot.source_scope == "official_default"


def test_effective_format_snapshot_rejects_tampering() -> None:
    snapshot = resolve_effective_match_format(draw_type="main", round_number=1)
    payload = snapshot.model_dump(mode="json")
    payload["format"]["games_to"] = 9

    with pytest.raises(ValidationError, match="snapshot hash mismatch"):
        EffectiveMatchFormatSnapshot.model_validate(payload)


def test_invalid_override_scope_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported match format phase"):
        resolve_effective_match_format(
            draw_type="main",
            round_number=1,
            phase_overrides={
                "semifinal": MatchFormat(best_of=5, games_to=11, win_by=2)
            },
        )

    with pytest.raises(ValueError, match="invalid match format round override"):
        resolve_effective_match_format(
            draw_type="main",
            round_number=1,
            round_overrides={
                "main:zero": MatchFormat(best_of=5, games_to=11, win_by=2)
            },
        )
