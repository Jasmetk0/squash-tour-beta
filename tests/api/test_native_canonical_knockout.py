"""Real HTTP/SQLite canonical Q/Main on an explicitly authored disposable source.

The source retains Gold24/Q16 or Platinum32/Q24 geometry, but explicitly changes
this test Edition to Unranked, one week and a recorded prior announcement. This
is NOT the original Ranked 80-Edition / 50-season acceptance.
"""

import itertools
import json

import pytest

from beta_engine.application.calendar_package_run_adapter import (
    CalendarPackageRunAdapter,
)
from beta_engine.application.run_working_draft_service import RunWorkingDraftService
from beta_engine.application.saved_fax_knockout_feeders import (
    SavedFaxKnockoutFeederService,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.tournaments.entry_field import TournamentEntryApplication
from beta_engine.domain.tournaments.fax_reference_player_draw import (
    fax_reference_entry_capacity,
)
from beta_engine.infrastructure.db.models import (
    BranchSavedRevisionModel,
    PublishedOfficialRankingModel,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
)
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
    tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.infrastructure import test_fax_reference_player_draw as fax

# Long real acceptance executes in the native Tour Ready/manual matrix.
pytestmark = pytest.mark.smoke


@pytest.fixture(scope="module")
def fax_source(tmp_path_factory):
    return fax.fax_source.__wrapped__(tmp_path_factory)


def authored_source(server, repo, source, size):
    view = inspect(server)
    clock = view["state"]["week"]["calendar"]
    event = next(e for e in source[0].events if e.main_draw_size == size)
    raw = event.model_dump(mode="json")
    raw.update(
        event_name="Disposable native acceptance, not original FAX",
        season_week=4,
        start_season_week=4,
        end_season_week=4,
        duration_in_season_weeks=1,
        calendar_year=2000,
        year_week=40,
        ranking_status="unranked",
        ranking_configuration_legacy=False,
        ranking_points_table={},
        point_distribution=None,
        event_level_overrides={
            **raw["event_level_overrides"],
            "native_announcement_week": {
                "calendar": clock,
                "season_index": 0,
                "week": 3,
            },
        },
    )
    entity = next(e for e in source[1].entities if e.source_entity_id == event.event_id)
    document = source[1].model_copy(
        update={
            "provenance": {"fixture": "explicit disposable Unranked same-week source"},
            "entities": tuple(
                e.model_copy(update={"payload": raw}) if e is entity else e
                for e in source[1].entities
            ),
        }
    )
    packages = fax.copied_state(document)
    event = next(
        e
        for e in CalendarPackageRunAdapter.project_calendar(
            packages, package_id=document.package_id
        ).calendar.events
        if e.event_id == event.event_id
    )
    players = tuple(p["player_id"] for p in view["players"])
    ranking = fax.ranking_snapshot(players)
    scope = {"run_id": "run", "branch_id": "branch", "event_id": event.event_id}
    with repo._session_factory.begin() as session:
        put_run_package_state(session, packages)
        session.add(
            PublishedOfficialRankingModel(
                run_id="run",
                branch_id="branch",
                week_ordinal=ranking.week.ordinal,
                snapshot_fingerprint=ranking.fingerprint,
                payload_json=ranking.model_dump_json(),
            )
        )
        session.flush()
        TournamentRankingSnapshotAuthorityStore(session).adopt(
            **scope, ranking_week=ranking.week, command_id="source-ranking"
        )
        TournamentEntryFieldStore(session).stage_initial(
            **scope,
            applications=tuple(
                TournamentEntryApplication(
                    application_id=f"{event.event_id}:app:{pid}",
                    **scope,
                    player_id=pid,
                    entry_window="main",
                    decision_slot_ordinal=10,
                    nr_tie_break_token="entry-" + pid,
                    eligible=True,
                )
                for pid in players[:-2]
            ),
            capacity=fax_reference_entry_capacity(event),
            command_id="source-field",
        )
        TournamentWildCardAuthorityStore(session).resolve(
            **scope, command_id="source-wc", original_wild_card_player_ids=players[-2:]
        )
        TournamentDrawInputAuthorityStore(session).commit(
            **scope, command_id="source-input", draw_seed=17
        )
        TournamentDrawAuthorityStore(session).generate(
            **scope, command_id="source-draw"
        )
    ids = itertools.count()
    owner = RunWorkingDraftService(
        repository=repo, id_factory=lambda kind: f"canonical-{kind}-{next(ids)}"
    )
    draft = owner.get_viewer_branch_draft(run_id="run", branch_id="branch")
    owner.save(
        run_id="run", branch_id="branch", expected_draft_version=draft.draft_version
    )
    view = inspect(server)
    plan = SavedFaxKnockoutFeederService(repo).prepare(
        **scope,
        season="2000/2001",
        expected_saved_revision_id=view["saved_head_revision_id"],
    )
    return plan


@pytest.mark.parametrize("size", [24, 32])
def test_actual_q_main_partial_save_restart_and_terminal(
    tmp_path, fax_source, size, monkeypatch
):
    db = f"sqlite:///{tmp_path / 'native-q-main.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(
            server, RunCalendar(61, 37, 2000, 3), count=40 if size == 24 else 56
        )
        plan = authored_source(server, repo, fax_source, size)
        schedule = {
            "qualification": [1, 2] if size == 24 else [1, 2, 3],
            "main": [4, 5, 6, 7, 8],
        }
        data = {
            "season": "2000/2001",
            "event_id": plan.source.draw.event_id,
            "source_plan_fingerprint": plan.fingerprint,
            "schedule": schedule,
        }
        before_adoption = inspect(server)
        if size == 24:
            for damaged in (
                {**data, "source_plan_fingerprint": "f" * 64},
                {**data, "schedule": {"qualification": [1], "main": [4, 5, 6, 7, 8]}},
                {**data, "season": None},
            ):
                status, rejected = _request(
                    "POST",
                    tour_url(server) + "/preview",
                    command(before_adoption, "adopt-saved-draw", data=damaged),
                )
                assert status == 409, rejected
            # Fail after the v13 checkpoint and adopted Tour have already been written.
            from beta_engine.application import calendar_tour_service

            cmd = command(before_adoption, "adopt-saved-draw", data=data)
            status, preview = _request("POST", tour_url(server) + "/preview", cmd)
            assert status == 200, preview

            def late_failure(name):
                if name == "after_tour_write":
                    raise ValueError("Injected late canonical adoption failure")

            with monkeypatch.context() as patch:
                patch.setattr(
                    calendar_tour_service, "_fault_injection_point", late_failure
                )
                status, rejected = _request(
                    "POST",
                    tour_url(server) + "/execute",
                    {
                        "command": cmd,
                        "expected_preview_fingerprint": preview["preview_fingerprint"],
                        "explicit_confirmation": True,
                    },
                )
                assert status == 409, rejected
            after_failure = inspect(server)
            assert after_failure["state"] == before_adoption["state"]
            assert (
                after_failure["checkpoint_fingerprint"]
                == before_adoption["checkpoint_fingerprint"]
            )
            assert (
                after_failure["saved_head_revision_id"]
                == before_adoption["saved_head_revision_id"]
            )
        execute(server, command(inspect(server), "adopt-saved-draw", data=data))
        # No sporting slot may run before the real public announcement / play week.
        assert (
            _request(
                "POST",
                tour_url(server) + "/preview",
                command(inspect(server), "next-match"),
            )[0]
            == 409
        )
        save_tour(server)
        # Only the normal public Week Transition publishes the explicit source date.
        for _ in range(2):
            execute(
                server,
                command(
                    inspect(server),
                    "transition",
                    name=f"announce-step-{inspect(server)['state']['week']['week']}",
                ),
            )
            save_tour(server)
        assert inspect(server)["state"]["week"]["week"] == 4
        assert (
            plan.source.draw.event_id
            in inspect(server)["state"]["transitions"][0]["public_event"][
                "announced_edition_ids"
            ]
        )
        result, request = execute(
            server, command(inspect(server), "next-match", name="first-canonical")
        )
        assert _request("POST", tour_url(server) + "/execute", request) == (201, result)
        before = inspect(server)
        slot = before["next_slot"]
        assert slot is not None
        save_tour(server)
        partial = inspect(server)
        if size == 24:
            # Warm ordinary source/prefix caches, then alter actual physical bytes.
            with repo._session_factory.begin() as session:
                row = session.get(
                    BranchSavedRevisionModel, plan.source_saved_revision_id
                )
                original = row.payload_json
                changed = json.loads(original)
                changed["run"]["display_name"] = "damaged actual Saved bytes"
                row.payload_json = json.dumps(changed)
            assert _request("GET", tour_url(server))[0] == 409
            with repo._session_factory.begin() as session:
                session.get(
                    BranchSavedRevisionModel, plan.source_saved_revision_id
                ).payload_json = original
            assert (
                inspect(server)["checkpoint_fingerprint"]
                == partial["checkpoint_fingerprint"]
            )

    with ApiServer(database_url=db) as server:
        view = inspect(server)
        assert view["checkpoint_fingerprint"] == partial["checkpoint_fingerprint"]
        assert view["next_slot"] == partial["next_slot"]
        if size == 24:
            from tests.api.test_calendar_sporting_horizon_extension import (
                extension,
                extend,
            )

            status, review = extension(server, 4)
            assert status == 200 and review["can_save"], review
            status, receipt = extend(server, review, "extend-partial-canonical")
            assert status == 200, receipt
            assert receipt["simulation_started"] is False
            assert inspect(server)["run_calendar"]["season_count"] == 4

        for i in range(12):
            view = inspect(server)
            if view["state"]["editions"][0]["tournament_fingerprint"]:
                break
            execute(server, command(view, "next-slot", name=f"remaining-slot-{i}"))
            save_tour(server)
        view = inspect(server)
        authority = view["state"]["editions"][0]
        assert authority["tournament_fingerprint"]
        evidence = view["edition_evidence"][plan.source.draw.event_id]
        assert len(evidence["matches"]) == (35 if size == 24 else 51)
        assert not evidence["results"]
        from beta_engine.application.calendar_continuation_service import (
            CalendarContinuationService,
        )

        final_id = plan.topology.terminal_group_id
        replay = CalendarContinuationService(
            server.app.state.runtime.repository
        ).replay(run_id="run", branch_id="branch", match_id=final_id)
        assert replay["exact_replay"]

        assert not set(plan.topology.bye_match_ids) & {
            m["match_id"] for m in evidence["matches"]
        }
        assert len({m["match_id"] for m in evidence["matches"]}) == len(
            evidence["matches"]
        )
        execute(
            server,
            command(view, "confirm-result", edition_id=plan.source.draw.event_id),
        )
        save_tour(server)
        execute(server, command(inspect(server), "transition"))
        save_tour(server)
        assert inspect(server)["state"]["week"]["week"] == 5
