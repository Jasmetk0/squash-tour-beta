"""Normalize the checked-in FIFA Big Count 2006 extract into Earth observations v2.

This converts only facts present in the source-specific CSV. It does not invent a
male-only split, recover lost row-level FIFA statistical flags, map association
identities onto modern Earth countries, or author country ratings.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from beta_engine.application.earth_research_observations import (
    EarthObservation,
    EarthObservationDataset,
    EarthObservationDatasetManifest,
    observation_dataset_sha256,
)
from scripts.reconcile_fifa_big_count_identities import DEFAULT_SOURCE

SOURCE_ID = "fifa-big-count-2006"
SOURCE_URL = (
    "https://web.archive.org/web/20160304131953/"
    "http://www.fifa.com/worldfootball/bigcount/allplayers.html"
)
DEFAULT_OUTPUT_DIR = Path("config/earth_research/observations/normalized")

FIELD_SPECS: dict[str, dict[str, Any]] = {
    "All Players": {
        "dataset_id": "fifa-big-count-2006-all-players-v2",
        "filename": "fifa_big_count_2006_all_players_v2.json",
        "measurement_type": "players_all_registered_and_unregistered",
        "sex_scope": "mixed",
        "age_scope": "all_or_unspecified",
        "competition_scope": "all_football_participation",
        "unit": "players",
        "comparability_group": "fifa-big-count-2006:all-players",
        "notes": (
            "All-player total in the checked-in FIFA Big Count table. It includes "
            "registered and unregistered participation and is not a men's-only count."
        ),
        "flags": ["mixed_sex", "includes_unregistered_and_casual_participation"],
    },
    "Registered players": {
        "dataset_id": "fifa-big-count-2006-registered-v2",
        "filename": "fifa_big_count_2006_registered_v2.json",
        "measurement_type": "players_registered_or_association_reported",
        "sex_scope": "mixed",
        "age_scope": "all_or_unspecified",
        "competition_scope": "registered_football",
        "unit": "players",
        "comparability_group": "fifa-big-count-2006:registered-reported",
        "notes": (
            "Association-reported registered-player field from the checked-in Big "
            "Count extract. Federation membership/registration definitions can vary "
            "between associations and must not be assumed globally identical."
        ),
        "flags": ["mixed_sex", "registration_definition_varies_by_association"],
    },
    "Unregistered Players": {
        "dataset_id": "fifa-big-count-2006-unregistered-v2",
        "filename": "fifa_big_count_2006_unregistered_v2.json",
        "measurement_type": "players_unregistered_reported_or_estimated",
        "sex_scope": "mixed",
        "age_scope": "all_or_unspecified",
        "competition_scope": "unregistered_and_occasional_football",
        "unit": "players",
        "comparability_group": "fifa-big-count-2006:unregistered-reported-or-estimated",
        "notes": (
            "Unregistered-player field from the checked-in Big Count extract. FIFA's "
            "published methodology includes occasional-player estimates in this "
            "population, so it is not an administrative registry count."
        ),
        "flags": ["mixed_sex", "includes_casual_estimate_component"],
    },
    "Clubs": {
        "dataset_id": "fifa-big-count-2006-clubs-v2",
        "filename": "fifa_big_count_2006_clubs_v2.json",
        "measurement_type": "clubs_reported",
        "sex_scope": "not_applicable",
        "age_scope": None,
        "competition_scope": "association_football_structure",
        "unit": "clubs",
        "comparability_group": "fifa-big-count-2006:clubs-reported",
        "notes": (
            "Reported club count in the checked-in Big Count table. Club definitions "
            "vary materially by association, so the field is primarily suitable for "
            "within-country context rather than mechanical cross-country access scoring."
        ),
        "flags": ["club_definition_varies_by_association"],
    },
    "Officials": {
        "dataset_id": "fifa-big-count-2006-officials-v2",
        "filename": "fifa_big_count_2006_officials_v2.json",
        "measurement_type": "officials_and_staff_reported",
        "sex_scope": "not_applicable",
        "age_scope": None,
        "competition_scope": "association_football_structure",
        "unit": "people",
        "comparability_group": "fifa-big-count-2006:officials-reported",
        "notes": (
            "Officials/staff field from the checked-in Big Count table. The extract "
            "does not preserve a finer category split, so this must not be treated as "
            "a direct count of licensed coaches or referees."
        ),
        "flags": ["official_category_not_disaggregated"],
    },
}

BASE_FLAGS = [
    "row_level_directness_unknown_in_checked_in_extract",
    "fifa_questionnaire_plus_supplementary_sources",
    "cross_country_definition_variation",
]


def _slug(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if not text:
        raise ValueError(f"cannot create stable observation slug from {value!r}")
    return text


def _number(value: str | None) -> int | float | None:
    if value is None or not str(value).strip():
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def _input_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_datasets(*, source: Path = DEFAULT_SOURCE) -> dict[str, EarthObservationDataset]:
    with source.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    input_sha256 = _input_sha256(source)
    observations_by_dataset: dict[str, list[EarthObservation]] = {
        spec["dataset_id"]: [] for spec in FIELD_SPECS.values()
    }
    seen_ids: set[str] = set()

    for row in rows:
        association = row["Association"]
        association_slug = _slug(association)

        for source_field, spec in FIELD_SPECS.items():
            value = _number(row.get(source_field))
            if value is None:
                # Missing source cells are omitted, never converted to zero.
                continue

            dataset_id = spec["dataset_id"]
            observation_id = f"{dataset_id}#{association_slug}"
            if observation_id in seen_ids:
                raise ValueError(f"duplicate normalized observation ID {observation_id!r}")
            seen_ids.add(observation_id)

            observations_by_dataset[dataset_id].append(
                EarthObservation(
                    observation_id=observation_id,
                    source_id=SOURCE_ID,
                    source_entity=association,
                    earth_country_code=None,
                    historical_entity=association,
                    observation_year=2006,
                    measurement_type=spec["measurement_type"],
                    sex_scope=spec["sex_scope"],
                    age_scope=spec["age_scope"],
                    competition_scope=spec["competition_scope"],
                    numeric_value=value,
                    unit=spec["unit"],
                    collection_method="mixed",
                    coverage_scope="association",
                    comparability_group=spec["comparability_group"],
                    cross_country_comparable=False,
                    is_direct_observation=None,
                    is_statistically_modelled=None,
                    source_locator=(
                        "Big Count All Players table; "
                        f"association={association};column={source_field}"
                    ),
                    definition_notes=(
                        spec["notes"]
                        + " The checked-in legacy extract does not retain the source's "
                        "per-cell direct/statistically-processed marker, so that "
                        "provenance is explicitly unknown here."
                    ),
                    quality_flags=list(dict.fromkeys(BASE_FLAGS + spec["flags"])),
                )
            )

    datasets: dict[str, EarthObservationDataset] = {}
    for source_field, spec in FIELD_SPECS.items():
        dataset_id = spec["dataset_id"]
        datasets[dataset_id] = EarthObservationDataset(
            dataset_id=dataset_id,
            source_id=SOURCE_ID,
            source_url=SOURCE_URL,
            source_document_sha256=None,
            input_artifact_sha256=input_sha256,
            generated_by="scripts/normalize_fifa_big_count_2006.py",
            scope=(
                f"Normalized FIFA Big Count 2006 {source_field!r} observations from "
                "the checked-in 208-row All Players extract."
            ),
            limitations=(
                "The checked-in extract cannot recover country-level male/female "
                "splits or per-cell FIFA statistical-processing flags. FIFA's "
                "methodology supplemented missing association responses with prior "
                "surveys and internal analysis. Cross-country field definitions are "
                "not assumed identical. Earth/geopolitical identity mapping is a "
                "separate reviewed transformation and is not embedded in source facts."
            ),
            observations=observations_by_dataset[dataset_id],
        )
    return datasets


def build_manifests(
    datasets: dict[str, EarthObservationDataset],
    *,
    output_dir: Path,
) -> dict[str, EarthObservationDatasetManifest]:
    manifests: dict[str, EarthObservationDatasetManifest] = {}
    for spec in FIELD_SPECS.values():
        dataset = datasets[spec["dataset_id"]]
        output_path = output_dir / spec["filename"]
        relative_path = output_path.relative_to(Path("config/earth_research"))
        manifests[dataset.dataset_id] = EarthObservationDatasetManifest(
            dataset_id=dataset.dataset_id,
            source_id=dataset.source_id,
            relative_path=relative_path.as_posix(),
            sha256=observation_dataset_sha256(dataset),
            record_count=len(dataset.observations),
            source_document_sha256=dataset.source_document_sha256,
            input_artifact_sha256=dataset.input_artifact_sha256,
            generated_by=dataset.generated_by,
        )
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-output", type=Path)
    args = parser.parse_args()

    datasets = build_datasets(source=args.source)
    manifests = build_manifests(datasets, output_dir=args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    spec_by_id = {spec["dataset_id"]: spec for spec in FIELD_SPECS.values()}
    for dataset_id, dataset in datasets.items():
        output = args.output_dir / spec_by_id[dataset_id]["filename"]
        output.write_text(
            json.dumps(dataset.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

    summary = {
        "source_row_count": 208,
        "dataset_count": len(datasets),
        "record_count": sum(len(dataset.observations) for dataset in datasets.values()),
        "input_artifact_sha256": next(iter(datasets.values())).input_artifact_sha256,
        "datasets": {
            dataset_id: {
                "record_count": manifest.record_count,
                "sha256": manifest.sha256,
                "relative_path": manifest.relative_path,
            }
            for dataset_id, manifest in manifests.items()
        },
    }
    print(json.dumps(summary, indent=2))

    if args.manifest_output:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_text(
            json.dumps(
                {
                    dataset_id: manifest.model_dump(mode="json")
                    for dataset_id, manifest in manifests.items()
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
