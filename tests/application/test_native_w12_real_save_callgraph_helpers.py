"""Focused deterministic tests for the independent Saved callgraph diagnostic."""
import cProfile

from scripts.profile_native_w12_real_save_cpu_callgraph import (
    _category, _format_profile, _verify_actual_sport,
)


def test_exclusive_and_inclusive_are_distinguished_and_methods_present():
    def leaf():
        return sum(range(80))
    def upper():
        for _ in range(20):
            leaf()
    p = cProfile.Profile()
    p.enable()
    upper()
    p.disable()
    report = _format_profile(p, limit=100)
    assert any(x["function"] == "upper" for x in report["top_inclusive"])
    assert any(x["function"] == "leaf" for x in report["top_exclusive"])
    assert report["profile_total_exclusive_elapsed_s"] >= 0
    assert "OVERLAP" in report["warning"]
    assert sum(report["exclusive_by_module_category_s"].values()) >= 0


def test_real_original_edition_match_checks_ignore_extra_calendar_fields():
    view = {
        "players": [{"player_id": f"P-{i}"} for i in range(256)],
        "state": {
            "week": {"season_index": 1, "week": 2, "ordinal": 54},
            "editions": [
                {"edition": {"edition_id": f"load-w{week}-{i}"},
                 "result_confirmed": True}
                for week in (4, 5) for i in range(4)
            ],
        },
        "edition_evidence": {
            f"load-w{week}-{i}": {
                "matches": [dict(match_number=m) for m in range(3)]
            }
            for week in (4, 5) for i in range(4)
        },
    }
    assert _verify_actual_sport(view, 2)["original_real_matches"] == 24


def test_profile_categories_are_exclusive_not_overlapping():
    assert _category("/usr/lib/python3.11/json/encoder.py") == "json"
    assert _category("/site-packages/pydantic/main.py") == "pydantic"
    assert _category("/src/beta_engine/domain/run_revisions.py") == "saved_revision_and_database_application"
    assert _category("/src/beta_engine/infrastructure/db/repositories.py") == "saved_revision_and_database_application"
    assert _category("/src/beta_engine/domain/tournaments/calendar_global_slots.py") == "sporting_domain"
