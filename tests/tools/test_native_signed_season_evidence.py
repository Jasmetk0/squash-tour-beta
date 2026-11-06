"""Fast source-bound checks for actual Signed native Tour long-run evidence."""
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest

from tools.audit_native_signed_seasons import (
    EvidenceFailure, audit_signed_seasons, http_reader, main,
)

pytestmark = pytest.mark.pr_critical

HEAD = "saved-revision-100"
FP = "a" * 64
RANK = "b" * 64
ROOT = "/admin/runs/run/branches/branch/calendar-tour"


def season(index):
    champion, finalist = ("p1", "p2") if index % 2 == 0 else ("p2", "p1")
    return {
        "schema_version": "native_tour_signed_season_summary.v1",
        "run_id": "run", "branch_id": "branch",
        "source_tour_fingerprint": FP,
        "season_index": index, "season_label": f"S{index+1}",
        "weeks_per_season": 4,
        "boundary_command_id": f"real-signed-season-{index}",
        "completed_edition_count": 1,
        "editions": [{
            "edition_id": f"cup-{index}", "name": f"Real Cup {index}",
            "week": 3, "source_tournament_fingerprint": "c" * 64,
            "champion_player_id": champion, "finalist_player_id": finalist,
        }],
        "countries": [{
            "country_code": "CZE", "titles": 1, "finals": 1,
            "awarded_points": 160, "semifinals": 0, "quarterfinals": 0,
            "distinct_players": 2, "edition_appearances": 1,
        }],
        "players": [
            {"player_id": champion, "country_code": "CZE", "titles": 1,
             "finals": 0, "awarded_points": 100, "edition_appearances": 1},
            {"player_id": finalist, "country_code": "CZE", "titles": 0,
             "finals": 1, "awarded_points": 60, "edition_appearances": 1},
        ],
        "last_week_published_ranking": {
            "week": 4, "source_fingerprint": RANK,
            "top_players": [{"player_id": "p1", "rank": 1, "points": 100}],
        },
    }


def record(scope, metric, winners):
    return {
        "record_id": f"native_tour.{scope}.{metric}.v1",
        "scope": scope, "metric": metric, "value": winners[0],
        "holders": [{"entity_id": key} for key in winners[1]],
        "holder_history": [], "leaderboard": [],
        "leaderboard_total": len(winners[1]),
    }


def fixture():
    seasons = [season(0), season(1)]
    records = {
        "schema_version": "calendar_tour_signed_records_response.v1",
        "run_id": "run", "branch_id": "branch",
        "saved_head_revision_id": HEAD,
        "source_tour_fingerprint": FP,
        "as_of_season_index": 1, "from_season_index": 0,
        "country_code": None, "leaderboard_limit": 20,
        "completed_seasons": [0, 1], "completed_edition_count": 2,
        "source_seasons": [
            {
                "season_index": index, "season_label": f"S{index+1}",
                "boundary_command_id": f"real-signed-season-{index}",
                "completed_edition_count": 1,
                "source_tour_fingerprint": FP,
                "published_ranking_fingerprint": RANK,
            } for index in range(2)
        ],
        "records": [
            record("player", "titles", (1, ["p1", "p2"])),
            record("player", "finals", (1, ["p1", "p2"])),
            record("player", "awarded_points", (160, ["p1", "p2"])),
            record("country", "titles", (2, ["CZE"])),
            record("country", "finals", (2, ["CZE"])),
            record("country", "awarded_points", (320, ["CZE"])),
        ],
    }
    return {
        ROOT + "/records": records,
        ROOT + "/seasons/0": {
            "schema_version": "calendar_tour_season_comparison.v1",
            "run_id": "run", "branch_id": "branch",
            "saved_head_revision_id": HEAD, "selected": seasons[0],
            "comparison": None, "country_deltas": [],
        },
        ROOT + "/seasons/1": {
            "schema_version": "calendar_tour_season_comparison.v1",
            "run_id": "run", "branch_id": "branch",
            "saved_head_revision_id": HEAD, "selected": seasons[1],
            "comparison": None, "country_deltas": [],
        },
    }


def run(table, *, read=None, required=2, minimum=1):
    def fetch(path):
        return deepcopy(table[path])
    return audit_signed_seasons(
        read or fetch, run_id="run", branch_id="branch",
        required_seasons=required, minimum_completed_editions=minimum,
    )


def test_two_completed_real_edition_summaries_reconcile_with_all_six_records():
    table = fixture()
    calls = []
    def fetch(path):
        calls.append(path)
        return deepcopy(table[path])
    result = run(table, read=fetch)
    assert result["status"] == "SCOPED_EVIDENCE_PASS"
    assert result["not_a_prealpha_release"] is True
    assert result["required_completed_seasons"] == 2
    assert result["observed_completed_editions_all_seasons"] == 2
    assert result["saved_head_revision_id"] == HEAD
    assert [s["completed_edition_count"] for s in result["season_evidence"]] == [1, 1]
    assert [s["awarded_edition_points"] for s in result["season_evidence"]] == [160, 160]
    assert calls == [ROOT + "/records", ROOT + "/seasons/0",
                     ROOT + "/seasons/1", ROOT + "/records"]
    assert "World Tour Editions" in result["limitations"][0]


def test_in_progress_season_cannot_be_fabricated_from_two_closed_seasons():
    with pytest.raises(EvidenceFailure, match="Only 2 Signed seasons"):
        run(fixture(), required=50)


def test_80_planned_is_not_80_confirmed_and_minimum_is_a_real_gate():
    with pytest.raises(EvidenceFailure, match="actually confirmed Editions"):
        run(fixture(), minimum=80)


@pytest.mark.parametrize("change,reason", [
    (lambda x: x[ROOT + "/records"].update(saved_head_revision_id="wrong"),
     "another Saved Run/Branch/HEAD"),
    (lambda x: x[ROOT + "/records"].update(completed_seasons=[0, 0]),
     "missing, repeated or noncontiguous"),
    (lambda x: x[ROOT + "/records"]["source_seasons"][1].update(
        source_tour_fingerprint="other"), "disagrees"),
    (lambda x: x[ROOT + "/seasons/0"]["selected"].update(
        source_tour_fingerprint="other"), "differs"),
    (lambda x: x[ROOT + "/seasons/0"]["selected"].update(
        completed_edition_count=2), "count differs"),
    (lambda x: x[ROOT + "/seasons/0"]["selected"]["editions"].append(
        x[ROOT + "/seasons/0"]["selected"]["editions"][0]), "count differs"),
    (lambda x: x[ROOT + "/seasons/0"]["selected"]["editions"][0].update(
        finalist_player_id=None), "incomplete champion/finalist"),
    (lambda x: x[ROOT + "/seasons/0"]["selected"]["countries"][0].update(
        awarded_points=999), "awarded Edition points disagree"),
    (lambda x: x[ROOT + "/seasons/0"]["selected"]["players"][0].update(
        titles=2), "titles do not reconcile"),
    (lambda x: x[ROOT + "/seasons/0"]["selected"]["last_week_published_ranking"].update(
        week=3), "Missing actual final-week"),
    (lambda x: x[ROOT + "/seasons/0"].update(
        saved_head_revision_id="stale"), "another Saved Run/Branch/HEAD"),
    (lambda x: x[ROOT + "/records"]["source_seasons"][0].update(
        boundary_command_id="forged"), "boundary, ranking or completed count"),
    (lambda x: x[ROOT + "/records"]["records"][0].update(value=99),
     "historical record differs"),
    (lambda x: x[ROOT + "/records"]["records"][0].update(
        holders=[{"entity_id": "p1"}]), "co-holders differ"),
])
def test_forged_or_inconsistent_signed_aggregate_must_fail(change, reason):
    table = fixture()
    change(table)
    with pytest.raises(EvidenceFailure, match=reason):
        run(table)


def test_actual_pure_groups_v2_can_be_completed_without_fake_finalists():
    table = fixture()
    first = table[ROOT + "/seasons/0"]["selected"]
    first["schema_version"] = "native_tour_signed_season_summary.v2"
    first["editions"][0].update(champion_player_id=None, finalist_player_id=None)
    first["players"] = [
        {"player_id": "p1", "titles": 0, "finals": 0, "awarded_points": 100},
        {"player_id": "p2", "titles": 0, "finals": 0, "awarded_points": 60},
    ]
    first["countries"][0].update(titles=0, finals=0)
    # Adjust cumulative actual records to this confirmed no-finalist Edition.
    recs = table[ROOT + "/records"]["records"]
    recs[0].update(value=1, holders=[{"entity_id": "p2"}])
    recs[1].update(value=1, holders=[{"entity_id": "p1"}])
    recs[3].update(value=1, holders=[{"entity_id": "CZE"}])
    recs[4].update(value=1, holders=[{"entity_id": "CZE"}])
    evidence = run(table)
    assert evidence["season_evidence"][0]["nonfinal_group_editions"] == 1
    assert evidence["season_evidence"][0]["actual_champions"] == 0


def test_source_head_changes_mid_scan_fail_closed_even_when_all_rows_look_valid():
    table = fixture()
    seen = [0]
    def fetch(path):
        value = deepcopy(table[path])
        if path.endswith("/records"):
            seen[0] += 1
            if seen[0] > 1:
                value["saved_head_revision_id"] = "different-after-concurrent-save"
        return value
    with pytest.raises(EvidenceFailure, match="changed during audit"):
        run(table, read=fetch)


def test_http_reader_is_read_only_with_real_ephemeral_http_server():
    requests = []
    table = fixture()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(("GET", self.path))
            body = json.dumps(table[self.path]).encode("utf8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = audit_signed_seasons(
            http_reader(f"http://127.0.0.1:{server.server_port}", 3),
            run_id="run", branch_id="branch", required_seasons=2,
            minimum_completed_editions=1,
        )
        assert result["status"] == "SCOPED_EVIDENCE_PASS"
        assert len(requests) == 4
        assert all(method == "GET" for method, _ in requests)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_cli_stops_on_unavailable_signed_source_without_creating_evidence(tmp_path):
    output = tmp_path / "never-written.json"
    assert main(["--base-url", "not-a-url", "--run", "r", "--branch", "b",
                 "--output", str(output)]) == 1
    assert not output.exists()
