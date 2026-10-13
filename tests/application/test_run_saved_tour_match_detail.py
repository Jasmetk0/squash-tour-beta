"""Saved Edition match detail must read canonical sport and only saved rally evidence."""
import pytest

from beta_engine.application import run_saved_tour_match_detail as detail
from beta_engine.application.run_saved_tour_read_model import resolve_run_saved_tour_edition
from tests.application.test_run_saved_tour_read_model import _args, _ranked
from tests.application.test_viewer_tournament_history_read_model import _state
from tests.application.test_saved_player_match_detail import _fake_competitive_match

pytestmark = pytest.mark.pr_critical


def _edition():
    return resolve_run_saved_tour_edition(
        **_args(_state(), ranking=_ranked()), event_id="event",
    )


def test_historical_canonical_match_without_rally_archive_is_still_readable():
    value = detail.resolve_run_saved_tour_match_detail(
        _edition(), match_id="final", saved_slots=None,
    )
    assert (value.run_id, value.branch_id, value.revision_branch_id) == (
        "run", "fork", "branch",
    )
    assert value.saved_revision_id == "ancestor-revision"
    assert (value.season_index, value.match_id, value.match.scoreline) == (
        2, "final", "3-2",
    )
    assert value.replay_status == "unavailable" and value.rallies == ()
    assert value.total_rallies == 0
    assert "seed" not in value.model_dump_json()


def test_missing_match_unpublished_event_and_bad_cursor_are_rejected():
    with pytest.raises(KeyError, match="not in the requested"):
        detail.resolve_run_saved_tour_match_detail(
            _edition(), match_id="no-match", saved_slots=None,
        )
    unpublished = resolve_run_saved_tour_edition(
        **_args(_state(), season_index=0), event_id="EVENT-OLD",
    )
    with pytest.raises(KeyError, match="no published"):
        detail.resolve_run_saved_tour_match_detail(
            unpublished, match_id="final", saved_slots=None,
        )
    for values in ({"offset": -1}, {"limit": 26}, {"match_id": " "}):
        with pytest.raises(ValueError):
            detail.resolve_run_saved_tour_match_detail(
                _edition(), match_id="final", saved_slots=None, **values,
            )


def test_real_archived_rallies_page_by_original_saved_branch(monkeypatch):
    from types import SimpleNamespace

    # Fake group here stands in for the already restore-grade validated Slot
    # component. HTTP/restart acceptance below uses the real persisted source.
    archived = _fake_competitive_match(count=3)
    monkeypatch.setattr(detail, "load_authoritative_group", lambda row: archived)
    component = {"groups": [{
        "match_id": "final", "week_ordinal": 2 * 61 + 16,
        "run_id": "run", "branch_id": "branch",
    }]}
    first = detail.resolve_run_saved_tour_match_detail(
        _edition(), match_id="final", saved_slots=component, limit=2,
    )
    assert first.replay_status == "available"
    assert first.total_rallies == 3 and first.has_more
    assert [r.rally_index for r in first.rallies] == [1, 2]
    last = detail.resolve_run_saved_tour_match_detail(
        _edition(), match_id="final", saved_slots=component, offset=2, limit=2,
    )
    assert [r.rally_index for r in last.rallies] == [3]
    assert not last.has_more
    assert last.branch_id == "fork" and last.revision_branch_id == "branch"

    foreign = {"groups": [{**component["groups"][0], "branch_id": "fork"}]}
    with pytest.raises(ValueError, match="foreign Run/Branch"):
        detail.resolve_run_saved_tour_match_detail(
            _edition(), match_id="final", saved_slots=foreign,
        )
    with pytest.raises(ValueError, match="Ambiguous archived"):
        detail.resolve_run_saved_tour_match_detail(
            _edition(), match_id="final",
            saved_slots={"groups": component["groups"] * 2},
        )
    archived.result.winner_player_id = "B"
    with pytest.raises(ValueError, match="contradicts canonical"):
        detail.resolve_run_saved_tour_match_detail(
            _edition(), match_id="final", saved_slots=component,
        )
