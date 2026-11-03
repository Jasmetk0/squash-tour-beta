"""Independent, read-only evidence coverage diagnostics for the ATP reference sources."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.audit_atp_reference_provenance import (
    audit,
    evidence_kind,
    licence_evidence_urls,
)

pytestmark = pytest.mark.pr_critical

SOURCE = (Path(__file__).resolve().parents[2] / "config" / "reference_packages"
          / "atp_tour_1990_2026")


def _inputs() -> tuple[dict, dict, dict]:
    return tuple(json.loads((SOURCE / name).read_text(encoding="utf-8"))
                 for name in ("category.json", "series.json", "seasons_1990_2026.json"))


def test_source_provenance_audit_full_37_year_inventory_is_reproducible() -> None:
    category, series, seasons = _inputs()
    before = copy.deepcopy((category, series, seasons))
    report = audit(category, series, seasons)
    assert report == audit(category, series, seasons)
    assert (category, series, seasons) == before
    assert report["schema_version"] == "tennis.atp_source_provenance_audit.v1"
    counts = report["counts"]
    assert counts["category_identities"] == 11
    assert counts["series_identities"] == 166
    assert counts["historical_season_rows"] == 37
    assert counts["source_interval_records"] == 1983
    assert counts["year_effective_series_memberships"] == 2431
    assert counts["explicit_historical_host_year_records"] == 1448
    assert counts["memberships_without_explicit_host_year_record"] == 983
    assert len(report["series_evidence"]) == 166
    assert [y["year"] for y in report["yearly_coverage"]] == list(range(1990, 2027))
    assert sum(y["source_membership_count"] for y in report["yearly_coverage"]) == 2431
    assert sum(y["without_explicit_host_year_evidence"]
               for y in report["yearly_coverage"]) == 983
    assert counts["source_period_evidence_kinds"]["atp_year_results_index"] >= 1700


def test_provenance_audit_does_not_mislabel_generic_atp_archive_as_licence_proof() -> None:
    url = "https://www.atptour.com/en/scores/results-archive?year=1990"
    assert evidence_kind(url) == "atp_year_results_index"
    assert evidence_kind("https://www.atptour.com/en/news/belgrade-athens-announcement-august-2025") == "atp_other"
    assert evidence_kind("https://www.nextgenatpfinals.com/en/news/host") == "atp_event_site"
    assert evidence_kind("https://www.tennis.com/news/relocation") == "external"
    assert evidence_kind("http://www.atptour.com/en/scores/results-archive") == "invalid"
    assert licence_evidence_urls({
        "historical_licence_source_url": "https://example.org/a",
        "historical_licence_source_urls": [
            "https://example.org/b", "https://example.org/a"],
    }) == ["https://example.org/a", "https://example.org/b"]
    category, series, seasons = _inputs()
    report = audit(category, series, seasons)
    by_id = {e["source_entity_id"]: e for e in report["series_evidence"]}
    assert by_id["belgrade"]["explicit_licence_evidence_urls"]
    assert by_id["los_cabos"]["explicit_licence_evidence_urls"]
    assert "atp_year_results_index" in report["counts"]["source_period_evidence_kinds"]
    assert report["counts"]["multi_host_series_without_explicit_licence_source"] >= 10


def test_2026_tbd_is_a_risk_note_not_fabricated_series_or_played_edition() -> None:
    category, series, seasons = _inputs()
    result = audit(category, series, seasons)
    data = result["provisional_2026"]
    assert data["source_status"] == "provisional_calendar_not_final_results"
    assert data["known_named_atp_250_series"] == 29
    assert data["published_2025_11_27_calendar_summary_atp_250"] == 29
    assert data["published_2025_11_27_calendar_has_separate_TBD_250_row"] is True
    assert data["tbd_is_not_approved_source_series"] is True
    assert not {"tbd", "to_be_decided", "unknown_250"} & {
        e["source_entity_id"] for e in series["entities"]
    }


def test_provenance_audit_rejects_stale_annual_snapshot_not_count_only() -> None:
    category, series, seasons = _inputs()
    altered = copy.deepcopy(seasons)
    # Two genuine 2025 Series retain the same tier; counts alone would pass.
    row = next(x for x in altered["seasons"] if x["year"] == 2025)
    row["series_category_ids"]["belgrade"] = "atp_500"
    with pytest.raises(ValueError, match="Stored seasons differ"):
        audit(category, series, altered)
