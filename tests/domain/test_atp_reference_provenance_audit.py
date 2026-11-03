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
    assert counts["series_identities"] == 164
    assert counts["historical_season_rows"] == 37
    assert counts["source_interval_records"] == 1983
    assert counts["year_effective_series_memberships"] == 2431
    assert counts["explicit_historical_host_year_records"] == 1455
    assert counts["memberships_without_explicit_host_year_record"] == 976
    assert len(report["series_evidence"]) == 164
    assert [y["year"] for y in report["yearly_coverage"]] == list(range(1990, 2027))
    assert sum(y["source_membership_count"] for y in report["yearly_coverage"]) == 2431
    assert sum(y["without_explicit_host_year_evidence"]
               for y in report["yearly_coverage"]) == 976
    assert counts["source_period_evidence_kinds"]["atp_year_results_index"] >= 1700
    assert counts["series_with_nonlicence_host_context"] == 19
    assert counts["multi_host_series_without_any_specific_context"] == 12
    assert counts["multi_host_series_without_explicit_licence_source"] == 31
    assert sum(counts["historical_host_context_kinds"].values()) == 19


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


def test_memphis_500_and_san_jose_250_licences_do_not_merge_at_2014_boundary() -> None:
    """A venue can retain its name while the underlying ATP sanction changes."""
    categories, series, seasons = _inputs()
    by_id = {e["source_entity_id"]: e for e in series["entities"]}
    assert "san_jose_2013" not in by_id
    memphis_to_rio = by_id["rio"]["payload"]
    san_jose_to_dallas = by_id["dallas"]["payload"]
    mhosts = {h["year"]: h["city"]
              for h in memphis_to_rio["historical_host_change"]}
    shosts = {h["year"]: h["city"]
              for h in san_jose_to_dallas["historical_host_change"]}
    assert mhosts[2013] == "Memphis" and mhosts[2014] == "Rio de Janeiro"
    assert shosts[2013] == "San Jose" and shosts[2014] == "Memphis"
    assert mhosts[1990] == "Memphis" and shosts[1990] == "San Francisco"

    annual = {row["year"]: row for row in seasons["seasons"]}
    for year in (2012, 2013):
        assert annual[year]["series_category_ids"]["rio"] == "atp_500"
        assert annual[year]["series_category_ids"]["dallas"] == "atp_250"
    for year in (2014, 2015):
        assert annual[year]["series_category_ids"]["rio"] == "atp_500"
        assert annual[year]["series_category_ids"]["dallas"] == "atp_250"
    assert annual[2008]["series_category_ids"]["rio"] == "atp_international_series_gold"
    assert annual[2008]["series_category_ids"]["dallas"] == "atp_international_series"
    assert annual[2025]["series_category_ids"]["dallas"] == "atp_500"
    assert by_id["rio"]["payload"]["historical_licence_source_urls"]
    assert by_id["dallas"]["payload"]["historical_licence_source_urls"]
    assert audit(categories, series, seasons)["counts"]["year_effective_series_memberships"] == 2431


def test_duesseldorf_to_geneva_audited_licence_is_one_source_identity() -> None:
    categories, series, seasons = _inputs()
    by_id = {e["source_entity_id"]: e["payload"] for e in series["entities"]}
    assert "duesseldorf_2014" not in by_id
    hosts = {host["year"]: host["city"]
             for host in by_id["geneva"]["historical_host_change"]}
    assert hosts[2013] == hosts[2014] == "Düsseldorf"
    assert hosts[2015] == hosts[2026] == "Geneva"
    for year in (2013, 2014, 2015, 2026):
        annual = next(row for row in seasons["seasons"] if row["year"] == year)
        assert annual["series_category_ids"]["geneva"] == "atp_250"
    assert by_id["geneva"]["historical_licence_source_urls"]
    assert by_id["cologne_1992_clay"]["historical_host_change"][0]["city"] == "Geneva"
    assert audit(categories, series, seasons)["counts"]["series_identities"] == 164


def test_six_verified_venue_transfers_retain_original_licence_identity() -> None:
    """Documented relocation may change the city, not the stable Series ID.

    These dated references prove specific host transfers, not all the
    historical movements of long-lived Series.
    """
    _, series, seasons = _inputs()
    by_id = {entity["source_entity_id"]: entity["payload"]
             for entity in series["entities"]}
    examples = {
        "hangzhou": (2023, "Zhuhai", 2024, "Hangzhou",
                     "https://www.atptour.com/en/news/hangzhou-press-conference-2024-june"),
        "almaty": (2023, "Astana", 2024, "Almaty",
                   "https://www.atptour.com/en/news/2024-atp-calendar-update-gijon-almaty"),
        "brussels": (2024, "Antwerp", 2025, "Brussels",
                     "https://www.atptour.com/en/news/antwerp-brussels-relocation-2025"),
        "lyon": (2025, "Marseille", 2026, "Lyon",
                 "https://www.atptour.com/en/news/marseille-lyon-relocation"),
        "sofia": (2015, "Zagreb", 2016, "Sofia",
                  "https://www.atptour.com/en/news/atp-announces-2017-2018-calendars"),
        "chengdu": (2015, "Kuala Lumpur", 2016, "Chengdu",
                    "https://www.denik.cz/tenis/teniste-uz-nebudou-hrat-v-kualu-lumpur-turnaj-se-stehuje-do-ccheng-tu-20160629.html"),
    }
    snapshot = {x["year"]: x["series_category_ids"] for x in seasons["seasons"]}
    for series_id, (old_year, old_city, new_year, new_city, url) in examples.items():
        payload = by_id[series_id]
        hosts = {row["year"]: row["city"] for row in payload["historical_host_change"]}
        assert hosts[old_year] == old_city
        assert hosts[new_year] == new_city
        assert url in licence_evidence_urls(payload)
        assert series_id in snapshot[old_year]
        assert series_id in snapshot[new_year]
        assert snapshot[old_year][series_id] == snapshot[new_year][series_id]
    # These six narrow transfers do not purport to certify every older city
    # or a legal chain in the many other historical source Series.
    report = audit(*_inputs())
    assert report["counts"]["multi_host_series_without_explicit_licence_source"] >= 10


def test_provenance_metadata_fail_closed_and_no_truncated_official_news_links() -> None:
    from scripts.build_atp_tour_historical_seasons import build

    categories, series, _ = _inputs()
    raw = json.dumps(series, ensure_ascii=False)
    assert '"https://www.atptour.com/en/news/to"' not in raw

    bad = copy.deepcopy(series)
    hangzhou = next(x for x in bad["entities"] if x["source_entity_id"] == "hangzhou")
    hangzhou["payload"]["historical_licence_source_urls"] = ["http://example.com"]
    with pytest.raises(ValueError, match="Invalid historical licence evidence"):
        build(categories, bad)

    bad = copy.deepcopy(series)
    hangzhou = next(x for x in bad["entities"] if x["source_entity_id"] == "hangzhou")
    url = hangzhou["payload"]["historical_licence_source_urls"][0]
    hangzhou["payload"]["historical_licence_source_urls"] = [url, url]
    with pytest.raises(ValueError, match="Invalid historical licence evidence"):
        build(categories, bad)


def test_venue_context_must_not_be_misrepresented_as_licence_ownership() -> None:
    categories, series, seasons = _inputs()
    report = audit(categories, series, seasons)
    by_id = {row["source_entity_id"]: row for row in report["series_evidence"]}
    expected = {
        "miami": "site_change",
        "canadian_open": "alternating_hosts",
        "cincinnati": "temporary_site",
        "acapulco": "site_change",
        "brisbane": "site_change",
        "delray_beach": "site_change",
        "houston": "site_change",
        "marrakech": "site_change",
        "stuttgart": "surface_not_licence",
        "s_hertogenbosch": "city_alias",
        "eastbourne": "site_change",
        "estoril": "historical_context_only",
        "atp_finals": "rotating_hosts",
        "belgrade_clay_2021": "site_change",
        "lyon_old": "site_change",
        "sao_paulo": "site_change",
        "st_petersburg": "city_alias",
        "warsaw_2008": "site_change",
        "bogota_colombia_2001": "city_alias",
    }
    assert {
        key: by_id[key]["historical_host_context_evidence_kinds"][0]
        for key in expected
    } == expected
    # Separate public context references must never be silently promoted
    # to legal licence proof; tracked missing-licence count remains unchanged.
    for key in ("canadian_open", "stuttgart", "s_hertogenbosch", "estoril"):
        assert by_id[key]["historical_host_context_evidence_urls"]
        assert not by_id[key]["explicit_licence_evidence_urls"]
        assert by_id[key]["multiple_host_cities_without_explicit_licence_source"]
    assert "estoril" not in report["multi_host_series_without_any_specific_context"]
    assert "miami" not in report["multi_host_series_without_any_specific_context"]


def test_invalid_venue_context_metadata_rejected_without_source_mutation() -> None:
    from scripts.build_atp_tour_historical_seasons import build

    category, series, snapshot = _inputs()
    baseline = audit(category, series, snapshot)
    assert baseline["counts"]["series_identities"] == 164
    for broken in (
        {"kind": "site_change", "url": "http://insecure.test", "note": "x"},
        {"kind": [], "url": "https://example.org/a", "note": "x"},
        {"kind": "legal_licence_certified", "url": "https://example.org/a", "note": "x"},
        {"kind": "site_change", "url": "https://example.org/a", "note": ""},
    ):
        altered = copy.deepcopy(series)
        item = next(e for e in altered["entities"] if e["source_entity_id"] == "miami")
        item["payload"]["historical_host_context_sources"] = [broken]
        with pytest.raises(ValueError, match="Invalid historical host-context evidence"):
            build(category, altered)
    assert audit(category, series, snapshot) == baseline
