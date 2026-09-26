"""Master §31.3 Official Run whole-season acceptance through production Admin boundaries."""

from __future__ import annotations

from sqlalchemy import select
import json
import pytest

from beta_engine.api.deps import (
    get_season_match_service,
    get_season_point_awards_service,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.application.season_draw_service import SeasonDrawsRegistry
from beta_engine.application.season_event_results_service import SeasonEventResultsRegistry
from beta_engine.application.season_point_awards_service import SeasonPointAwardsRegistry
from beta_engine.world_packages import OFFICIAL_FAX_WORLD_ID
from beta_engine.infrastructure.db.authoritative_week_transition import (
    AuthoritativeWeekTransitionRunner,
)
from beta_engine.infrastructure.db.models import (
    PlayerLifecycleWeekStateModel,
    PlayerSportingWeekStateModel,
    PublishedOfficialRankingModel,
)
from tests.api.test_initial_world_ranking_integration import _post_headers
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request
from tests.support.world_packages import copy_builtin_world_packages

from test_authoritative_empty_week_completion import (
    _remove_week_two_source_fixture,
)
from test_authoritative_simulation_api import (
    _server_state,
    confirm,
)
from test_authoritative_three_completed_weeks import _save_ranking


# This file is the whole-season acceptance boundary for Master §31.3.
AUDIT = {
    "actor_label": "Official Run acceptance admin",
    "reason": "Exercise the canonical whole-season pre-alpha flow",
}


class _ForbiddenLegacyBackend:
    """Explode on any legacy result/template access after canonical preparation."""

    def __init__(self, label: str):
        self.label = label

    def __getattr__(self, name: str):
        raise AssertionError(
            f"authoritative Package-backed flow accessed forbidden legacy "
            f"{self.label} backend attribute '{name}'"
        )


def _custom_player(player_id: str, index: int, country_code: str) -> dict:
    ability = 72 + index
    potential = 84 + index
    return {
        "player_id": player_id,
        "name": f"Official Player {index + 1}",
        "country_code": country_code,
        "birth_year": 1977 + index,
        "birth_year_week": 8 + index,
        "current_ability": ability,
        "potential_ability": potential,
        "potential_tier": "A",
        "career_stage": "prime",
        "play_style": "balanced",
        "archetype": "all_court",
        "attributes": {
            "technique": ability,
            "movement": ability - 1,
            "physical": ability,
            "mental": ability + 1,
            "consistency": ability,
            "clutch": ability - 1,
            "recovery": ability,
        },
        "hidden_career_traits": {
            "potential_ceiling": potential,
            "growth_curve": "steady",
            "professionalism": 0.8,
            "ambition": 0.7,
            "travel_tolerance": 0.6,
            "schedule_aggression": 0.5,
            "injury_proneness": 0.2,
            "resilience": 0.7,
        },
        "reason": "Master §31.3 Official Run acceptance fixture",
        "actor": "acceptance-admin",
    }


def _save_initial_world(world_root: str) -> str:
    preview = _request("GET", world_root + "/save/preview")[1]
    status, saved = _request(
        "POST",
        world_root + "/save",
        {
            "expected_draft_version": preview["draft_version"],
            "expected_initial_world_fingerprint": preview[
                "initial_world_fingerprint"
            ],
        },
    )
    assert status == 201, saved
    return saved["saved_revision"]["revision_id"]


def _prepare_initial_ranking(ranking_root: str) -> str:
    payload = {
        "command_id": "official-full-season-initial-ranking",
        "audit": AUDIT,
    }
    status, preview = _request(
        "POST",
        ranking_root + "/prepare/initial/derived/preview",
        payload,
    )
    assert status == 200, preview
    status, candidate = _post_headers(
        ranking_root + "/prepare/initial/derived",
        payload,
        {
            "X-Ranking-Preview-Fingerprint": preview["candidate"]["fingerprint"],
            "X-Ranking-Preview-Request": preview["request_fingerprint"],
        },
    )
    assert status == 201, candidate
    return candidate["fingerprint"]


def _derive_transition_authority(
    ranking_root: str,
    *,
    completed_week: int,
) -> None:
    payload = {
        "command_id": f"official-full-season-authority-{completed_week}",
        "audit": AUDIT,
    }
    status, preview = _request(
        "POST",
        ranking_root + "/transition-authorities/derived/preview",
        payload,
    )
    assert status == 200, preview
    status, authority = _post_headers(
        ranking_root + "/transition-authorities/derived",
        payload,
        {
            "X-Ranking-Transition-Authority-Fingerprint": preview[
                "authority_fingerprint"
            ]
        },
    )
    assert status == 201, authority


def _advance_week(
    *,
    ranking_root: str,
    transition_root: str,
    completed_week: int,
    revision: str,
) -> str:
    _derive_transition_authority(
        ranking_root,
        completed_week=completed_week,
    )
    status, preview = _request(
        "POST",
        transition_root + "/derived/preview",
        {"command_id": f"official-full-season-transition-{completed_week}"},
    )
    assert status == 200, preview
    assert preview["command"]["completed_week"] == {
        "season_index": 0,
        "week": completed_week,
    }
    assert preview["command"]["target_week"] == {
        "season_index": 0,
        "week": completed_week + 1,
    }
    assert confirm(transition_root, preview["command"], preview)[0] == 201
    # The next week's canonical work remains in the clean Working Draft until
    # an explicit acceptance checkpoint Save. The Saved head therefore stays
    # unchanged across ordinary draft-only Week Transitions.
    return revision


def _complete_empty_week(
    *,
    sim_root: str,
    revision: str,
    week: int,
) -> str:
    position = _request("GET", sim_root + "/position")[1]
    assert position["current_week"] == {"season_index": 0, "week": week}
    status, completed = _request(
        "POST",
        sim_root + "/empty-week/complete",
        {
            "command_id": f"official-full-season-empty-{week}",
            "expected_week": position["current_week"],
            "expected_position_fingerprint": position["position_fingerprint"],
            "expected_revision_id": revision,
            "operator_label": "Official Run acceptance admin",
            "audit_reason": "Explicitly close a Calendar-proven event-free week",
        },
    )
    assert status == 201, completed
    assert completed["competitive_match_count"] == 0
    # Keep the completed evidence in the clean Working Draft. The next explicit
    # acceptance checkpoint Save persists it together with the accumulated world.
    return revision


def _roots(server: ApiServer, run_id: str, branch_id: str) -> tuple[str, str, str]:
    ranking_root = (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        "/ranking-candidates"
    )
    transition_root = (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        "/week-transitions"
    )
    sim_root = (
        f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}"
        "/authoritative-simulation"
    )
    return ranking_root, transition_root, sim_root


@pytest.mark.pr_critical
def test_canonical_next_week_finishes_week_one_and_publishes_week_two(
    tmp_path,
    monkeypatch,
):
    server, week_one_package = _server_state(tmp_path)
    pool_path = tmp_path / "next-week-initial-pool.json"
    server.app.state.initial_player_pool_config_path = pool_path
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

    with server:
        status, countries = _request("GET", server.base_url + "/world/countries")
        assert status == 200, countries
        country_code = countries["countries"][0]["code"]
        for index, player_id in enumerate(participant_ids):
            status, created = _request(
                "POST",
                server.base_url + "/admin/players/custom",
                _custom_player(player_id, index, country_code),
            )
            assert status == 200, created

        run_id, branch_id, revision = _create_run(
            server,
            display_name="Canonical Next Week acceptance",
        )
        world_root = (
            f"{server.base_url}/admin/players/runs/{run_id}/branches/{branch_id}"
            "/initial-world"
        )
        adoption = {
            "command_id": "next-week-adopt-world",
            "source_season": "2000/2001",
            "bootstrap_seed": 200001,
            "audit_label": "Next Week acceptance admin",
            "audit_reason": "Prepare canonical Next Week acceptance",
            "official_run": True,
        }
        status, world_preview = _request(
            "POST",
            world_root + "/preview",
            adoption,
        )
        assert status == 200, world_preview
        status, adopted = _post_headers(
            world_root,
            adoption,
            {
                "X-Initial-World-Preview-Fingerprint": world_preview[
                    "fingerprint"
                ]
            },
        )
        assert status == 201, adopted
        revision = _save_initial_world(world_root)

        ranking_root, _, sim_root = _roots(server, run_id, branch_id)
        _prepare_initial_ranking(ranking_root)
        revision = _save_ranking(None, ranking_root)

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
                "request_id": "next-week-schedule",
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
        assert position["current_week"] == {"season_index": 0, "week": 1}
        assert position["current_slot_kind"] == "match"

        preview_request = {
            "command_id": "canonical-next-week-1",
            "operator_label": "Next Week acceptance admin",
            "audit_reason": "Advance the reviewed complete Week 1 range",
        }
        status, preview = _request(
            "POST",
            sim_root + "/next-week/preview",
            preview_request,
        )
        assert status == 200, preview
        assert preview["schema_version"] == "authoritative_week_preview.v1"
        assert preview["week"] == {"season_index": 0, "week": 1}
        assert preview["target_week"] == {"season_index": 0, "week": 2}
        assert preview["target_slot_ordinals"]
        assert preview["ranking_authority_mode"] == "derived"
        assert preview["expected_revision_id"] == revision

        command = {
            **preview_request,
            "expected_week": preview["week"],
            "expected_position_fingerprint": preview[
                "expected_position_fingerprint"
            ],
            "expected_revision_id": preview["expected_revision_id"],
            "expected_preview_fingerprint": preview["preview_fingerprint"],
        }
        original_execute = AuthoritativeWeekTransitionRunner.execute
        injected = {"raised": False}

        def lose_parent_response(self, transition_command, **kwargs):
            result = original_execute(self, transition_command, **kwargs)
            if not injected["raised"]:
                injected["raised"] = True
                raise ValueError("lost response after committed Week Transition")
            return result

        monkeypatch.setattr(
            AuthoritativeWeekTransitionRunner,
            "execute",
            lose_parent_response,
        )
        status, lost = _request(
            "POST",
            sim_root + "/simulate-next-week",
            command,
        )
        assert status == 409, lost

        status, result = _request(
            "POST",
            sim_root + "/simulate-next-week",
            command,
        )
        assert status == 201, result
        assert result["schema_version"] == "authoritative_week_result.v1"
        assert result["status"] == "complete"
        assert result["completed_week"] == {"season_index": 0, "week": 1}
        assert result["target_week"] == {"season_index": 0, "week": 2}
        assert result["completed_slot_count"] == len(
            preview["target_slot_ordinals"]
        )
        assert result["ranking_authority_fingerprint"] == preview[
            "ranking_authority_fingerprint"
        ]
        assert result["world_event_kind"] == "week_transition_completed"
        assert _request(
            "POST",
            sim_root + "/simulate-next-week",
            command,
        ) == (201, result)

        status, after = _request("GET", sim_root + "/position")
        assert status == 200, after
        assert after["current_week"] == {"season_index": 0, "week": 2}

        with server.app.state.runtime.repository._session_factory() as session:
            week_two = session.get(
                PublishedOfficialRankingModel,
                (run_id, branch_id, RankingWeek(season_index=0, week=2).ordinal),
            )
            assert week_two is not None
            assert (
                week_two.snapshot_fingerprint
                == result["official_ranking_fingerprint"]
            )


@pytest.mark.pr_critical
def test_official_run_completes_whole_season_reopens_and_rolls_to_next_season(
    tmp_path,
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

        status, proposed = _request(
            "GET",
            sim_root + "/week-schedule/proposal",
        )
        assert status == 200, proposed
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

        status, preview = _request(
            "POST",
            sim_root + "/full-simulation/preview",
            full_review,
        )
        assert status == 200, preview
        assert (
            preview["schema_version"]
            == "authoritative_full_simulation_preview.v1"
        )
        assert preview["start_week"] == {"season_index": 0, "week": 1}
        assert preview["final_week"] == {"season_index": 49, "week": 61}
        assert preview["remaining_seasons_including_current"] == 50
        assert preview["remaining_weeks_including_current"] == 3050
        assert preview["expected_revision_id"] == revision
        assert preview["season_child_mode"] == "canonical_next_season"
        assert preview["final_season_mode"] == "canonical_final_run_closure"

        full_command = {
            **full_review,
            "expected_start_week": preview["start_week"],
            "expected_position_fingerprint": preview[
                "expected_position_fingerprint"
            ],
            "expected_revision_id": preview["expected_revision_id"],
            "expected_preview_fingerprint": preview["preview_fingerprint"],
        }
        status, progress = _request(
            "POST",
            sim_root + "/simulate-full-simulation",
            full_command,
        )
        assert status == 201, progress
        assert (
            progress["schema_version"]
            == "authoritative_full_simulation_progress.v1"
        )
        assert progress["status"] == "blocked"
        assert progress["checkpoint"] == "season_transition_save_required"
        assert progress["current_week"] == {"season_index": 0, "week": 61}
        assert progress["completed_season_count"] == 0
        assert progress["blockers"] == ["season_transition_save_required"]
        assert progress["child_progress"]["completed_week_count"] == 61

        # The durable parent and every already-completed child survive process reopen.
        boundary_position = _request("GET", sim_root + "/position")[1]
        assert boundary_position["current_week"] == {
            "season_index": 0,
            "week": 61,
        }
        boundary_head = revision

    reopened = ApiServer(database_url=f"sqlite:///{db_path}")
    reopened.app.dependency_overrides[get_season_match_service] = lambda: matches
    reopened.app.dependency_overrides[get_season_point_awards_service] = lambda: awards

    with reopened:
        ranking_root, transition_root, sim_root = _roots(
            reopened, run_id, branch_id
        )
        reopened_package_root = (
            f"{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/packages"
        )
        status, reopened_calendar = _request(
            "GET",
            reopened_package_root + "/calendar/calendar-2000-2001",
        )
        assert status == 200, reopened_calendar
        assert reopened_calendar["season"] == "2000/2001"
        assert week_one_package.event_id in {
            event["event_id"]
            for event in reopened_calendar["calendar"]["events"]
        }

        loaded = _request("GET", sim_root + "/position")[1]
        assert loaded["current_week"] == boundary_position["current_week"]

        # Exact retry before Save stays on the same explicit checkpoint.
        status, retry_before_save = _request(
            "POST",
            sim_root + "/simulate-full-simulation",
            full_command,
        )
        assert status == 201, retry_before_save
        assert (
            retry_before_save["checkpoint"]
            == "season_transition_save_required"
        )
        assert retry_before_save["completed_season_count"] == 0
        assert retry_before_save["child_progress"]["completed_week_count"] == 61

        # Persist the exact Week-61 world. Full Simulation and its nested
        # Next Season child must observe the new head rather than hiding a Save.
        revision = _save_ranking(None, ranking_root)
        assert revision != boundary_head

        status, transition_checkpoint = _request(
            "POST",
            sim_root + "/simulate-full-simulation",
            full_command,
        )
        assert status == 201, transition_checkpoint
        assert transition_checkpoint["status"] == "blocked"
        assert (
            transition_checkpoint["checkpoint"]
            == "season_transition_review_required"
        )
        transition_preflight = transition_checkpoint[
            "season_transition_preflight"
        ]
        assert transition_preflight["completed_week"] == {
            "season_index": 0,
            "week": 61,
        }
        assert transition_preflight["target_week"] == {
            "season_index": 1,
            "week": 1,
        }
        assert transition_preflight["ready_for_execution"] is True
        assert transition_preflight["saved_revision_id"] == revision

        status, configuration = _request(
            "POST",
            sim_root + "/season-transition/configuration/preview",
            {},
        )
        assert status == 200, configuration
        assert (
            configuration["configuration_fingerprint"]
            == transition_preflight["default_configuration_fingerprint"]
        )

        status, rollover = _request(
            "POST",
            sim_root + "/season-transition/advance",
            {
                "command_id": "official-full-season-rollover",
                "expected_preflight_fingerprint": transition_preflight[
                    "preflight_fingerprint"
                ],
                "expected_saved_revision_id": revision,
                "expected_draft_version": transition_preflight[
                    "draft_version"
                ],
                "configuration": configuration["configuration"],
                "season_saved_revision_id": "official-full-season-s1-revision",
                "audit_event_id": "official-full-season-s1-audit",
            },
        )
        assert status == 201, rollover
        assert rollover["target_week"] == {
            "season_index": 1,
            "week": 1,
        }
        assert rollover["world_event_kind"] == "season_transition_completed"

        # The exact same outer parent observes the reviewed Season Transition,
        # completes its Season-0 child exactly once and continues into Season 1.
        status, full_progress = _request(
            "POST",
            sim_root + "/simulate-full-simulation",
            full_command,
        )
        assert status == 201, full_progress
        assert (
            full_progress["schema_version"]
            == "authoritative_full_simulation_progress.v1"
        )
        assert full_progress["status"] == "blocked"
        assert full_progress["completed_seasons"] == [0]
        assert full_progress["completed_season_count"] == 1
        assert full_progress["current_week"] == {
            "season_index": 1,
            "week": 1,
        }
        assert full_progress["checkpoint"] in {
            "season_preparation_required",
            "week_preparation_required",
            "entry_process_required",
        }

        next_season_position = _request("GET", sim_root + "/position")[1]
        assert next_season_position["current_week"] == {
            "season_index": 1,
            "week": 1,
        }

        # Destroy the legacy active-player compatibility registry. The current
        # Season-1 Entry roster must still be reconstructed entirely from Run-owned
        # lifecycle/sporting/player-profile authority.
        legacy_registry = matches.active_players_service._load_registry()
        legacy_registry.players_by_season.clear()
        legacy_registry.bootstrap_metadata_by_season.clear()
        matches.active_players_service._save_registry(legacy_registry)

        status, season_two_entry_roster = _request(
            "GET",
            sim_root + "/entry-roster",
        )
        assert status == 200, season_two_entry_roster
        assert season_two_entry_roster["week"] == {
            "season_index": 1,
            "week": 1,
        }
        assert season_two_entry_roster["season"] == "2001/2002"
        assert season_two_entry_roster["source"] == (
            "run_owned_lifecycle_sporting_profiles.v1"
        )
        assert set(generated_ids).issubset(
            set(season_two_entry_roster["player_ids"])
        )
        assert all(
            player["season"] == "2001/2002"
            for player in season_two_entry_roster["players"]
        )

        with reopened.app.state.runtime.repository._session_factory() as session:
            rankings = session.scalars(
                select(PublishedOfficialRankingModel)
                .where(
                    PublishedOfficialRankingModel.run_id == run_id,
                    PublishedOfficialRankingModel.branch_id == branch_id,
                )
                .order_by(PublishedOfficialRankingModel.week_ordinal)
            ).all()
            lifecycle = session.scalars(
                select(PlayerLifecycleWeekStateModel)
                .where(
                    PlayerLifecycleWeekStateModel.run_id == run_id,
                    PlayerLifecycleWeekStateModel.branch_id == branch_id,
                )
                .order_by(PlayerLifecycleWeekStateModel.week_ordinal)
            ).all()
            sporting = session.scalars(
                select(PlayerSportingWeekStateModel)
                .where(
                    PlayerSportingWeekStateModel.run_id == run_id,
                    PlayerSportingWeekStateModel.branch_id == branch_id,
                )
                .order_by(PlayerSportingWeekStateModel.week_ordinal)
            ).all()

        assert [row.week_ordinal for row in rankings] == list(range(62))
        assert [row.week_ordinal for row in lifecycle] == list(range(62))
        assert [row.week_ordinal for row in sporting] == list(range(62))

        season_two_lifecycle = json.loads(lifecycle[-1].payload_json)
        season_two_sporting = json.loads(sporting[-1].payload_json)
        active_lifecycle_ids = {
            player["player_id"]
            for player in season_two_lifecycle["players"]
            if player["status"] == "active"
        }
        sporting_ids = {
            player["player_id"] for player in season_two_sporting["players"]
        }
        assert set(season_two_entry_roster["player_ids"]) == (
            active_lifecycle_ids & sporting_ids
        )
        assert rankings[-1].snapshot_fingerprint == rollover[
            "official_ranking_fingerprint"
        ]
        assert sporting[-1].fingerprint == rollover[
            "player_sporting_fingerprint"
        ]

