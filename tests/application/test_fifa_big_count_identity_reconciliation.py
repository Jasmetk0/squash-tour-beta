from __future__ import annotations

import pytest

from scripts.reconcile_fifa_big_count_identities import build_report

pytestmark = pytest.mark.pr_critical


def test_big_count_identity_reconciliation_is_explicit_and_complete() -> None:
    report = build_report()

    assert report["row_count"] == 208
    assert report["unresolved"] == []
    assert report["duplicate_direct_targets"] == {}

    manual = {
        item["association"]
        for item in report["mappings"]
        if item["status"] == "manual_review"
    }
    assert manual == {"Netherlands Antilles", "Curacao", "Serbia", "Sudan"}

    aggregate_members = {
        item["association"]
        for item in report["mappings"]
        if item["status"] == "aggregate_member"
    }
    assert aggregate_members == {"England", "Scotland", "Wales", "Northern Ireland"}


def test_big_count_identity_special_cases_do_not_silently_collapse_geographies() -> None:
    report = build_report()
    by_association = {item["association"]: item for item in report["mappings"]}

    assert by_association["Tahiti"]["earth_code"] == "PYF"
    assert by_association["Puerto Rico"]["earth_code"] == "PRI"
    assert by_association["Chinese Taipei"]["earth_code"] == "TWN"
    assert by_association["Czech Republic"]["earth_code"] == "CZE"
    assert by_association["Swaziland"]["earth_code"] == "SWZ"
    assert by_association["FYR Macedonia"]["earth_code"] == "MKD"

    for association in ("Netherlands Antilles", "Curacao", "Serbia", "Sudan"):
        assert by_association[association]["earth_code"] is None


def test_big_count_uk_aggregate_is_sum_of_four_home_associations() -> None:
    report = build_report()
    aggregate = report["aggregates"]["GBR"]

    assert aggregate["source_associations"] == ["England", "Scotland", "Wales", "Northern Ireland"]
    assert aggregate["null_fields"] == []
    assert aggregate["values"]["All Players"] == 4850569
    assert aggregate["values"]["Registered players"] == 1703369
    assert aggregate["values"]["Clubs"] == 51966
