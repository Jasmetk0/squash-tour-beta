"""Prevent forged winner/placement labels in authenticated MatchEngine results.

A result can preserve all rally-event hashes while changing only its top-level
winner fields; that must not produce a false native tournament champion.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import (
    MatchContext,
    MatchEngine,
    MatchParticipantContext,
    MatchResult,
    MatchTerminationReason,
    RetirementRule,
)
from tests.domain.test_match_engine import _player
from tests.domain.test_match_rally_log import _result

pytestmark = pytest.mark.pr_critical


def test_completed_match_winner_cannot_be_relabelled_without_changing_rallies():
    played = _result()
    original = played.model_dump(mode="json")
    forged = played.model_dump(mode="json")
    forged["winner_player_id"], forged["loser_player_id"] = (
        forged["loser_player_id"], forged["winner_player_id"]
    )
    # Original self-consistent source must remain readable and byte-identical.
    assert MatchResult.model_validate(original).model_dump(mode="json") == original
    assert forged["rally_log"] == original["rally_log"]
    with pytest.raises(ValidationError, match="completed match winner contradicts actual scored sets"):
        MatchResult.model_validate(forged)


def test_logged_match_rejects_wrong_set_winner_even_with_same_set_tallies():
    played = _result()
    forged = played.model_dump(mode="json")
    forged["sets"][0]["winner_player_id"], forged["sets"][0]["loser_player_id"] = (
        forged["sets"][0]["loser_player_id"], forged["sets"][0]["winner_player_id"]
    )
    # Relabelling an individual set cannot silently change the winner ledger.
    with pytest.raises(ValidationError, match="authoritative rally events|played set winners"):
        MatchResult.model_validate(forged)


def test_retirement_winner_must_be_opponent_not_retired_player():
    ctx = MatchContext(
        match_id="retirement-winner-integrity",
        player_a=MatchParticipantContext(player=_player(player_id="RET-A", base=84)),
        player_b=MatchParticipantContext(player=_player(player_id="RET-B", base=83)),
        retirement_rule=RetirementRule(
            enabled=True, retired_player_id="RET-A", set_number=3,
        ),
    )
    played = MatchEngine(rng=DeterministicRng(31415)).simulate(ctx)
    assert played.termination_reason == MatchTerminationReason.RETIREMENT
    assert played.retired_player_id == "RET-A"
    original = played.model_dump(mode="json")
    assert MatchResult.model_validate(original).model_dump(mode="json") == original

    forged = played.model_dump(mode="json")
    forged["winner_player_id"], forged["loser_player_id"] = (
        forged["loser_player_id"], forged["winner_player_id"]
    )
    with pytest.raises(ValidationError, match="retirement match winner must be the non-retired player"):
        MatchResult.model_validate(forged)
