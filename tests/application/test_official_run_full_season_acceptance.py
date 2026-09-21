"""Master §31.3 Official Run whole-season acceptance through production Admin boundaries."""

from __future__ import annotations

from sqlalchemy import select
import pytest

from beta_engine.api.deps import (
    get_season_match_service,
    get_season_point_awards_service,
)
from beta_engine.infrastructure.db.models import (
    PlayerSportingWeekStateModel,
    PublishedOfficialRankingModel,
)
from tests.api.test_initial_world_ranking_integration import _post_headers
from tests.api.test_saved_revision_history_api import ApiServer, _create_run, _request

from test_authoritative_empty_week_completion import (
    _remove_week_two_source_fixture,
)
from test_authoritative_simulation_api import (
    _server_state,
    confirm,
)
from test_authoritative_three_completed_weeks import _save_ranking


AUDIT = {
    "actor_label": "Official Run acceptance admin",
    "reason": "Exercise the canonical whole-season pre-alpha flow",
}


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


def _prepare_initial_ranking(ranking_root: str) -> None:
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
def test_official_run_completes_whole_season_reopens_and_rolls_to_next_season(
    tmp_path,
):
    server, week_one_package = _server_state(tmp_path)
    _remove_week_two_source_fixture(server)
    db_path = tmp_path / "api.sqlite"
    pool_path = tmp_path / "official-initial-pool.json"
    server.app.state.initial_player_pool_config_path = pool_path

    matches = server.app.dependency_overrides[get_season_match_service]()
    awards = server.app.dependency_overrides[get_season_point_awards_service]()
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
            display_name="Official Run whole-season acceptance",
        )
        world_root = (
            f"{server.base_url}/admin/players/runs/{run_id}/branches/{branch_id}"
            "/initial-world"
        )
        adoption = {
            "command_id": "official-full-season-adopt-world",
            "source_season": "2000/2001",
            "bootstrap_seed": 200001,
            "audit_label": "Official Run acceptance admin",
            "audit_reason": "Adopt production Initial World for Master §31.3",
            "official_run": True,
        }
        status, world_preview = _request(
            "POST",
            world_root + "/preview",
            adoption,
        )
        assert status == 200, world_preview
        assert world_preview["state"]["policies"] == [
            {
                "policy_id": "msa-official-2000-01",
                "best_n": 15,
                "tie_break_version": "result_profile_age_previous_token.v1",
            }
        ]
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
        assert {player["player_id"] for player in adopted["players"]} == set(
            participant_ids
        )
        revision = _save_initial_world(world_root)

        ranking_root, transition_root, sim_root = _roots(
            server, run_id, branch_id
        )
        _prepare_initial_ranking(ranking_root)
        revision = _save_ranking(None, ranking_root)

        for slot_index in (1, 2):
            position = _request("GET", sim_root + "/position")[1]
            assert position["current_week"] == {
                "season_index": 0,
                "week": 1,
            }
            status, simulated = _request(
                "POST",
                sim_root + "/simulate-next-slot",
                {
                    "command_id": f"official-full-season-week-1-slot-{slot_index}",
                    "run_id": run_id,
                    "branch_id": branch_id,
                    "expected_week": position["current_week"],
                    "expected_position_fingerprint": position[
                        "position_fingerprint"
                    ],
                    "expected_revision_id": revision,
                },
            )
            assert status == 200, simulated

        completed_week_one = _request("GET", sim_root + "/position")[1]
        assert completed_week_one["supported_tournament_complete"] is True
        revision = _advance_week(
            ranking_root=ranking_root,
            transition_root=transition_root,
            completed_week=1,
            revision=revision,
        )

        for week in range(2, 31):
            revision = _complete_empty_week(
                sim_root=sim_root,
                revision=revision,
                week=week,
            )
            revision = _advance_week(
                ranking_root=ranking_root,
                transition_root=transition_root,
                completed_week=week,
                revision=revision,
            )

        before_save = _request("GET", sim_root + "/position")[1]
        assert before_save["current_week"] == {
            "season_index": 0,
            "week": 31,
        }
        # Persist the exact mid-season world before shutting the process down.
        # Position identity intentionally includes the Saved Revision head and
        # Working Draft base/version, so compare reopen against the canonical
        # post-Save position rather than the stale pre-Save fingerprint.
        revision = _save_ranking(None, ranking_root)
        before_reopen = _request("GET", sim_root + "/position")[1]
        assert before_reopen["current_week"] == before_save["current_week"]
        assert before_reopen["position_fingerprint"] != before_save[
            "position_fingerprint"
        ]
        head_before_reopen = revision

    reopened = ApiServer(database_url=f"sqlite:///{db_path}")
    reopened.app.dependency_overrides[get_season_match_service] = lambda: matches
    reopened.app.dependency_overrides[get_season_point_awards_service] = lambda: awards

    with reopened:
        ranking_root, transition_root, sim_root = _roots(
            reopened, run_id, branch_id
        )
        loaded = _request("GET", sim_root + "/position")[1]
        assert loaded["current_week"] == saved_before_reopen["current_week"]
        assert loaded["position_fingerprint"] == saved_before_reopen["position_fingerprint"]
        revision = head_before_reopen

        for week in range(31, 61):
            revision = _complete_empty_week(
                sim_root=sim_root,
                revision=revision,
                week=week,
            )
            revision = _advance_week(
                ranking_root=ranking_root,
                transition_root=transition_root,
                completed_week=week,
                revision=revision,
            )

        revision = _complete_empty_week(
            sim_root=sim_root,
            revision=revision,
            week=61,
        )
        # Persist the full Week-61 Working Draft before Season Transition.
        # Ranking Save captures ranking, lifecycle, sporting, and simulation
        # components atomically, including the explicit empty-week evidence.
        revision = _save_ranking(None, ranking_root)
        status, preflight = _request(
            "GET",
            sim_root + "/season-transition/preflight",
        )
        assert status == 200, preflight
        assert preflight["completed_week"] == {
            "season_index": 0,
            "week": 61,
        }
        assert preflight["target_week"] == {
            "season_index": 1,
            "week": 1,
        }
        assert preflight["ready_for_execution"] is True, preflight[
            "state_blockers"
        ]
        assert preflight["saved_revision_id"] == revision

        status, configuration = _request(
            "POST",
            sim_root + "/season-transition/configuration/preview",
            {},
        )
        assert status == 200, configuration
        assert (
            configuration["configuration_fingerprint"]
            == preflight["default_configuration_fingerprint"]
        )

        status, rollover = _request(
            "POST",
            sim_root + "/season-transition/advance",
            {
                "command_id": "official-full-season-rollover",
                "expected_preflight_fingerprint": preflight[
                    "preflight_fingerprint"
                ],
                "expected_saved_revision_id": revision,
                "expected_draft_version": preflight["draft_version"],
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

        next_season_position = _request("GET", sim_root + "/position")[1]
        assert next_season_position["current_week"] == {
            "season_index": 1,
            "week": 1,
        }

        with reopened.app.state.runtime.repository._session_factory() as session:
            rankings = session.scalars(
                select(PublishedOfficialRankingModel)
                .where(
                    PublishedOfficialRankingModel.run_id == run_id,
                    PublishedOfficialRankingModel.branch_id == branch_id,
                )
                .order_by(PublishedOfficialRankingModel.week_ordinal)
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
        assert [row.week_ordinal for row in sporting] == list(range(62))
        assert rankings[-1].snapshot_fingerprint == rollover[
            "official_ranking_fingerprint"
        ]
        assert sporting[-1].fingerprint == rollover[
            "player_sporting_fingerprint"
        ]
