from __future__ import annotations

import pytest

from scripts.reconcile_fifa_professional_2023_identities import build_report

pytestmark = pytest.mark.pr_critical


def test_professional_2023_identity_reconciliation_is_page_aware_and_complete() -> None:
    report = build_report()

    assert report["row_count"] == 211
    assert report["unique_association_label_count"] == 210
    assert report["unresolved"] == []
    assert report["duplicate_direct_targets"] == {}
    assert report["aggregate_member_count"] == 4
    assert report["manual_review_count"] == 1
    assert report["safe_earth_entity_count"] == 207


def test_professional_2023_preserves_kuwait_kyrgyzstan_identity_conflict() -> None:
    report = build_report()
    by_page = {item["pdf_page"]: item for item in report["mappings"]}

    assert by_page[37]["association"] == "KUWAIT"
    assert by_page[37]["earth_code"] == "KWT"
    assert by_page[37]["status"] in {"exact_normalized_name", "explicit_map"}

    assert by_page[38]["association"] == "KUWAIT"
    assert by_page[38]["status"] == "manual_review"
    assert by_page[38]["earth_code"] is None
    assert by_page[38]["candidate_earth_code"] == "KGZ"
    assert "Kyrgyzstan" in by_page[38]["identity_note"]


def test_professional_2023_special_association_names_map_to_earth_catalog() -> None:
    report = build_report()
    by_association = {
        item["association"]: item
        for item in report["mappings"]
        if item["status"] not in {"aggregate_member", "manual_review"}
    }

    assert by_association["BUTHAN"]["earth_code"] == "BTN"
    assert by_association["IR IRAN"]["earth_code"] == "IRN"
    assert by_association["CHINESE TAIPEI"]["earth_code"] == "TWN"
    assert by_association["TAHITI"]["earth_code"] == "PYF"
    assert by_association["PUERTO RICO"]["earth_code"] == "PRI"
    assert by_association["KOSOVO"]["earth_code"] == "XKX"
    assert by_association["TÜRKIYE"]["earth_code"] == "TUR"


def test_professional_2023_uk_aggregate_keeps_missing_values_null() -> None:
    report = build_report()
    aggregate = report["aggregates"]["GBR"]

    assert aggregate["source_associations"] == [
        "ENGLAND",
        "SCOTLAND",
        "WALES",
        "NORTHERN IRELAND",
    ]

    players = aggregate["fields"]["professional_players"]
    assert players["value"] is None
    assert players["known_partial_sum"] == 10_791
    assert players["missing_associations"] == ["NORTHERN IRELAND"]

    clubs = aggregate["fields"]["professional_clubs"]
    assert clubs["value"] is None
    assert clubs["known_partial_sum"] == 181
    assert clubs["missing_associations"] == ["NORTHERN IRELAND"]


def test_professional_2023_preserves_published_vs_extracted_total_discrepancy() -> None:
    report = build_report()

    assert report["published_global_totals"] == {
        "professional_players": 128_694,
        "professional_clubs": 3_986,
    }
    assert report["extracted_national_sums"] == {
        "professional_players": 129_388,
        "professional_clubs": 3_997,
    }
    assert report["published_global_totals"] != report["extracted_national_sums"]
