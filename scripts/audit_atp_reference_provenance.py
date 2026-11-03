"""Read-only, reproducible provenance coverage audit for ATP 1990–2026 sources.

A year-indexed Results Archive link proves neither a legal licence transfer
nor every edition's venue. No HTTP requests, no automatic backfilling, and
no changes to source Packages, derived seasons or Runs.

Run:
  python scripts/audit_atp_reference_provenance.py
  python scripts/audit_atp_reference_provenance.py --output /tmp/atp_audit.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    # Support direct execution: python scripts/audit_atp_reference_provenance.py
    sys.path.insert(0, str(ROOT))
from scripts.build_atp_tour_historical_seasons import build

SOURCE = ROOT / "config" / "reference_packages" / "atp_tour_1990_2026"
GENERIC_ATP_RESULTS = "/en/scores/results-archive"
FIRST_YEAR, LAST_YEAR = 1990, 2026


def evidence_kind(url: str) -> str:
    """Source specificity, not an invented confidence or legal-proof score."""
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        return "invalid"
    host = parts.hostname.removeprefix("www.").lower()
    if host == "atptour.com" and parts.path.rstrip("/") == GENERIC_ATP_RESULTS:
        return "atp_year_results_index"
    if host == "atptour.com":
        return "atp_other"
    if host == "nittoatpfinals.com" or host == "nextgenatpfinals.com":
        return "atp_event_site"
    return "external"


def effective_years(periods: list[dict[str, Any]]) -> set[int]:
    return {year for period in periods
            for year in range(period["from"], period["to"] + 1)}


def licence_evidence_urls(payload: dict[str, Any]) -> list[str]:
    """Only explicitly marked licence evidence, never generic archive links."""
    candidates = []
    single = payload.get("historical_licence_source_url")
    if isinstance(single, str):
        candidates.append(single)
    multi = payload.get("historical_licence_source_urls", [])
    if isinstance(multi, list):
        candidates.extend(url for url in multi if isinstance(url, str))
    return sorted(set(candidates))


def audit(
    categories: dict[str, Any],
    series: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    # The source-of-truth deterministic builder also guards malformed source
    # references, category histories, historic hosts and played-tier totals.
    derived = build(categories, series)
    if snapshot != derived:
        raise ValueError("Stored seasons differ from the canonical builder output")

    entries = []
    source_kinds: Counter[str] = Counter()
    yearly_memberships: Counter[int] = Counter()
    yearly_host_evidence: Counter[int] = Counter()
    licences_missing_on_multi_host: list[str] = []
    context_missing_on_multi_host: list[str] = []
    context_kinds: Counter[str] = Counter()
    for item in sorted(series["entities"], key=lambda e: e["source_entity_id"]):
        identity = item["source_entity_id"]
        payload = item["payload"]
        periods = payload["history_periods"]
        active = effective_years(periods)
        hosts = payload.get("historical_host_change", [])
        hosted = {x["year"] for x in hosts}
        cities = sorted({x["city"] for x in hosts})
        licence_urls = licence_evidence_urls(payload)
        # A historical site reference is not legal ownership evidence.
        host_context = payload.get("historical_host_context_sources", [])
        context_urls = [row["url"] for row in host_context]
        context_kinds.update(row["kind"] for row in host_context)
        period_kinds = Counter(evidence_kind(period["source_url"])
                               for period in periods)
        source_kinds.update(period_kinds)
        for year in active:
            yearly_memberships[year] += 1
        for year in hosted:
            yearly_host_evidence[year] += 1
        if len(cities) > 1 and not licence_urls:
            licences_missing_on_multi_host.append(identity)
        if len(cities) > 1 and not licence_urls and not host_context:
            context_missing_on_multi_host.append(identity)
        entries.append({
            "source_entity_id": identity,
            "effective_from": min(active),
            "effective_to": max(active),
            "member_years": len(active),
            "historical_host_years": len(hosted),
            "missing_explicit_host_years": len(active - hosted),
            "documented_distinct_host_cities": cities,
            "source_period_evidence_kind_counts": dict(sorted(period_kinds.items())),
            "explicit_licence_evidence_urls": licence_urls,
            "historical_host_context_evidence_urls": context_urls,
            "historical_host_context_evidence_kinds":
                sorted({row["kind"] for row in host_context}),
            "multiple_host_cities_without_any_specific_context":
                len(cities) > 1 and not licence_urls and not host_context,
            "multiple_host_cities_without_explicit_licence_source":
                len(cities) > 1 and not licence_urls,
        })

    year_rows = []
    for row in snapshot["seasons"]:
        year = row["year"]
        count = len(row["series_category_ids"])
        if yearly_memberships[year] != count:
            raise ValueError(f"Year membership mismatch: {year}")
        year_rows.append({
            "year": year,
            "source_membership_count": count,
            "explicit_host_year_evidence": yearly_host_evidence[year],
            "without_explicit_host_year_evidence":
                count - yearly_host_evidence[year],
            "played_tier_count_status":
                row["played_tier_roster_validation"]["status"],
            "known_not_held_series_count":
                len(row["known_not_held_series_ids"]),
        })

    current = snapshot["seasons"][-1]
    known_named_250 = sum(c == "atp_250"
                          for c in current["series_category_ids"].values())
    total_memberships = sum(yearly_memberships.values())
    total_hosts = sum(yearly_host_evidence.values())
    return {
        "schema_version": "tennis.atp_source_provenance_audit.v1",
        "scope": "READ_ONLY_REFERENCE_AUDIT_NOT_INDEPENDENT_HISTORICAL_CERTIFICATION",
        "counts": {
            "category_identities": len(categories["entities"]),
            "series_identities": len(entries),
            "source_interval_records": sum(source_kinds.values()),
            "historical_season_rows": len(year_rows),
            "year_effective_series_memberships": total_memberships,
            "explicit_historical_host_year_records": total_hosts,
            "memberships_without_explicit_host_year_record":
                total_memberships - total_hosts,
            "source_period_evidence_kinds": dict(sorted(source_kinds.items())),
            "multi_host_series_without_explicit_licence_source":
                len(licences_missing_on_multi_host),
            "multi_host_series_without_any_specific_context":
                len(context_missing_on_multi_host),
            "series_with_nonlicence_host_context":
                sum(bool(row["historical_host_context_evidence_urls"]) for row in entries),
            "historical_host_context_kinds": dict(sorted(context_kinds.items())),
        },
        "provisional_2026": {
            "source_status": current["played_tier_roster_validation"]["status"],
            "known_named_atp_250_series": known_named_250,
            "published_2025_11_27_calendar_summary_atp_250": 29,
            "published_2025_11_27_calendar_has_separate_TBD_250_row": True,
            "tbd_is_not_approved_source_series": True,
            "source_url": "https://www.atptour.com/en/news/what-is-the-2026-atp-tour-calendar/",
            "interpretation": (
                "Published summary/table may differ; do not invent a Series for "
                "TBD, equate schedule with played results, or certify 2026 as final."
            ),
        },
        "multi_host_series_without_explicit_licence_source":
            licences_missing_on_multi_host,
        "multi_host_series_without_any_specific_context":
            context_missing_on_multi_host,
        "yearly_coverage": year_rows,
        "series_evidence": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        help="Optional JSON report path. Omitted = no writes.")
    args = parser.parse_args()
    categories = json.loads((SOURCE / "category.json").read_text(encoding="utf-8"))
    series = json.loads((SOURCE / "series.json").read_text(encoding="utf-8"))
    seasons = json.loads((SOURCE / "seasons_1990_2026.json").read_text(encoding="utf-8"))
    result = audit(categories, series, seasons)
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False,
                                          sort_keys=True, indent=2) + "\n",
                               encoding="utf-8")
        print(f"Saved read-only provenance review: {args.output}")
    else:
        print(json.dumps(result["counts"], ensure_ascii=False, sort_keys=True))
        print("2026 is provisional; source coverage is not licence verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
