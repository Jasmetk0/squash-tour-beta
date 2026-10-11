"""Reconcile FIFA Professional Football Report 2023 pages to Earth entities.

The report is association-level and contains one known page-identity conflict.
Resolution is page-aware so duplicate labels cannot silently overwrite one
another. Missing professional counts remain null, including aggregate cases.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path("config/earth_research/observations/fifa_professional_2023.json")
DEFAULT_EARTH_ROOT = Path("config/world_packages/real_world/countries")
DEFAULT_OVERRIDES = Path(
    "config/earth_research/mappings/fifa_professional_2023_identity_overrides.json"
)
NUMERIC_FIELDS = ("professional_players", "professional_clubs")


def normalize_label(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def load_earth_catalog(root: Path) -> tuple[set[str], dict[str, list[str]]]:
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    codes = index.get("country_codes")
    if not isinstance(codes, list) or not codes:
        raise ValueError("Earth index must contain country_codes")

    names: dict[str, list[str]] = {}
    for code in codes:
        payload = json.loads((root / code / "country.json").read_text(encoding="utf-8"))
        name = str(payload.get("name") or "").strip()
        if not name:
            raise ValueError(f"{code}: Earth country name is missing")
        names.setdefault(normalize_label(name), []).append(code)
    return set(codes), names


def load_source(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("source_id") != "fifa-professional-2023":
        raise ValueError("unexpected professional-football source id")
    observations = raw.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("professional-football observations are required")
    return raw


def load_overrides(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "earth_source_identity_overrides.v1":
        raise ValueError("unsupported identity override schema")
    if raw.get("source_id") != "fifa-professional-2023":
        raise ValueError("identity overrides target the wrong source")
    return raw


def _validate_numeric(value: Any, *, page: int, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"page {page}: invalid {field}")
    return value


def reconcile(
    *,
    source: dict[str, Any],
    earth_codes: set[str],
    earth_names: dict[str, list[str]],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    direct: dict[str, str] = dict(overrides.get("direct") or {})
    groups: dict[str, Any] = dict(overrides.get("aggregate_groups") or {})
    manual_pages: dict[str, Any] = dict(overrides.get("manual_review_pages") or {})

    observations = source["observations"]
    pages = [int(item["pdf_page"]) for item in observations]
    if len(set(pages)) != len(pages):
        raise ValueError("professional report contains duplicate PDF page identifiers")

    labels = [str(item["association"]) for item in observations]
    known_labels = set(labels)

    for label, code in direct.items():
        if label not in known_labels:
            raise ValueError(f"configured source label not found: {label}")
        if code not in earth_codes:
            raise ValueError(f"direct mapping {label!r} targets missing Earth code {code}")

    member_to_target: dict[str, str] = {}
    for target, group in groups.items():
        if target not in earth_codes:
            raise ValueError(f"aggregate group targets missing Earth code {target}")
        members = group.get("source_associations")
        if not isinstance(members, list) or not members:
            raise ValueError(f"{target}: aggregate source_associations are required")
        for member in members:
            if member not in known_labels:
                raise ValueError(f"{target}: aggregate member not found: {member}")
            if member in member_to_target:
                raise ValueError(f"{member}: appears in multiple aggregate groups")
            member_to_target[member] = target

    observations_by_page = {str(item["pdf_page"]): item for item in observations}
    for page, rule in manual_pages.items():
        item = observations_by_page.get(str(page))
        if item is None:
            raise ValueError(f"manual-review page not found: {page}")
        expected = rule.get("expected_association")
        if expected and item["association"] != expected:
            raise ValueError(
                f"page {page}: expected {expected!r}, got {item['association']!r}"
            )
        candidate = rule.get("candidate_earth_code")
        if candidate is not None and candidate not in earth_codes:
            raise ValueError(f"page {page}: candidate Earth code does not exist: {candidate}")

    mappings: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    safe_target_usage: dict[str, list[dict[str, Any]]] = {}
    aggregate_inputs: dict[str, list[dict[str, Any]]] = {target: [] for target in groups}

    for item in observations:
        page = int(item["pdf_page"])
        page_key = str(page)
        label = str(item["association"])

        for field in NUMERIC_FIELDS:
            _validate_numeric(item.get(field), page=page, field=field)

        if page_key in manual_pages:
            rule = manual_pages[page_key]
            mappings.append(
                {
                    "association": label,
                    "pdf_page": page,
                    "status": "manual_review",
                    "earth_code": None,
                    "candidate_earth_code": rule.get("candidate_earth_code"),
                    "reason": rule["reason"],
                    "identity_note": item.get("identity_note"),
                }
            )
            continue

        if label in member_to_target:
            target = member_to_target[label]
            aggregate_inputs[target].append(item)
            mappings.append(
                {
                    "association": label,
                    "pdf_page": page,
                    "status": "aggregate_member",
                    "earth_code": target,
                    "reason": groups[target]["reason"],
                }
            )
            continue

        if label in direct:
            target = direct[label]
            status = "explicit_map"
        else:
            candidates = earth_names.get(normalize_label(label), [])
            if len(candidates) == 1:
                target = candidates[0]
                status = "exact_normalized_name"
            else:
                unresolved_item = {
                    "association": label,
                    "pdf_page": page,
                    "candidate_codes": candidates,
                }
                unresolved.append(unresolved_item)
                mappings.append(
                    {
                        **unresolved_item,
                        "status": "unresolved",
                        "earth_code": None,
                    }
                )
                continue

        mapping = {
            "association": label,
            "pdf_page": page,
            "status": status,
            "earth_code": target,
        }
        mappings.append(mapping)
        safe_target_usage.setdefault(target, []).append(mapping)

    duplicate_targets = {
        code: items
        for code, items in safe_target_usage.items()
        if len(items) > 1
    }

    aggregates: dict[str, Any] = {}
    for target, group in groups.items():
        inputs = aggregate_inputs[target]
        expected_members = list(group["source_associations"])
        actual_members = [item["association"] for item in inputs]
        if len(actual_members) != len(set(actual_members)):
            raise ValueError(f"{target}: duplicate aggregate member observations: {actual_members}")
        if set(actual_members) != set(expected_members):
            raise ValueError(
                f"{target}: aggregate member content mismatch: {actual_members}"
            )
        by_member = {item["association"]: item for item in inputs}
        inputs = [by_member[member] for member in expected_members]

        field_results: dict[str, Any] = {}
        for field in NUMERIC_FIELDS:
            missing = [
                item["association"]
                for item in inputs
                if item.get(field) is None
            ]
            known_values = [
                int(item[field])
                for item in inputs
                if item.get(field) is not None
            ]
            field_results[field] = {
                "value": None if missing else sum(known_values),
                "known_partial_sum": sum(known_values),
                "missing_associations": missing,
            }

        aggregates[target] = {
            "source_associations": expected_members,
            "numeric_policy": group["numeric_policy"],
            "fields": field_results,
        }

    safe_entity_count = len(safe_target_usage) + len(aggregates)
    return {
        "schema_version": "earth_source_identity_report.v1",
        "source_id": "fifa-professional-2023",
        "row_count": len(observations),
        "unique_association_label_count": len(set(labels)),
        "mapped_count": sum(
            item["status"] in {"explicit_map", "exact_normalized_name"}
            for item in mappings
        ),
        "aggregate_member_count": sum(
            item["status"] == "aggregate_member" for item in mappings
        ),
        "manual_review_count": sum(
            item["status"] == "manual_review" for item in mappings
        ),
        "safe_earth_entity_count": safe_entity_count,
        "unresolved_count": len(unresolved),
        "unresolved": unresolved,
        "duplicate_direct_targets": duplicate_targets,
        "mappings": mappings,
        "aggregates": aggregates,
        "published_global_totals": source.get("published_global_totals"),
        "extracted_national_sums": source.get("extracted_national_sums"),
        "source_review_status": source.get("review_status"),
        "source_limitations": source.get("limitations"),
    }


def build_report(
    source_path: Path = DEFAULT_SOURCE,
    earth_root: Path = DEFAULT_EARTH_ROOT,
    overrides_path: Path = DEFAULT_OVERRIDES,
) -> dict[str, Any]:
    source = load_source(source_path)
    earth_codes, earth_names = load_earth_catalog(earth_root)
    return reconcile(
        source=source,
        earth_codes=earth_codes,
        earth_names=earth_names,
        overrides=load_overrides(overrides_path),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--earth-root", type=Path, default=DEFAULT_EARTH_ROOT)
    parser.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    report = build_report(args.source, args.earth_root, args.overrides)
    summary = {
        key: report[key]
        for key in (
            "row_count",
            "unique_association_label_count",
            "mapped_count",
            "aggregate_member_count",
            "manual_review_count",
            "safe_earth_entity_count",
            "unresolved_count",
            "duplicate_direct_targets",
        )
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    if args.strict and (report["unresolved_count"] or report["duplicate_direct_targets"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
