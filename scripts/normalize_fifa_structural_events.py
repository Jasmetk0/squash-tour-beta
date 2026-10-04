"""Normalize curated FIFA structural events into canonical observation v2 datasets.

The seed contains reviewed event facts only. This script does not convert events
into rating deltas, interpolate them, or resolve source conflicts. One normalized
dataset is emitted per original source so source provenance remains exact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from beta_engine.application.earth_research_observations import (
    EarthObservation,
    EarthObservationDataset,
    EarthObservationDatasetManifest,
    observation_dataset_sha256,
)

DEFAULT_SEED = Path(
    "config/earth_research/observations/structural/fifa_structural_events_seed_v1.json"
)
DEFAULT_RESEARCH = Path("config/earth_research/fifa_earth.json")
DEFAULT_OUTPUT_DIR = Path(
    "config/earth_research/observations/normalized/structural"
)
GENERATED_BY = "scripts/normalize_fifa_structural_events.py"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _dataset_id(source_id: str) -> str:
    return f"fifa-structural-{source_id}-v1"


def _filename(source_id: str) -> str:
    return f"{_dataset_id(source_id).replace('-', '_')}.json"


def _load_seed(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "fifa_structural_event_seed.v1":
        raise ValueError("unsupported structural-event seed schema")
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        raise ValueError("structural-event seed requires events")

    event_ids: set[str] = set()
    for event in events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("every structural event requires event_id")
        if event_id in event_ids:
            raise ValueError(f"duplicate structural event ID {event_id!r}")
        event_ids.add(event_id)

        tags = event.get("dimension_tags")
        if not isinstance(tags, list) or not tags:
            raise ValueError(f"{event_id}: dimension_tags are required")
        if len(tags) != len(set(tags)):
            raise ValueError(f"{event_id}: dimension_tags must be unique")

        conflict_group = event.get("conflict_group")
        flags = event.get("quality_flags") or []
        if conflict_group and "source_timing_conflict" not in flags:
            raise ValueError(
                f"{event_id}: conflict_group requires source_timing_conflict flag"
            )
    return payload


def build_datasets(
    *,
    seed_path: Path = DEFAULT_SEED,
    research_path: Path = DEFAULT_RESEARCH,
) -> dict[str, EarthObservationDataset]:
    seed = _load_seed(seed_path)
    research = json.loads(research_path.read_text(encoding="utf-8"))
    sources = research.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("Earth research source catalogue is missing")

    seed_sha256 = _file_sha256(seed_path)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in seed["events"]:
        source_id = str(event["source_id"])
        if source_id not in sources:
            raise ValueError(
                f"{event['event_id']}: source {source_id!r} is not in FIFA research catalogue"
            )
        grouped.setdefault(source_id, []).append(event)

    datasets: dict[str, EarthObservationDataset] = {}
    for source_id, events in sorted(grouped.items()):
        source = sources[source_id]
        dataset_id = _dataset_id(source_id)
        observations: list[EarthObservation] = []

        for event in sorted(events, key=lambda item: item["event_id"]):
            flags = list(event.get("quality_flags") or [])
            flags.extend(
                f"supports_{dimension}"
                for dimension in event["dimension_tags"]
            )
            conflict_group = event.get("conflict_group")
            if conflict_group:
                flags.append(f"conflict_group:{conflict_group}")
            flags = list(dict.fromkeys(flags))

            definition_notes = (
                "Structural football event. Dimension tags indicate plausible evidence "
                "relevance only and are not rating weights or effect sizes."
            )
            if conflict_group:
                definition_notes += (
                    f" This fact belongs to unresolved source conflict "
                    f"{conflict_group!r}; conflicting observations must remain separate."
                )

            observations.append(
                EarthObservation(
                    observation_id=f"{dataset_id}#{event['event_id']}",
                    source_id=source_id,
                    source_entity=event["source_entity"],
                    earth_country_code=event["earth_country_code"],
                    historical_entity=event.get("historical_entity"),
                    observation_year=int(event["observation_year"]),
                    measurement_type="football_structural_event",
                    sex_scope="not_applicable",
                    age_scope=None,
                    competition_scope="football_system_structure",
                    text_value=event["description"],
                    unit="event",
                    collection_method="official_narrative",
                    coverage_scope="association",
                    comparability_group=event["event_type"],
                    cross_country_comparable=False,
                    is_direct_observation=True,
                    is_statistically_modelled=False,
                    territory_mapping_method="explicit_reviewed_event_to_earth",
                    source_locator=event["source_locator"],
                    definition_notes=definition_notes,
                    quality_flags=flags,
                )
            )

        datasets[dataset_id] = EarthObservationDataset(
            dataset_id=dataset_id,
            source_id=source_id,
            source_url=source["url"],
            source_document_sha256=None,
            input_artifact_sha256=seed_sha256,
            generated_by=GENERATED_BY,
            scope=(
                f"Canonical structural football events from source {source_id!r} "
                "for the FIFA Earth review set."
            ),
            limitations=(
                source["limitations"]
                + " Structural-event relevance tags are not numeric ratings, "
                "effect sizes or proof of nationwide implementation outcomes."
            ),
            observations=observations,
        )

    return datasets


def build_manifests(
    datasets: dict[str, EarthObservationDataset],
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, EarthObservationDatasetManifest]:
    manifests: dict[str, EarthObservationDatasetManifest] = {}
    for dataset_id, dataset in sorted(datasets.items()):
        output = output_dir / _filename(dataset.source_id)
        relative = output.relative_to(Path("config/earth_research"))
        manifests[dataset_id] = EarthObservationDatasetManifest(
            dataset_id=dataset_id,
            source_id=dataset.source_id,
            relative_path=relative.as_posix(),
            sha256=observation_dataset_sha256(dataset),
            record_count=len(dataset.observations),
            source_document_sha256=dataset.source_document_sha256,
            input_artifact_sha256=dataset.input_artifact_sha256,
            generated_by=dataset.generated_by,
        )
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--research", type=Path, default=DEFAULT_RESEARCH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-output", type=Path)
    args = parser.parse_args()

    datasets = build_datasets(seed_path=args.seed, research_path=args.research)
    manifests = build_manifests(datasets, output_dir=args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for dataset_id, dataset in datasets.items():
        output = args.output_dir / _filename(dataset.source_id)
        output.write_text(
            json.dumps(dataset.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

    summary = {
        "dataset_count": len(datasets),
        "event_count": sum(len(dataset.observations) for dataset in datasets.values()),
        "seed_sha256": _file_sha256(args.seed),
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
