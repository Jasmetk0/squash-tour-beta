"""Production HTTP/SQLite birth transaction, Signed Save, retry and recovery."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.infrastructure.db.repositories import RunProspectRecord
from tests.api.test_calendar_population_sporting_checkpoint import restore
from tests.api.test_calendar_tour_flow import (
    command,
    create_edition,
    edition,
    execute,
    inspect,
    save_tour,
    setup,
    tour_url,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.application.test_calendar_native_prospect_intake import source_at
from tests.application.test_prospect_persistence import _record

pytestmark = pytest.mark.smoke


def sign_prospects(server, repo, clock, *, target_week=3, target_season=0):
    world = repo.get_initial_world(run_id="run", branch_id="branch")
    target = RunWeekPosition(
        calendar=clock, season_index=target_season, week=target_week
    )
    new = source_at(clock, target, pid="born-native-15")
    template = _record()
    record = RunProspectRecord(
        **(
            template.__dict__
            | {
                "prospect_id": new["prospect_id"],
                "run_id": "run",
                "world_id": world.world_package_id,
                "season_start_year": new["season_start_year"],
                "season_label": "2030",
                "season_week": new["season_week"],
                "calendar_year": new["calendar_year"],
                "year_week": new["year_week"],
                "birth_year": new["birth_year"],
                "birth_year_week": new["birth_year_week"],
                "age": 15,
                "country_code": new["country_code"],
                "status": "prospect",
                "source_type": "native_calendar_15yo_cohort",
                "cohort_policy_version": "native_calendar_15yo_cohort_v1",
                "profile_version": "prospect_profile_v1",
                "profile_seed": "profile",
                "development_seed": "development",
                "potential_seed": "potential",
                "profile_json": new["profile"],
                "development_json": new["development"],
                "potential_json": new["potential"],
            }
        )
    )
    repo.upsert_run_prospects([record])
    url = (
        server.base_url
        + "/admin/runs/run/branches/branch/authoritative-simulation/prospect-source/save"
    )
    code, review = _request("GET", url + "/preview")
    assert code == 200 and review["can_save"], review
    code, saved = _request(
        "POST",
        url,
        {
            "expected_draft_version": review["draft_version"],
            "expected_run_prospect_source_fingerprint": review[
                "run_prospect_source_fingerprint"
            ],
        },
    )
    assert code == 201, saved
    return saved["saved_revision"]


@pytest.mark.parametrize(
    "width,offset",
    [(52, 1), (61, 37), (80, 80), (2, 2)],
    ids=["earth", "fax", "extended", "short_year"],
)
def test_native_birth_week_is_atomic_signed_and_recoverable(
    tmp_path, monkeypatch, width, offset
):
    path = tmp_path / "native-week.db"
    database_url = f"sqlite:///{path}"
    clock = RunCalendar(width, offset, 2030, 3)
    with ApiServer(database_url=database_url) as server:
        repo, _ = setup(server, clock, 8)
        if width == 80:
            from tests.api.test_calendar_sporting_horizon_extension import (
                extend,
                extension,
            )

            code, review = extension(server, 5)
            assert code == 200 and review["can_save"], review
            assert extend(server, review)[0] == 200
        boundary = width == 2
        before_birth = sign_prospects(
            server,
            repo,
            clock,
            target_week=1 if boundary else 3,
            target_season=1 if boundary else 0,
        )
        view = inspect(server)
        assert (
            view["season_transition_blockers" if boundary else "transition_blockers"]
            == []
        )
        cmd = command(
            view,
            "season-transition" if boundary else "transition",
            name="real-native-birth",
        )
        code, preview = _request("POST", tour_url(server) + "/preview", cmd)
        assert code == 200, preview
        impact = preview["impact"]
        assert impact["native_transition"] and impact["admitted_player_ids"] == [
            "born-native-15"
        ]
        assert impact["sporting"]["player_count"] == 9
        assert "born-native-15" not in {
            r["player_id"] for r in impact["ranking"]["rows"]
        }
        request = {
            "command": cmd,
            "expected_preview_fingerprint": preview["preview_fingerprint"],
            "explicit_confirmation": True,
        }
        viewer_url = server.base_url + "/viewer/runs/run/calendar-tour"
        viewer_before = _request("GET", viewer_url)
        assert viewer_before[0] == 200, viewer_before
        assert (
            _request(
                "POST",
                tour_url(server) + "/preview",
                {**cmd, "data": {"invented": True}},
            )[0]
            == 409
        )
        if width == 61:
            from beta_engine.application import calendar_tour_service as service

            for seam in (
                "after_development_write",
                "after_health_write",
                "after_lifecycle_write",
                "after_ranking_and_public_event_staging",
                "after_tour_write",
                "after_native_replay",
            ):
                before = _dump(path)

                def fail(name, seam=seam):
                    if name == seam:
                        raise ValueError("late native fault " + name)

                with monkeypatch.context() as patch:
                    patch.setattr(service, "_fault_injection_point", fail)
                    code, failed = _request(
                        "POST", tour_url(server) + "/execute", request
                    )
                assert code == 409, failed
                assert _dump(path) == before
        code, result = _request("POST", tour_url(server) + "/execute", request)
        assert code == 201, result
        assert _request("POST", tour_url(server) + "/execute", request) == (201, result)
        assert _request("GET", viewer_url) == viewer_before
        changed = deepcopy(request)
        changed["command"]["seed"] += 1
        assert _request("POST", tour_url(server) + "/execute", changed)[0] == 409
        born = inspect(server)
        assert not born["saved"] and len(born["players"]) == 9
        assert born["state"]["schema_version"] == "calendar_tour_authority.v3"
        assert born["state"]["week"]["week"] == (1 if boundary else 3)
        assert born["state"]["week"]["season_index"] == (1 if boundary else 0)
        assert born["state"]["week"]["calendar"]["season_count"] == (
            5 if width == 80 else 3
        )
        code, player = _request("GET", tour_url(server) + "/players/born-native-15")
        assert code == 200, player
        assert player["lifecycle"]["age"] == 15
        saved_birth = save_tour(server)
        published = _request("GET", viewer_url)
        assert published[0] == 200, published
        assert published[1]["saved_revision_id"] == saved_birth["revision_id"]
        assert published[1]["official_ranking"] == impact["ranking"]
        assert repo.verify_branch_saved_revision_hash(
            revision_id=saved_birth["revision_id"]
        )
        if width == 52:
            from beta_engine.domain.run_packages import canonical_hash
            from beta_engine.infrastructure.db.models import CalendarTourAuthorityModel

            original_cp_origin = repo.get_branch_saved_revision(
                revision_id=before_birth["revision_id"]
            ).payload["content"]["calendar_player_sporting_checkpoint"]["state"][
                "source_saved_head"
            ]

            for attack in (
                "seed",
                "confirmation",
                "result",
                "health_origin",
                "foreign_origin",
                "wrong_saved_owner",
                "malformed_command",
            ):
                with repo._session_factory.begin() as session:
                    row = session.get(CalendarTourAuthorityModel, ("run", "branch"))
                    original = (row.payload_json, row.fingerprint)
                    raw = json.loads(row.payload_json)
                    receipt = raw["receipts"][-1]
                    if attack == "seed":
                        receipt["request"]["command"]["seed"] += 1
                    elif attack == "confirmation":
                        receipt["request"]["expected_preview_fingerprint"] = "0" * 64
                    elif attack == "result":
                        receipt["result"]["impact"]["admitted_player_ids"] = []
                    elif attack == "health_origin":
                        raw["native_root_health_state_count"] += 1
                    elif attack == "malformed_command":
                        receipt["request"]["command"] = []
                    else:
                        source_id = (
                            "missing-native-origin"
                            if attack == "foreign_origin"
                            else original_cp_origin
                        )
                        raw["native_root_saved_head"] = source_id
                        receipt["request"]["command"]["expected_saved_head"] = source_id
                        # Re-sign all self-attested receipt bytes. Only the
                        # independent actual Saved-lineage guard can reject it.
                        body = {
                            "schema_version": "calendar_tour_command_preview.v1",
                            "run_id": "run",
                            "branch_id": "branch",
                            "command": deepcopy(receipt["request"]["command"]),
                            "week": raw["native_root_tour"]["week"],
                            "edition": None,
                            "impact": deepcopy(receipt["result"]["impact"]),
                        }
                        receipt["request"]["expected_preview_fingerprint"] = (
                            canonical_hash(body)
                        )
                    row.payload_json = json.dumps(raw)
                    row.fingerprint = canonical_hash(raw)
                try:
                    code, rejected = _request("GET", tour_url(server))
                    assert code == 409, (attack, rejected)
                    if attack == "foreign_origin":
                        assert "Saved origin" in rejected["detail"]["message"]
                    if attack == "wrong_saved_owner":
                        assert "Saved Tour/checkpoint" in rejected["detail"]["message"]
                finally:
                    with repo._session_factory.begin() as session:
                        row = session.get(CalendarTourAuthorityModel, ("run", "branch"))
                        row.payload_json, row.fingerprint = original
        code, bad = _request(
            "POST",
            tour_url(server) + "/preview",
            command(inspect(server), "create-edition", name="unsupported"),
        )
        assert code == 409, bad
        saved_view = inspect(server)
        if width == 80:
            frozen = repo.get_branch_saved_revision(
                revision_id=saved_birth["revision_id"]
            )
            code, review = extension(server, 6)
            assert code == 200 and review["can_save"], review
            assert (
                extend(server, review, command_id="extend-after-native-birth")[0] == 200
            )
            assert (
                repo.get_branch_saved_revision(revision_id=saved_birth["revision_id"])
                == frozen
            )
            saved_view = inspect(server)
            assert saved_view["run_calendar"]["season_count"] == 6
            assert saved_view["state"]["week"]["calendar"]["season_count"] == 5
    with ApiServer(database_url=database_url) as restarted:
        assert inspect(restarted) == saved_view
        result, _ = execute(
            restarted,
            command(inspect(restarted), "transition", name="natural-after-birth"),
        )
        assert result["impact"]["admitted_player_ids"] == []
        assert result["impact"]["sporting"]["player_count"] == 9
        if width == 80:
            assert result["impact"]["target_week"]["calendar"]["season_count"] == 6
        after = save_tour(restarted)
        assert _request("POST", tour_url(restarted) + "/execute", request)[0] == 201
        restore(restarted, before_birth["revision_id"])
        assert len(inspect(restarted)["players"]) == 8
        restore(restarted, after["revision_id"])
        assert len(inspect(restarted)["players"]) == 9
        if width == 52:
            # A later annual/source edit cannot silently reinterpret the old
            # birth hash. The generic component Save must roll back too.
            original = repo.list_run_prospects(run_id="run")[0]
            assert repo.list_activated_run_prospect_ids(
                run_id="run", prospect_ids={original.prospect_id}
            ) == {original.prospect_id}
            before = _dump(path)
            with pytest.raises(ValueError, match="immutable"):
                repo.upsert_run_prospects(
                    [replace(original, display_name="Changed source")]
                )
            with pytest.raises(ValueError, match="immutable"):
                repo.delete_run_prospects_by_ids(
                    run_id="run", prospect_ids=[original.prospect_id]
                )
            assert _dump(path) == before
            future = source_at(
                clock,
                RunWeekPosition(calendar=clock, season_index=0, week=6),
                pid="future-native-source",
            )
            future_record = replace(
                original,
                prospect_id=future["prospect_id"],
                season_start_year=future["season_start_year"],
                season_week=future["season_week"],
                calendar_year=future["calendar_year"],
                year_week=future["year_week"],
                birth_year=future["birth_year"],
                birth_year_week=future["birth_year_week"],
                profile_json=future["profile"],
                development_json=future["development"],
                potential_json=future["potential"],
            )
            repo.upsert_run_prospects([future_record])
            try:
                source_url = (
                    restarted.base_url
                    + "/admin/runs/run/branches/branch/authoritative-simulation/prospect-source/save"
                )
                code, review = _request("GET", source_url + "/preview")
                assert code == 200 and review["can_save"], review
                before = _dump(path)
                code, rejected = _request(
                    "POST",
                    source_url,
                    {
                        "expected_draft_version": review["draft_version"],
                        "expected_run_prospect_source_fingerprint": review[
                            "run_prospect_source_fingerprint"
                        ],
                    },
                )
                assert code == 409, rejected
                assert _dump(path) == before
            finally:
                repo.delete_run_prospects_by_ids(
                    run_id="run", prospect_ids=[future_record.prospect_id]
                )
            assert len(inspect(restarted)["players"]) == 9


def test_native_birth_preserves_actual_edition_entry_awards_and_match_counts(tmp_path):
    clock = RunCalendar(52, 1, 2030, 3)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'ranked-birth.db'}") as server:
        repo, _ = setup(server, clock, 8)
        create_edition(server, "before-birthday", size=4)
        for n in (3, 4):
            execute(
                server, command(inspect(server), "transition", name=f"old-week-{n}")
            )
            save_tour(server)
        edition(server, "before-birthday", size=4)
        sign_prospects(server, repo, clock, target_week=5)
        result, _ = execute(
            server, command(inspect(server), "transition", name="ranked-birthday")
        )
        impact = result["impact"]
        assert impact["admitted_player_ids"] == ["born-native-15"]
        rows = impact["ranking"]["rows"]
        assert len(rows) == 4
        assert "born-native-15" not in {r["player_id"] for r in rows}
        assert max(r["points"] for r in rows) == 100
        saved = save_tour(server)
        raw = repo.get_branch_saved_revision(revision_id=saved["revision_id"]).payload
        cp = raw["content"]["calendar_player_sporting_checkpoint"]["state"]
        assert any(n > 0 for _, n in cp["native_weeks"][0]["advance"]["played_counts"])
        assert repo.verify_branch_saved_revision_hash(revision_id=saved["revision_id"])
