"""Explicit candidates are never equivalent to verified identities or profiles."""
import pytest

from scripts.audit_atp_2019_research import ROOT, load

pytestmark = pytest.mark.pr_critical
RESEARCH = ROOT / "research_2019"


def test_all_canonical_2019_occurrences_have_distinct_candidate_atp_ids():
    report = load(RESEARCH / "identity_crosswalk.json")
    inventory = load(RESEARCH / "inventory.json")
    canonical = {r["occurrence_id"]: r for y in inventory["years"] if y["year"] == 2019
                 for r in y["events"]}
    rows = report["rows"]
    assert len(rows) == len({r["atp_id"] for r in rows}) == 63
    assert {r["occurrence_id"] for r in rows} == canonical.keys()
    assert sum(r["identity_state"] == "previously_reviewed" for r in rows) == 4
    assert all(r["profile_state"] == "not_installed" for r in rows)
    for row in rows:
        assert row["external_start"] == canonical[row["occurrence_id"]]["main_start"]


def test_historical_host_is_not_replaced_by_stable_id():
    rows = {r["occurrence_id"]: r for r in load(RESEARCH / "identity_crosswalk.json")["rows"]}
    for series, slug in {"hong_kong": "pune", "dallas": "new-york",
                         "lyon": "marseille", "belgrade_clay_2021": "budapest",
                         "hangzhou": "zhuhai", "brussels": "antwerp"}.items():
        row = rows["atp_2019_" + series]
        assert row["external_slug"] == slug
        assert row["identity_state"] == "lineage_review_required"
        assert row["lineage_note"]


def test_preseason_points_table_preserves_blank_values_and_distinct_draw_sizes():
    evidence = load(RESEARCH / "points_source_evidence.json")
    rows = evidence["rows"]
    assert rows["atp_250_draw_32"][8:] == [12, None, 6]
    assert rows["atp_250_draw_48"][8:] == [5, None, 3]
    assert rows["atp_500_draw_32"][8:] == [20, None, 10]
    assert rows["atp_500_draw_48"][8:] == [10, None, 4]
    assert rows["atp_250_draw_32"][5] is None
    assert evidence["finals"]["undefeated_champion"] == 3*200+400+500
    assert evidence["source"]["raw_sha256"] is None
