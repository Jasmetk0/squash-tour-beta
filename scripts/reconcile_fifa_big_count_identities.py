"""Reconcile FIFA Big Count 2006 association labels to the Earth catalogue.

The source is association-level while the Earth package is geography-level. This
tool intentionally avoids fuzzy guessing: rows are resolved by an explicit
override, a unique normalized Earth country name, a declared aggregate group,
or an explicit manual-review block.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path("config/earth_research/observations/fifa_big_count_2006.csv")
DEFAULT_EARTH_ROOT = Path("config/world_packages/real_world/countries")
DEFAULT_OVERRIDES = Path("config/earth_research/mappings/fifa_big_count_2006_identity_overrides.json")
NUMERIC_FIELDS = ("All Players", "Registered players", "Unregistered Players", "Clubs", "Officials")


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


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_overrides(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "earth_source_identity_overrides.v1":
        raise ValueError("unsupported identity override schema")
    if raw.get("source_id") != "fifa-big-count-2006":
        raise ValueError("identity overrides target the wrong source")
    return raw


def _number(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    return float(value)


def reconcile(
    *,
    rows: list[dict[str, str]],
    earth_codes: set[str],
    earth_names: dict[str, list[str]],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    direct: dict[str, str] = dict(overrides.get("direct") or {})
    manual: dict[str, Any] = dict(overrides.get("manual_review") or {})
    groups: dict[str, Any] = dict(overrides.get("aggregate_groups") or {})

    for source_label, code in direct.items():
        if code not in earth_codes:
            raise ValueError(f"direct mapping {source_label!r} targets missing Earth code {code}")
    for code, group in groups.items():
        if code not in earth_codes:
            raise ValueError(f"aggregate group targets missing Earth code {code}")

    aggregate_member_to_target: dict[str, str] = {}
    for target, group in groups.items():
        members = group.get("source_associations")
        if not isinstance(members, list) or not members:
            raise ValueError(f"{target}: aggregate source_associations are required")
        for member in members:
            if member in aggregate_member_to_target:
                raise ValueError(f"{member}: appears in multiple aggregate groups")
            aggregate_member_to_target[member] = target

    source_labels = [row.get("Association", "") for row in rows]
    known_source_labels = set(source_labels)
    configured = set(direct) | set(manual) | set(aggregate_member_to_target)
    missing_configured = configured - known_source_labels
    if missing_configured:
        raise ValueError(f"configured source labels not found: {sorted(missing_configured)}")

    mappings: list[dict[str, Any]] = []
    unresolved: list[str] = []
    auto_target_usage: dict[str, list[str]] = {}
    aggregates: dict[str, dict[str, Any]] = {
        target: {
            "source_associations": list(group["source_associations"]),
            "numeric_policy": group["numeric_policy"],
            "values": {field: 0.0 for field in NUMERIC_FIELDS},
            "null_fields": [],
        }
        for target, group in groups.items()
    }

    for row in rows:
        label = row["Association"]
        if label in manual:
            mappings.append({
                "association": label,
                "status": "manual_review",
                "earth_code": None,
                "reason": manual[label]["reason"],
            })
            continue

        if label in aggregate_member_to_target:
            target = aggregate_member_to_target[label]
            mappings.append({
                "association": label,
                "status": "aggregate_member",
                "earth_code": target,
                "reason": groups[target]["reason"],
            })
            aggregate = aggregates[target]
            for field in NUMERIC_FIELDS:
                number = _number(row.get(field))
                if number is None:
                    aggregate["null_fields"].append({"association": label, "field": field})
                else:
                    aggregate["values"][field] += number
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
                unresolved.append(label)
                mappings.append({
                    "association": label,
                    "status": "unresolved",
                    "earth_code": None,
                    "candidate_codes": candidates,
                })
                continue

        mappings.append({
            "association": label,
            "status": status,
            "earth_code": target,
        })
        auto_target_usage.setdefault(target, []).append(label)

    duplicate_targets = {
        code: labels
        for code, labels in auto_target_usage.items()
        if len(labels) > 1
    }

    for aggregate in aggregates.values():
        aggregate["values"] = {
            key: int(value) if float(value).is_integer() else value
            for key, value in aggregate["values"].items()
        }

    return {
        "schema_version": "earth_source_identity_report.v1",
        "source_id": "fifa-big-count-2006",
        "row_count": len(rows),
        "mapped_count": sum(item["status"] in {"explicit_map", "exact_normalized_name"} for item in mappings),
        "aggregate_member_count": sum(item["status"] == "aggregate_member" for item in mappings),
        "manual_review_count": sum(item["status"] == "manual_review" for item in mappings),
        "unresolved_count": len(unresolved),
        "unresolved": unresolved,
        "duplicate_direct_targets": duplicate_targets,
        "mappings": mappings,
        "aggregates": aggregates,
    }


def build_report(
    source: Path = DEFAULT_SOURCE,
    earth_root: Path = DEFAULT_EARTH_ROOT,
    overrides_path: Path = DEFAULT_OVERRIDES,
) -> dict[str, Any]:
    earth_codes, earth_names = load_earth_catalog(earth_root)
    return reconcile(
        rows=load_rows(source),
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
            "mapped_count",
            "aggregate_member_count",
            "manual_review_count",
            "unresolved_count",
            "duplicate_direct_targets",
        )
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.strict and (report["unresolved_count"] or report["duplicate_direct_targets"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
