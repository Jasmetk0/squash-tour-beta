"""Immutable name provenance, missing IDs and cross-Branch integrity."""
from __future__ import annotations
from dataclasses import replace

import pytest

from beta_engine.application.run_home_player_identity_read_model import resolve_run_home_player_identities
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot
from tests.application.test_viewer_people_read_model import _world


pytestmark = pytest.mark.pr_critical


def test_saved_initial_world_resolves_only_requested_names_and_explicit_missing():
    result = resolve_run_home_player_identities(
        run_id="run", branch_id="branch", saved_revision_id="saved",
        initial_world=_world(), prospects=None, player_ids=("P2", "NO-PLAYER", "P1", "P2"),
    )
    assert result.saved_revision_id == "saved"
    assert [(p.player_id, p.name, p.country_code, p.identity_source) for p in result.players] == [
        ("P2", "Initial Two", "EGY", "initial_world"),
        ("P1", "Initial One", "CZE", "initial_world"),
    ]
    assert result.unresolved_ids == ("NO-PLAYER",)
    assert "NO-PLAYER" not in {p.player_id for p in result.players}


def test_saved_prospect_identity_is_included_without_guessing():
    prospect = RunProspectSourceSnapshot(
        schema_version="run_prospect_source_snapshot.v1",
        run_id="run",
        records=({"prospect_id": "PRO-1", "display_name": "New Prospect",
                  "country_code": "cze"},),
        fingerprint="sha-test",
    )
    result = resolve_run_home_player_identities(
        run_id="run", branch_id="branch", saved_revision_id="saved",
        initial_world=_world(), prospects=prospect,
        player_ids=("PRO-1", "P1", "UNSEEN"),
    )
    assert [p.name for p in result.players] == ["New Prospect", "Initial One"]
    assert result.players[0].identity_source == "run_prospect"
    assert result.players[0].country_code == "CZE"
    assert result.unresolved_ids == ("UNSEEN",)


def test_rejects_foreign_initial_world_duplicate_and_invalid_prospect():
    world = _world()
    with pytest.raises(ValueError, match="scope"):
        resolve_run_home_player_identities(
            run_id="run", branch_id="other", saved_revision_id="saved",
            initial_world=world, prospects=None, player_ids=("P1",),
        )
    overlap = RunProspectSourceSnapshot(
        schema_version="run_prospect_source_snapshot.v1", run_id="run",
        records=({"prospect_id": "P1", "display_name": "Duplicated",
                  "country_code": "CZE"},), fingerprint="fake",
    )
    with pytest.raises(ValueError, match="overlap"):
        resolve_run_home_player_identities(
            run_id="run", branch_id="branch", saved_revision_id="saved",
            initial_world=world, prospects=overlap, player_ids=("P1",),
        )
    with pytest.raises(ValueError, match="at most 30"):
        resolve_run_home_player_identities(
            run_id="run", branch_id="branch", saved_revision_id="saved",
            initial_world=world, prospects=None,
            player_ids=tuple(f"player-{i}" for i in range(31)),
        )
