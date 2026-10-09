"""Real HTTP/SQLite single-tournament Saved Revision fork acceptance.

The fixture uses the same Run-owned World, Calendar, Admin reviewed submissions,
Draw, full rally engine and canonical point authorities as the full-season gate.
It deliberately stops after Week 1 so Fast CI never runs all 61 weeks.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

import beta_engine.infrastructure.db.repositories as repository_module
from beta_engine.infrastructure.db.models import RunBranchModel

from beta_engine.api.deps import get_season_match_service, get_season_point_awards_service
from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID
from beta_engine.application.season_draw_service import SeasonDrawsRegistry
from beta_engine.application.season_event_results_service import SeasonEventResultsRegistry
from beta_engine.application.season_point_awards_service import SeasonPointAwardsRegistry
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state
from beta_engine.infrastructure.db.models import (
    AuthoritativeWeekTransitionReceiptModel,
    AuthoritativeWorldEventModel,
)
from tests.api.test_initial_world_ranking_integration import _post_headers
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.support.world_packages import copy_builtin_world_packages
from test_official_run_full_season_acceptance import (
    _server_state,
    _remove_week_two_source_fixture,
    _ForbiddenLegacyBackend,
    _save_initial_world,
    _prepare_initial_ranking,
    _save_ranking,
    _roots,
)
from test_earth_world_package_run_integration import _advance_empty_week


@pytest.mark.pr_critical
def test_single_completed_run_owned_tournament_fork_reopen_and_continue(
    tmp_path, monkeypatch,
):
    server, week_one_package = _server_state(tmp_path)
    _remove_week_two_source_fixture(server)
    db_path = tmp_path / "api.sqlite"
    world_packages_root = copy_builtin_world_packages(tmp_path / "world-packages")
    server.app.state.world_packages_root = world_packages_root

    matches = server.app.dependency_overrides[get_season_match_service]()
    awards = server.app.dependency_overrides[get_season_point_awards_service]()
    server.app.state.season_calendar_registry_path = (
        awards.calendar_service.calendar_registry_path
    )
    participant_ids = tuple(
        dict.fromkeys(
            player_id
            for match in sorted(
                (
                    item
                    for item in week_one_package.main_draw_matches
                    if item.round_number == 1
                ),
                key=lambda item: item.bracket_position,
            )
            for player_id in (match.top_player_id, match.bottom_player_id)
        )
    )
    assert len(participant_ids) == 4

    full_review = {
        "command_id": "official-full-simulation-parent",
        "operator_label": "Official Run acceptance admin",
        "audit_reason": (
            "Advance the reviewed canonical Run through explicit season "
            "and final-closure boundaries"
        ),
    }

    with server:
        run_id, branch_id, revision = _create_run(
            server,
            display_name="Official Run whole-season acceptance",
        )

        package_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/packages"
        )
        source_world_root = (
            package_root + f"/source-world/{OFFICIAL_FAX_WORLD_ID}"
        )
        status, package_preview = _request(
            "POST", source_world_root + "/preview"
        )
        assert status == 200, package_preview
        status, applied_world = _request(
            "POST",
            source_world_root + "/confirm",
            {
                "command_id": "official-full-season-apply-world",
                "expected_head_revision_id": package_preview[
                    "saved_head_revision_id"
                ],
                "expected_draft_version": package_preview["draft_version"],
                "expected_state_fingerprint": package_preview[
                    "current_state_fingerprint"
                ],
                "expected_preview_fingerprint": package_preview[
                    "preview_fingerprint"
                ],
                "conflict_resolutions": {},
            },
        )
        assert status == 200, applied_world

        # Package application is its own reviewed Working Draft change. Save it
        # before adopting InitialWorld so the later component-only Save remains
        # narrow and cannot accidentally persist unrelated pending Package edits.
        save_url = (
            f"{server.base_url}/run-containers/{run_id}/branches/{branch_id}"
            "/working-draft/save"
        )
        status, saved_package = _request(
            "POST",
            save_url,
            {"expected_draft_version": applied_world["draft_version"]},
        )
        assert status == 201, saved_package
        revision = saved_package["saved_revision"]["revision_id"]

        source_calendar_root = package_root + "/source-calendar/2000-2001"
        status, calendar_preview = _request(
            "POST",
            source_calendar_root + "/preview",
        )
        assert status == 200, calendar_preview
        assert calendar_preview["document"]["package_type"] == "Calendar"
        assert (
            calendar_preview["document"]["package_id"]
            == "calendar-2000-2001"
        )
        status, applied_calendar = _request(
            "POST",
            source_calendar_root + "/confirm",
            {
                "command_id": "official-full-season-apply-calendar",
                "expected_head_revision_id": calendar_preview[
                    "saved_head_revision_id"
                ],
                "expected_draft_version": calendar_preview["draft_version"],
                "expected_state_fingerprint": calendar_preview[
                    "current_state_fingerprint"
                ],
                "expected_preview_fingerprint": calendar_preview[
                    "preview_fingerprint"
                ],
                "conflict_resolutions": {},
            },
        )
        assert status == 200, applied_calendar

        status, calendar_projection = _request(
            "GET",
            package_root + "/calendar/calendar-2000-2001",
        )
        assert status == 200, calendar_projection
        assert calendar_projection["season"] == "2000/2001"
        assert week_one_package.event_id in {
            event["event_id"]
            for event in calendar_projection["calendar"]["events"]
        }

        status, saved_calendar = _request(
            "POST",
            save_url,
            {"expected_draft_version": applied_calendar["draft_version"]},
        )
        assert status == 201, saved_calendar
        revision = saved_calendar["saved_revision"]["revision_id"]

        world_root = (
            f"{server.base_url}/admin/players/runs/{run_id}/branches/{branch_id}"
            "/initial-world"
        )
        generation = {
            "world_package_id": OFFICIAL_FAX_WORLD_ID,
            "season": "2000/2001",
            "seed": 200001,
            "target_pool_size": len(participant_ids),
        }
        adoption = {
            "command_id": "official-full-season-adopt-world",
            "generation": generation,
            "audit_label": "Official Run acceptance admin",
            "audit_reason": (
                "Adopt Run-owned Official FAX World generated players for Master §31.3"
            ),
            "official_run": True,
        }
        status, world_preview = _request(
            "POST",
            world_root + "/world-package/preview",
            adoption,
        )
        assert status == 200, world_preview
        assert world_preview["state"]["source_kind"] == "run_world_generated_pool.v1"
        assert world_preview["state"]["world_package_id"] == OFFICIAL_FAX_WORLD_ID
        assert world_preview["state"]["policies"] == [
            {
                "policy_id": "msa-official-2000-01",
                "best_n": 15,
                "tie_break_version": "result_profile_age_previous_token.v1",
            }
        ]
        generated_ids = tuple(
            sorted(player["player_id"] for player in world_preview["state"]["players"])
        )
        assert len(generated_ids) == len(participant_ids)

        status, adopted = _post_headers(
            world_root + "/world-package",
            adoption,
            {
                "X-Initial-World-Preview-Fingerprint": world_preview[
                    "fingerprint"
                ]
            },
        )
        assert status == 201, adopted
        assert {player["player_id"] for player in adopted["players"]} == set(
            generated_ids
        )
        assert adopted["run_world_pool_preview_fingerprint"] == world_preview[
            "state"
        ]["run_world_pool_preview_fingerprint"]
        revision = _save_initial_world(world_root)

        ranking_root, transition_root, sim_root = _roots(
            server, run_id, branch_id
        )
        initial_ranking_fingerprint = _prepare_initial_ranking(ranking_root)
        revision = _save_ranking(None, ranking_root)
        status, published_initial = _request(
            "POST",
            ranking_root + "/publish-initial",
            {
                "expected_ranking_fingerprint": initial_ranking_fingerprint,
            },
        )
        assert status == 201, published_initial
        assert published_initial["week"] == {
            "season_index": 0,
            "week": 1,
        }
        assert (
            published_initial["ranking_fingerprint"]
            == initial_ranking_fingerprint
        )
        assert published_initial["exact_retry"] is False

        status, published_retry = _request(
            "POST",
            ranking_root + "/publish-initial",
            {
                "expected_ranking_fingerprint": initial_ranking_fingerprint,
            },
        )
        assert status == 201, published_retry
        assert published_retry["ranking_fingerprint"] == initial_ranking_fingerprint
        assert published_retry["exact_retry"] is True

        event_id = week_one_package.event_id
        tournament_root = (
            f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            f"/tournaments/{event_id}"
        )
        ranking_authority_root = tournament_root + "/ranking-snapshot-authority"
        status, available_rankings = _request(
            "GET", ranking_authority_root + "/available"
        )
        assert status == 200, available_rankings
        assert available_rankings["source"] == "published_official_rankings.v1"
        assert available_rankings["publication_count"] == 1
        assert available_rankings["publications"] == [
            {
                "ranking_week": {"season_index": 0, "week": 1},
                "snapshot_fingerprint": initial_ranking_fingerprint,
                "ranked_row_count": 0,
                "policy_id": "msa-official-2000-01",
                "best_n": 15,
            }
        ]
        status, tournament_ranking = _request(
            "POST",
            ranking_authority_root,
            {
                "command_id": "official-week-1-ranking-authority",
                "ranking_week": {"season_index": 0, "week": 1},
            },
        )
        assert status == 201, tournament_ranking
        assert tournament_ranking["event_id"] == event_id
        assert tournament_ranking["ranking_week"] == {
            "season_index": 0,
            "week": 1,
        }

        explicit_entry_reviews = [
            {
                "event_id": event_id,
                "player_id": player_id,
                "target": "MAIN",
            }
            for player_id in sorted(generated_ids)
        ]
        status, entry_slot = _request(
            "POST",
            sim_root + "/entry-decision-slot/review",
            {
                "command_id": "official-week-1-entry-slot",
                "expected_week": {"season_index": 0, "week": 1},
                "expected_revision_id": revision,
                "decision_slot_ordinal": 1,
                "operator_label": "Official Run acceptance admin",
                "reason": "Review Week-1 tournament application intents",
                "reviews": explicit_entry_reviews,
            },
        )
        assert status == 201, entry_slot
        assert entry_slot["decision_mode"] == "explicit_admin_review.v1"
        assert entry_slot["decision_count"] == len(generated_ids)
        assert {
            decision["player_id"]
            for decision in entry_slot["authority"]["decisions"]
        } == set(generated_ids)

        status, entry_position = _request("GET", sim_root + "/position")
        assert status == 200, entry_position
        assert entry_position["current_slot_kind"] == "entry"
        assert entry_position["slot_ordinal"] == 1

        reviews = [
            {
                "event_id": decision["event_id"],
                "player_id": decision["player_id"],
                "outcome": "valid",
                "reasons": [],
            }
            for decision in sorted(
                entry_slot["authority"]["decisions"],
                key=lambda item: (item["event_id"], item["player_id"]),
            )
        ]
        status, validated_entry = _request(
            "POST",
            sim_root + "/entry-decision-slot/validation/review",
            {
                "command_id": "official-week-1-entry-validation",
                "expected_week": entry_slot["week"],
                "expected_revision_id": revision,
                "expected_position_fingerprint": entry_position[
                    "position_fingerprint"
                ],
                "decision_slot_ordinal": 1,
                "expected_entry_slot_fingerprint": entry_slot[
                    "slot_fingerprint"
                ],
                "operator_label": "Official Run acceptance admin",
                "reason": "Review Week-1 Run-owned Entry decisions",
                "reviews": reviews,
            },
        )
        assert status == 201, validated_entry
        assert validated_entry["valid_submission_count"] == len(generated_ids)

        entry_field_root = tournament_root + "/entry-field"
        status, entry_field = _request(
            "POST",
            entry_field_root + "/from-valid-submissions",
            {
                "command_id": "official-week-1-entry-field",
                "capacity": {
                    "main_draw_size": 4,
                    "qualification_draw_size": 0,
                    "qualifier_spots": 0,
                    "wild_card_slots": 0,
                    "bye_slots": 0,
                },
            },
        )
        assert status == 201, entry_field
        assert set(entry_field["direct_main_player_ids"]) == set(generated_ids)
        status, entry_field_state = _request("GET", entry_field_root)
        assert status == 200, entry_field_state
        assert set(entry_field_state["direct_main_player_ids"]) == set(generated_ids)

        # Week Schedule readiness must already see the Run-owned Calendar event before
        # any Draw exists. The canonical preparation state, not MatchPackage/Draw
        # existence, owns the blocker and next action.
        status, schedule_before_draw_input = _request(
            "GET",
            sim_root + "/week-schedule/preflight",
        )
        assert status == 200, schedule_before_draw_input
        assert schedule_before_draw_input["event_ids"] == [event_id]
        assert schedule_before_draw_input["group_ids"] == []
        assert schedule_before_draw_input["schedule_required"] is True
        assert schedule_before_draw_input["canonical_preparation_ready"] is False
        assert schedule_before_draw_input["can_propose_schedule"] is False
        assert schedule_before_draw_input["blockers"] == [
            f"{event_id}:draw_input_ready"
        ]
        assert (
            schedule_before_draw_input["canonical_preparation"]["tournaments"][0][
                "phase"
            ]
            == "draw_input_ready"
        )
        status, blocked_schedule_proposal = _request(
            "GET",
            sim_root + "/week-schedule/proposal",
        )
        assert status == 409, blocked_schedule_proposal
        assert "canonical tournament preparation draw_ready" in str(
            blocked_schedule_proposal
        )

        draw_root = tournament_root + "/draw"
        status, draw_input = _request(
            "POST",
            draw_root + "/commit-input",
            {
                "command_id": "official-week-1-draw-input",
                "run_id": run_id,
                "branch_id": branch_id,
                "event_id": event_id,
                "expected_field_fingerprint": entry_field_state["field_fingerprint"],
                "draw_seed": 200001,
            },
        )
        assert status == 200, draw_input
        assert draw_input["draw_input_committed"] is True

        status, schedule_before_draw_generation = _request(
            "GET",
            sim_root + "/week-schedule/preflight",
        )
        assert status == 200, schedule_before_draw_generation
        assert schedule_before_draw_generation["canonical_preparation_ready"] is False
        assert schedule_before_draw_generation["blockers"] == [
            f"{event_id}:draw_generation_ready"
        ]
        assert (
            schedule_before_draw_generation["canonical_preparation"]["tournaments"][0][
                "next_required_action"
            ]
            == "generate_draw"
        )

        status, generated_draw = _request(
            "POST",
            draw_root + "/generate",
            {
                "command_id": "official-week-1-generate-draw",
                "run_id": run_id,
                "branch_id": branch_id,
                "event_id": event_id,
                "expected_draw_input_fingerprint": draw_input[
                    "draw_input_fingerprint"
                ],
            },
        )
        assert status == 200, generated_draw
        assert generated_draw["initial_draw_generated"] is True

        status, draw_authority = _request("GET", draw_root + "/effective-authority")
        assert status == 200, draw_authority
        assert draw_authority["event_id"] == event_id
        assert {
            slot["player_id"]
            for slot in draw_authority["main"]["slots"]
            if slot["entrant_kind"] == "player"
        } == set(generated_ids)

        preparation_root = tournament_root + "/preparation"
        status, preparation_ready = _request("GET", preparation_root)
        assert status == 200, preparation_ready
        assert preparation_ready["phase"] == "draw_ready"
        assert preparation_ready["next_required_action"] == "none"
        assert preparation_ready["ready_for_match_schedule"] is True
        assert preparation_ready["authority_source"] == (
            "run_owned_db_authorities.v1"
        )
        assert (
            preparation_ready["effective_draw_fingerprint"]
            == generated_draw["draw_authority_fingerprint"]
        )

        # Destroy the live legacy Calendar source after the Run-owned Calendar and
        # Draw exist. Tournament adoption, point-authority freezing, empty-week proof
        # and whole-season simulation must now replay only from Run-owned evidence.
        legacy_calendars = awards.calendar_service._load_registry()
        legacy_calendars.calendars_by_season.clear()
        awards.calendar_service._save_registry(legacy_calendars)

        # Destroy every remaining file-backed tournament result/draw/award source and
        # replace service references with exploding sentinels. From this point the
        # canonical Package/Draw Run must close, rank and transition using DB-owned
        # authorities only.
        matches.draw_service._save_registry(SeasonDrawsRegistry())
        awards.result_service._save_registry(SeasonEventResultsRegistry())
        awards._save_registry(SeasonPointAwardsRegistry())
        awards.result_service = _ForbiddenLegacyBackend("result")
        awards.template_service = _ForbiddenLegacyBackend("template")
        awards.points_config_path = tmp_path / "forbidden-legacy-points.json"

        status, preparation_after_legacy_removal = _request(
            "GET", preparation_root
        )
        assert status == 200, preparation_after_legacy_removal
        assert preparation_after_legacy_removal == preparation_ready

        # Remove the old Week-1 MatchPackage source completely. From this point the
        # authoritative driver must derive its compatibility MatchPackage from the
        # Run-owned canonical Draw + Run-owned Calendar or the acceptance will fail.
        match_registry = matches._load_registry()
        match_registry.matches_by_event_id.pop(event_id, None)
        matches._save_registry(match_registry)
        assert event_id not in matches._load_registry().matches_by_event_id

        status, schedule_preflight = _request(
            "GET",
            sim_root + "/week-schedule/preflight",
        )
        assert status == 200, schedule_preflight
        assert schedule_preflight["canonical_preparation_ready"] is True
        assert schedule_preflight["can_propose_schedule"] is True
        assert schedule_preflight["blockers"] == []
        assert (
            schedule_preflight["canonical_preparation"]["event_ids"]
            == [event_id]
        )
        assert (
            schedule_preflight["canonical_preparation"]["tournaments"][0]["phase"]
            == "draw_ready"
        )
        assert (
            schedule_preflight["canonical_preparation"]["tournaments"][0][
                "effective_draw_fingerprint"
            ]
            == generated_draw["draw_authority_fingerprint"]
        )
        assert (
            schedule_preflight["canonical_preparation"]["authority_source"]
            == "run_owned_db_authorities.v1"
        )
        assert len(schedule_preflight["preflight_fingerprint"]) == 64

        status, proposed = _request(
            "GET",
            sim_root + "/week-schedule/proposal",
        )
        assert status == 200, proposed
        assert proposed["canonical_preparation"] == schedule_preflight[
            "canonical_preparation"
        ]
        status, adopted_schedule = _request(
            "POST",
            sim_root + "/week-schedule/adopt-proposal",
            {
                "request_id": "official-full-season-week-1-schedule",
                "expected_week": proposed["schedule"]["week"],
                "expected_schedule_fingerprint": proposed[
                    "schedule_fingerprint"
                ],
                "expected_position_fingerprint": proposed[
                    "position_fingerprint"
                ],
            },
        )
        assert status == 201, adopted_schedule

        status, position = _request("GET", sim_root + "/position")
        assert status == 200, position
        assert position["current_week"] == {
            "season_index": 0,
            "week": 1,
        }

        review = {
            "command_id": "one-tournament-week-one-next-week",
            "operator_label": "Run-owned tournament fork acceptance admin",
            "audit_reason": "Complete all reviewed Week-1 real tournament matches",
        }
        status, week_preview = _request(
            "POST", sim_root + "/next-week/preview", review,
        )
        assert status == 200, week_preview
        assert week_preview["target_slot_ordinals"]
        week_command = {
            **review,
            "expected_week": week_preview["week"],
            "expected_position_fingerprint": week_preview["expected_position_fingerprint"],
            "expected_revision_id": week_preview["expected_revision_id"],
            "expected_preview_fingerprint": week_preview["preview_fingerprint"],
        }
        status, completed = _request(
            "POST", sim_root + "/simulate-next-week", week_command,
        )
        assert status == 201, completed
        assert completed["status"] == "complete"
        assert completed["completed_week"] == {"season_index": 0, "week": 1}
        assert completed["target_week"] == {"season_index": 0, "week": 2}
        revision = _save_ranking(None, ranking_root)
        assert _request("GET", sim_root + "/position")[1]["current_week"] == {
            "season_index": 0, "week": 2
        }

    # Restart the actual API with the same persisted SQLite database. No mock
    # ranking, results, Slot ledger or manually populated SQL is used here.
    reopened = ApiServer(database_url=f"sqlite:///{db_path}")
    reopened.app.dependency_overrides[get_season_match_service] = lambda: matches
    reopened.app.dependency_overrides[get_season_point_awards_service] = lambda: awards
    with reopened:
        source_sim_root = (
            f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}"
            "/authoritative-simulation"
        )
        source_position = _request("GET", source_sim_root + "/position")[1]
        assert source_position["current_week"] == {
            "season_index": 0, "week": 2
        }
        repository = reopened.app.state.runtime.repository
        with repository._session_factory() as session:
            original_ranking = capture_ranking_revision_state(
                session, run_id=run_id, branch_id=branch_id
            )
            assert len(original_ranking.tournament_sources) == 1
            original_tournament = original_ranking.tournament_sources[0]
            assert original_tournament.canonical_result is not None
            assert original_tournament.canonical_awards is not None
            assert original_tournament.canonical_result.matches
            assert len(original_ranking.authoritative_transition_state["receipts"]) == 1

        # Force failure during the real SQLite installer. Every staged ranking,
        # player, Branch and audit row must roll back together.
        fork_url = f"{reopened.base_url}/run-containers/{run_id}/branches"
        original_install = repository_module.install_remapped_week_transition_audit

        def reject_install(*args, **kwargs):
            raise ValueError("injected atomic tournament audit installation failure")

        monkeypatch.setattr(
            repository_module, "install_remapped_week_transition_audit",
            reject_install,
        )
        try:
            rejected_status, rejected = _request(
                "POST", fork_url,
                {
                    "source_branch_id": branch_id,
                    "source_saved_revision_id": revision,
                    "display_name": "Rejected tournament fork",
                },
            )
            assert rejected_status == 409, rejected
        finally:
            monkeypatch.setattr(
                repository_module, "install_remapped_week_transition_audit",
                original_install,
            )
        with repository._session_factory() as session:
            assert session.scalars(
                select(RunBranchModel).where(
                    RunBranchModel.run_id == run_id,
                    RunBranchModel.display_name == "Rejected tournament fork",
                )
            ).all() == []
            assert capture_ranking_revision_state(
                session, run_id=run_id, branch_id=branch_id
            ).fingerprint == original_ranking.fingerprint

        status, fork = _request(
            "POST",
            f"{reopened.base_url}/run-containers/{run_id}/branches",
            {
                "source_branch_id": branch_id,
                "source_saved_revision_id": revision,
                "display_name": "One completed standard tournament fork",
            },
        )
        assert status == 201, fork
        target_branch_id = fork["branch_id"]
        assert target_branch_id != branch_id
        assert fork["saved_head_revision_id"] != revision

        with repository._session_factory() as session:
            target_ranking = capture_ranking_revision_state(
                session, run_id=run_id, branch_id=target_branch_id
            )
            assert len(target_ranking.tournament_sources) == 1
            assert target_ranking.tournament_sources[0].binding.branch_id == target_branch_id
            assert (
                target_ranking.tournament_sources[0].canonical_result.champion_player_id
                == original_tournament.canonical_result.champion_player_id
            )
            assert target_ranking.entries[-1].snapshot.rows != ()
            assert (
                target_ranking.entries[-1].snapshot.fingerprint
                != original_ranking.entries[-1].snapshot.fingerprint
            )
            for model in (
                AuthoritativeWeekTransitionReceiptModel,
                AuthoritativeWorldEventModel,
            ):
                assert len(session.scalars(select(model).where(
                    model.run_id == run_id, model.branch_id == target_branch_id
                )).all()) == 1

        target_sim_root = (
            f"{reopened.base_url}/admin/runs/{run_id}/branches/{target_branch_id}"
            "/authoritative-simulation"
        )
        assert _request("GET", target_sim_root + "/position")[1][
            "current_week"
        ] == {"season_index": 0, "week": 2}

        continuation_revision = _advance_empty_week(
            reopened,
            run_id=run_id,
            branch_id=target_branch_id,
            revision=fork["saved_head_revision_id"],
            week=2,
        )
        assert continuation_revision != fork["saved_head_revision_id"]
        assert _request("GET", target_sim_root + "/position")[1][
            "current_week"
        ] == {"season_index": 0, "week": 3}
        assert _request("GET", source_sim_root + "/position")[1] == source_position

        with repository._session_factory() as session:
            assert capture_ranking_revision_state(
                session, run_id=run_id, branch_id=branch_id
            ).fingerprint == original_ranking.fingerprint
            target = capture_ranking_revision_state(
                session, run_id=run_id, branch_id=target_branch_id
            )
            assert len(target.authoritative_transition_state["receipts"]) == 2
