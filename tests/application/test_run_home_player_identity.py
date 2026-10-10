"""Run Home names are verified Saved Revision identities, not guessed labels."""
import pytest

from beta_engine.application.run_home_player_identity import (
    resolve_saved_home_player_identities,
)
from beta_engine.infrastructure.db.run_prospect_source_state import RunProspectSourceSnapshot
from tests.application.test_viewer_people_read_model import _world


@pytest.mark.pr_critical
def test_player_identity_from_run_initial_world_and_prospect_without_leaking_hidden_fields():
    source = RunProspectSourceSnapshot(
        schema_version="run_prospect_source_snapshot.v1",
        run_id="run",
        records=({"prospect_id": "PROSPECT-1", "display_name": "Future Star", "country_code": "USA"},),
        fingerprint="stored-immutable-proof",
    )
    output = resolve_saved_home_player_identities(
        run_id="run", branch_id="branch", saved_revision_id="revision-1",
        requested_ids=("P1", "PROSPECT-1", "unknown", "P2"),
        initial_world=_world(), prospect_source=source,
    )
    assert output.status == "partial"
    assert [player.display_name for player in output.players] == ["Initial One", "Future Star", "Initial Two"]
    assert [player.identity_source for player in output.players] == ["initial_world", "run_prospect", "initial_world"]
    assert output.unresolved_ids == ("unknown",)
    assert output.players[0].country_code == "CZE"
    assert "potential" not in output.model_dump_json()
    assert "seed" not in output.model_dump_json()


@pytest.mark.pr_critical
def test_player_identity_missing_is_explicit_not_fabricated_and_cross_branch_rejected():
    output = resolve_saved_home_player_identities(
        run_id="run", branch_id="branch", saved_revision_id="revision-0",
        requested_ids=("P1",), initial_world=None, prospect_source=None,
    )
    assert output.status == "unavailable"
    assert output.players == () and output.unresolved_ids == ("P1",)
    with pytest.raises(ValueError, match="another Run/Branch"):
        resolve_saved_home_player_identities(
            run_id="run", branch_id="foreign", saved_revision_id="revision-0",
            requested_ids=("P1",), initial_world=_world(), prospect_source=None,
        )
    with pytest.raises(ValueError, match="overlaps"):
        resolve_saved_home_player_identities(
            run_id="run", branch_id="branch", saved_revision_id="revision-0",
            requested_ids=("P1",), initial_world=_world(),
            prospect_source=RunProspectSourceSnapshot(
                schema_version="run_prospect_source_snapshot.v1", run_id="run",
                records=({"prospect_id": "P1", "display_name": "Impostor", "country_code": "USA"},),
                fingerprint="invalid",
            ),
        )


@pytest.mark.pr_critical
def test_player_identity_bounded_distinct_ids():
    for ids in [(), ("A", "A"), tuple(str(i) for i in range(26)), ("",)]:
        with pytest.raises(ValueError):
            resolve_saved_home_player_identities(
                run_id="run", branch_id="branch", saved_revision_id="revision",
                requested_ids=ids, initial_world=None, prospect_source=None,
            )
