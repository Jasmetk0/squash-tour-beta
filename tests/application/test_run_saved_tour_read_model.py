"""Exact Saved Tour reads: multi-season identities and canonical results only."""
import pytest

from beta_engine.application.run_saved_tour_read_model import (
    resolve_run_saved_tour_calendar, resolve_run_saved_tour_edition,
)
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.domain.run_packages import RunPackageState
from tests.application.test_viewer_tournament_history_read_model import _state
from tests.application.test_viewer_tournament_result_read_model import _source

pytestmark = pytest.mark.pr_critical


def _args(packages=None, ranking=None, **overrides):
    return dict(
        run_id="run", selected_branch_id="fork", revision_branch_id="branch",
        saved_revision_id="ancestor-revision", season_index=2,
        packages=packages, ranking=ranking,
    ) | overrides


def _ranked():
    return RankingRevisionState(
        run_id="run", branch_id="branch", entries=(), sources=(),
        tournament_sources=(_source(),),
    )


def test_empty_saved_calendar_and_distinct_multi_season_editions_are_read_only():
    empty = resolve_run_saved_tour_calendar(**_args())
    assert empty.calendar_status == "empty" and empty.editions == ()
    assert empty.week_count == 61 and empty.season == "2002/2003"

    saved = _state()
    before = saved.model_dump(mode="json")
    older = resolve_run_saved_tour_calendar(**_args(saved, season_index=0))
    current = resolve_run_saved_tour_calendar(**_args(saved))
    missing = resolve_run_saved_tour_calendar(**_args(saved, season_index=49))
    assert [(e.event_id, e.season_week) for e in older.editions] == [("EVENT-OLD", 5)]
    assert [(e.event_id, e.season_week) for e in current.editions] == [("event", 17)]
    assert missing.calendar_status == "ready" and missing.editions == ()
    assert older.branch_id == "fork" and older.revision_branch_id == "branch"
    assert current.saved_revision_id == "ancestor-revision"
    assert saved.model_dump(mode="json") == before


def test_edition_reads_real_result_only_if_published_in_same_saved_revision():
    saved = _state()
    unpublished = resolve_run_saved_tour_edition(
        **_args(saved, season_index=0), event_id="EVENT-OLD",
    )
    assert unpublished.published_result is None
    assert unpublished.lifecycle_status == "unavailable"
    assert not unpublished.edition.result_published

    ranking = _ranked()
    result = resolve_run_saved_tour_edition(
        **_args(saved, ranking=ranking), event_id="event",
    )
    assert result.edition.event_id == "event"
    assert result.published_result is not None
    assert result.published_result.champion_player_id == "A"
    assert result.published_result.matches[-1].match_id == "final"
    assert result.branch_id == "fork" and result.revision_branch_id == "branch"
    assert result.published_result.viewer_branch_id == "branch"
    assert result.lifecycle_status == "unavailable"
    with pytest.raises(KeyError, match="requested saved season"):
        resolve_run_saved_tour_edition(
            **_args(saved, ranking=ranking, season_index=0), event_id="event",
        )


def test_foreign_source_wrong_season_and_result_without_calendar_fail_closed():
    saved = _state()
    with pytest.raises(ValueError, match="Calendar belongs"):
        resolve_run_saved_tour_calendar(**_args(
            _state(branch_id="not-ancestor"),
        ))
    with pytest.raises(ValueError, match="Ranking belongs"):
        resolve_run_saved_tour_calendar(**_args(saved, ranking=_ranked().model_copy(
            update={"branch_id": "different"},
        )))
    with pytest.raises(ValueError, match="without Saved Calendar"):
        resolve_run_saved_tour_calendar(**_args(None, ranking=_ranked()))
    with pytest.raises(ValueError, match="requires a valid event"):
        resolve_run_saved_tour_edition(**_args(saved), event_id=" ")
    with pytest.raises(ValueError, match="season must be"):
        resolve_run_saved_tour_calendar(**_args(saved, season_index=50))


def test_duplicate_cross_package_events_keep_canonical_rejection():
    state = _state()
    first, second = state.entities[1], state.entities[3]
    # Same event_id in different packages/seasons must not be accepted even
    # if the requested season includes only one of those events.
    collision = state.model_copy(update={
        "entities": tuple(
            second.model_copy(update={
                "source_entity_id": first.source_entity_id,
                "payload": {**second.payload, "event_id": first.source_entity_id},
            }) if e is second else e for e in state.entities
        )
    })
    with pytest.raises(ValueError, match="duplicate event identity"):
        resolve_run_saved_tour_calendar(**_args(collision, season_index=0))
    with pytest.raises(ValueError, match="duplicate event identity"):
        resolve_run_saved_tour_calendar(**_args(collision, season_index=2))


def test_saved_edition_entry_draw_absence_and_foreign_source_fail_closed():
    saved = _state()
    none = resolve_run_saved_tour_edition(
        **_args(saved), event_id="event", simulation_slots=None,
    )
    assert none.entry_field is None and none.draw is None
    assert none.published_result is None

    foreign = {"entry_fields": [{
        "run_id": "run", "branch_id": "foreign", "event_id": "event",
    }]}
    with pytest.raises(ValueError, match="another Run/Branch"):
        resolve_run_saved_tour_edition(
            **_args(saved), event_id="event", simulation_slots=foreign,
        )

    orphan_draw = {"draw_authorities": [{
        "run_id": "run", "branch_id": "branch", "event_id": "event",
    }]}
    with pytest.raises(ValueError, match="no saved Entry Field"):
        resolve_run_saved_tour_edition(
            **_args(saved), event_id="event", simulation_slots=orphan_draw,
        )

    orphan_revision = {"draw_revisions": [{
        "run_id": "run", "branch_id": "branch", "event_id": "event",
    }]}
    with pytest.raises(ValueError, match="no original draw"):
        resolve_run_saved_tour_edition(
            **_args(saved), event_id="event", simulation_slots=orphan_revision,
        )

    # Filtering by exact event never allows unrelated Entry/Draw rows to appear
    # as an Edition's own authority.
    other = {"entry_fields": [{
        "run_id": "run", "branch_id": "foreign", "event_id": "other-event",
    }]}
    clean = resolve_run_saved_tour_edition(
        **_args(saved), event_id="event", simulation_slots=other,
    )
    assert clean.entry_field is None and clean.draw is None
