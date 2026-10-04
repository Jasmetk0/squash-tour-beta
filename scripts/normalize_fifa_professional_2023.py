"""Normalize FIFA Professional Football Report 2023 national-page extracts.

The checked-in source-specific JSON is preserved as input. This script emits exact
published non-null men's professional-player and professional-club observations;
it does not reconcile association identities to Earth geography, repair the known
Kuwait/Kyrgyzstan page anomaly, or force national sums to match FIFA's global headline.
"""
from __future__ import annotations

import argparse
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

SOURCE_ID = "fifa-professional-2023"
DEFAULT_SOURCE = Path(
    "config/earth_research/observations/fifa_professional_2023.json"
)
DEFAULT_OUTPUT_DIR = Path("config/earth_research/observations/normalized")

FIELD_SPECS: dict[str, dict[str, Any]] = {
    "professional_players": {
        "dataset_id": "fifa-professional-2023-players-v2",
        "filename": "fifa_professional_2023_players_v2.json",
        "measurement_type": "professional_male_players_reported",
        "sex_scope": "male",
        "age_scope": "all_professional_ages_or_unspecified",
        "unit": "players",
        "comparability_group": "fifa-professional-2023:professional-male-players",
        "notes": (
            "Published national-page count of men's professional football players "
            "from FIFA Professional Football Report 2023."
        ),
    },
    "professional_clubs": {
        "dataset_id": "fifa-professional-2023-clubs-v2",
        "filename": "fifa_professional_2023_clubs_v2.json",
        "measurement_type": "professional_clubs_reported",
        "sex_scope": "not_applicable",
        "age_scope": None,
        "unit": "clubs",
        "comparability_group": "fifa-professional-2023:professional-clubs",
        "notes": (
            "Published national-page count of professional football clubs from "
            "FIFA Professional Football Report 2023."
        ),
    },
}

BASE_FLAGS = [
    "national_sum_differs_from_published_global_total",
]


def _slug(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if not text:
        raise ValueError(f"cannot create stable observation slug from {value!r}")
    return text


def _input_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_source(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != "earth_source_observations.v1":
        raise ValueError("unsupported FIFA Professional Report extract schema")
    if raw.get("source_id") != SOURCE_ID:
        raise ValueError("FIFA Professional Report extract has unexpected source_id")
    observations = raw.get("observations")
    if not isinstance(observations, list) or len(observations) != 211:
        raise ValueError("expected exactly 211 FIFA association page observations")
    return raw


def build_datasets(*, source: Path = DEFAULT_SOURCE) -> dict[str, EarthObservationDataset]:
    raw = _load_source(source)
    input_sha256 = _input_sha256(source)
    source_document_sha256 = raw["source_sha256"]
    source_url = raw["source_url"]

    observations_by_dataset: dict[str, list[EarthObservation]] = {
        spec["dataset_id"]: [] for spec in FIELD_SPECS.values()
    }
    seen_ids: set[str] = set()

    for row in raw["observations"]:
        association = str(row["association"]).strip()
        page = int(row["pdf_page"])
        identity_note = row.get("identity_note")
        local_id = f"{_slug(association)}-p{page}"

        for source_field, spec in FIELD_SPECS.items():
            value = row.get(source_field)
            if value is None:
                # Source null is missing/unknown, not zero.
                continue
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(
                    f"{association} page {page}: invalid {source_field} value {value!r}"
                )

            dataset_id = spec["dataset_id"]
            observation_id = f"{dataset_id}#{local_id}"
            if observation_id in seen_ids:
                raise ValueError(f"duplicate normalized observation ID {observation_id!r}")
            seen_ids.add(observation_id)

            flags = list(BASE_FLAGS)
            notes = spec["notes"]
            if identity_note:
                flags.extend(["source_identity_anomaly", "do_not_auto_map_to_earth"])
                notes += f" Source identity warning: {identity_note}"

            observations_by_dataset[dataset_id].append(
                EarthObservation(
                    observation_id=observation_id,
                    source_id=SOURCE_ID,
                    source_entity=association,
                    earth_country_code=None,
                    historical_entity=association,
                    observation_year=2023,
                    measurement_type=spec["measurement_type"],
                    sex_scope=spec["sex_scope"],
                    age_scope=spec["age_scope"],
                    competition_scope="mens_professional_football",
                    numeric_value=value,
                    unit=spec["unit"],
                    collection_method="published_table",
                    coverage_scope="association",
                    comparability_group=spec["comparability_group"],
                    cross_country_comparable=True,
                    is_direct_observation=True,
                    is_statistically_modelled=False,
                    source_page=page,
                    source_locator=(
                        "FIFA Professional Football Report 2023; "
                        f"page={page};association={association};field={source_field}"
                    ),
                    definition_notes=notes,
                    quality_flags=flags,
                )
            )

    datasets: dict[str, EarthObservationDataset] = {}
    for source_field, spec in FIELD_SPECS.items():
        dataset_id = spec["dataset_id"]
        datasets[dataset_id] = EarthObservationDataset(
            dataset_id=dataset_id,
            source_id=SOURCE_ID,
            source_url=source_url,
            source_document_sha256=source_document_sha256,
            input_artifact_sha256=input_sha256,
            generated_by="scripts/normalize_fifa_professional_2023.py",
            scope=(
                f"Normalized {source_field!r} national-page observations from "
                "FIFA Professional Football Report 2023."
            ),
            limitations=(
                "Missing national-page values remain absent rather than zero. "
                "Extracted national sums differ from FIFA's published global headline "
                "and both are preserved. One source page is labelled KUWAIT while "
                "showing Kyrgyzstan visual identity; that observation is preserved "
                "with an explicit identity-anomaly flag and is not automatically "
                "reassigned. Association-to-Earth identity mapping is separate."
            ),
            observations=observations_by_dataset[dataset_id],
        )

    player_sum = sum(
        int(observation.numeric_value)
        for observation in datasets[
            "fifa-professional-2023-players-v2"
        ].observations
    )
    club_sum = sum(
        int(observation.numeric_value)
        for observation in datasets[
            "fifa-professional-2023-clubs-v2"
        ].observations
    )
    if player_sum != raw["extracted_national_sums"]["professional_players"]:
        raise ValueError("normalized professional-player sum differs from source extract")
    if club_sum != raw["extracted_national_sums"]["professional_clubs"]:
        raise ValueError("normalized professional-club sum differs from source extract")

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
        "dataset_count": len(datasets),
        "record_count": sum(len(dataset.observations) for dataset in datasets.values()),
        "input_artifact_sha256": next(iter(datasets.values())).input_artifact_sha256,
        "source_document_sha256": next(iter(datasets.values())).source_document_sha256,
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
