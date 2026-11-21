"""Deterministic offline checks of real W12 HTTP cost diagnostic logic."""
import json

import pytest

from scripts.profile_w12_real_client_http_attribution import (
    _assert_real_sporting, _route_name, _summary,
)

pytestmark = pytest.mark.pr_critical


def test_route_attribution_names_real_native_inspect_preview_execute_and_save():
    endpoint = "http://127.0.0.1:8888/admin/runs/run/branches/branch/calendar-tour"
    assert _route_name("GET", endpoint, execute_index=0) == "inspection-get"
    assert _route_name("POST", endpoint + "/preview", execute_index=0) == "preview-post"
    assert _route_name("POST", endpoint + "/execute", execute_index=1) == "execute-first-post"
    assert _route_name("POST", endpoint + "/execute", execute_index=2) == "execute-idempotency-retry-post"
    assert _route_name("POST", endpoint + "/save", execute_index=0) == "manual-save-post"


def test_original_real_sporting_validation_does_not_assume_players_stay_unchanged():
    edition_ids = [
        f"load-w{week}-{i}" for week in (4, 5) for i in range(4)
    ]
    view = {
        "saved": True,
        "players": [{"player_id": f"p{i:03d}", "level": i} for i in range(256)],
        "state": {
            "week": {"season_index": 1, "week": 2},
            "editions": [
                {"edition": {"edition_id": eid}, "result_confirmed": True}
                for eid in edition_ids
            ],
        },
        "edition_evidence": {
            eid: {"matches": [{"match": n} for n in range(3)]}
            for eid in edition_ids
        },
    }
    result = _assert_real_sporting(view, week=2)
    assert result["original_completed_match_count"] == 24
    assert result["confirmed_editions"] == 8
    with pytest.raises(AssertionError):
        _assert_real_sporting(view, week=1)
    view["edition_evidence"][edition_ids[0]]["matches"].pop()
    with pytest.raises(AssertionError):
        _assert_real_sporting(view, week=2)


def test_summary_requires_same_real_sportrun_output_and_reports_unneeded_calls(tmp_path):
    for case, wall in (("A1", 120.0), ("B1", 75.0), ("B2", 85.0), ("A2", 100.0)):
        legacy = case.startswith("A")
        result = {
            "case": case,
            "total_wall_s": wall,
            "added_saved_payload_bytes": 47_000_000,
            "unchanged_256_player_24_match_evidence": {
                "players_sha256": "a" * 64,
                "edition_evidence_sha256": "b" * 64,
            },
            "calls": {
                "inspection-get": {"sum_wall_s": 40 if legacy else 20},
                "execute-idempotency-retry-post": {
                    "sum_wall_s": 30 if legacy else 0
                },
            },
        }
        (tmp_path / (case + ".json")).write_text(json.dumps(result))
    _summary(tmp_path)
    report = json.loads((tmp_path / "summary.json").read_text())
    assert report["legacy_median_total_wall_s"] == 110
    assert report["minimal_median_total_wall_s"] == 80
    assert report["legacy_extra_get_wall_s_median"] == 20
    assert report["legacy_duplicate_execute_wall_s_median"] == 30
    assert report["same_sporting_output_in_all_cases"]
    assert report["not_a_production_engine_speedup"]

    bad = json.loads((tmp_path / "B2.json").read_text())
    bad["unchanged_256_player_24_match_evidence"]["players_sha256"] = "z" * 64
    (tmp_path / "B2.json").write_text(json.dumps(bad))
    with pytest.raises(AssertionError, match="Sporting content"):
        _summary(tmp_path)
