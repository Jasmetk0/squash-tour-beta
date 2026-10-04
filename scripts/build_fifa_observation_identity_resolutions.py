"""Build exact observation->Earth identity resolution sets for FIFA research.

This consumes the canonical normalized observation datasets plus the reviewed source
identity override/reconciliation rules. It never changes source facts and never
turns manual/unresolved identities into resolved Earth countries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.application.earth_research_identity import (
    EarthObservationIdentityManifest,
    EarthObservationIdentityResolution,
    EarthObservationIdentityResolutionSet,
    identity_resolution_sha256,
)
from scripts.reconcile_fifa_big_count_identities import (
    DEFAULT_EARTH_ROOT,
    DEFAULT_OVERRIDES as BIG_COUNT_OVERRIDES,
    build_report as build_big_count_report,
)
from scripts.reconcile_fifa_professional_2023_identities import (
    DEFAULT_OVERRIDES as PROFESSIONAL_OVERRIDES,
    build_report as build_professional_report,
)

RESEARCH = Path("config/earth_research/fifa_earth.json")
DEFAULT_OUTPUT_DIR = Path("config/earth_research/identity_resolutions")

BIG_COUNT_DATASET_IDS = (
    "fifa-big-count-2006-all-players-v2",
    "fifa-big-count-2006-registered-v2",
    "fifa-big-count-2006-unregistered-v2",
    "fifa-big-count-2006-clubs-v2",
    "fifa-big-count-2006-officials-v2",
)
PROFESSIONAL_DATASET_IDS = (
    "fifa-professional-2023-players-v2",
    "fifa-professional-2023-clubs-v2",
)

SET_SPECS = {
    "fifa-big-count-2006-identity-v1": {
        "filename": "fifa_big_count_2006_identity_v1.json",
        "dataset_ids": BIG_COUNT_DATASET_IDS,
        "source_id": "fifa-big-count-2006",
        "override_path": BIG_COUNT_OVERRIDES,
    },
    "fifa-professional-2023-identity-v1": {
        "filename": "fifa_professional_2023_identity_v1.json",
        "dataset_ids": PROFESSIONAL_DATASET_IDS,
        "source_id": "fifa-professional-2023",
        "override_path": PROFESSIONAL_OVERRIDES,
    },
}


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _earth_identity_catalog_sha256(root: Path = DEFAULT_EARTH_ROOT) -> str:
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    codes = index["country_codes"]
    payload = []
    for code in sorted(codes):
        country = json.loads((root / code / "country.json").read_text(encoding="utf-8"))
        payload.append({"code": code, "name": country["name"]})
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _resolution_payload(mapping: dict[str, Any]) -> tuple[str, str, str | None, list[str], str]:
    status = mapping["status"]
    if status == "explicit_map":
        return (
            "direct",
            "explicit_override",
            mapping["earth_code"],
            [],
            mapping.get("reason") or "Reviewed explicit source-to-Earth override.",
        )
    if status == "exact_normalized_name":
        return (
            "direct",
            "exact_normalized_name",
            mapping["earth_code"],
            [],
            "Unique normalized source association label matches one Earth country name.",
        )
    if status == "aggregate_member":
        return (
            "aggregate_member",
            "aggregate_group",
            mapping["earth_code"],
            [],
            mapping["reason"],
        )
    if status == "manual_review":
        candidates = []
        candidate = mapping.get("candidate_earth_code")
        if candidate:
            candidates.append(candidate)
        return (
            "manual_review",
            "manual_review",
            None,
            candidates,
            mapping["reason"],
        )
    if status == "unresolved":
        return (
            "unresolved",
            "unresolved",
            None,
            list(mapping.get("candidate_codes") or []),
            "No unique reviewed Earth identity resolution is available.",
        )
    raise ValueError(f"unsupported mapping status {status!r}")


def _make_resolution(
    *,
    observation,
    mapping: dict[str, Any],
) -> EarthObservationIdentityResolution:
    status, method, earth_code, candidates, reason = _resolution_payload(mapping)
    return EarthObservationIdentityResolution(
        observation_id=observation.observation_id,
        source_id=observation.source_id,
        source_entity=observation.source_entity,
        source_page=observation.source_page,
        status=status,
        method=method,
        confidence="high" if status in {"direct", "aggregate_member"} else "low",
        earth_country_code=earth_code,
        candidate_earth_codes=candidates,
        reason=reason,
    )


def build_big_count_resolution_set() -> EarthObservationIdentityResolutionSet:
    bundle = load_earth_research_bundle(RESEARCH)
    report = build_big_count_report()
    by_association = {item["association"]: item for item in report["mappings"]}
    resolutions = []

    for dataset_id in BIG_COUNT_DATASET_IDS:
        dataset = bundle.datasets[dataset_id]
        for observation in dataset.observations:
            mapping = by_association.get(observation.source_entity)
            if mapping is None:
                raise ValueError(
                    f"Big Count normalized observation lacks identity mapping: "
                    f"{observation.observation_id}"
                )
            resolutions.append(_make_resolution(observation=observation, mapping=mapping))

    return EarthObservationIdentityResolutionSet(
        resolution_set_id="fifa-big-count-2006-identity-v1",
        source_id="fifa-big-count-2006",
        generated_by="scripts/build_fifa_observation_identity_resolutions.py",
        mapping_algorithm_id="fifa-source-association-to-earth.v1",
        input_dataset_sha256s={
            dataset_id: bundle.research.observation_datasets[dataset_id].sha256
            for dataset_id in BIG_COUNT_DATASET_IDS
        },
        override_artifact_sha256=_file_sha256(BIG_COUNT_OVERRIDES),
        earth_identity_catalog_sha256=_earth_identity_catalog_sha256(),
        resolutions=sorted(resolutions, key=lambda item: item.observation_id),
    )


def build_professional_resolution_set() -> EarthObservationIdentityResolutionSet:
    bundle = load_earth_research_bundle(RESEARCH)
    report = build_professional_report()
    by_page = {int(item["pdf_page"]): item for item in report["mappings"]}
    resolutions = []

    for dataset_id in PROFESSIONAL_DATASET_IDS:
        dataset = bundle.datasets[dataset_id]
        for observation in dataset.observations:
            if observation.source_page is None:
                raise ValueError(
                    f"Professional observation lacks source page: {observation.observation_id}"
                )
            mapping = by_page.get(observation.source_page)
            if mapping is None or mapping["association"] != observation.source_entity:
                raise ValueError(
                    f"Professional observation/page identity mismatch: "
                    f"{observation.observation_id}"
                )
            resolutions.append(_make_resolution(observation=observation, mapping=mapping))

    return EarthObservationIdentityResolutionSet(
        resolution_set_id="fifa-professional-2023-identity-v1",
        source_id="fifa-professional-2023",
        generated_by="scripts/build_fifa_observation_identity_resolutions.py",
        mapping_algorithm_id="fifa-source-association-to-earth.v1",
        input_dataset_sha256s={
            dataset_id: bundle.research.observation_datasets[dataset_id].sha256
            for dataset_id in PROFESSIONAL_DATASET_IDS
        },
        override_artifact_sha256=_file_sha256(PROFESSIONAL_OVERRIDES),
        earth_identity_catalog_sha256=_earth_identity_catalog_sha256(),
        resolutions=sorted(resolutions, key=lambda item: item.observation_id),
    )


def build_resolution_sets() -> dict[str, EarthObservationIdentityResolutionSet]:
    sets = {
        "fifa-big-count-2006-identity-v1": build_big_count_resolution_set(),
        "fifa-professional-2023-identity-v1": build_professional_resolution_set(),
    }
    observation_ids = [
        resolution.observation_id
        for resolution_set in sets.values()
        for resolution in resolution_set.resolutions
    ]
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("identity resolution sets overlap observation IDs")
    return sets


def build_manifests(
    sets: dict[str, EarthObservationIdentityResolutionSet],
    *,
    output_dir: Path,
) -> dict[str, EarthObservationIdentityManifest]:
    manifests = {}
    for resolution_set_id, resolution_set in sets.items():
        spec = SET_SPECS[resolution_set_id]
        output = output_dir / spec["filename"]
        relative = output.relative_to(Path("config/earth_research"))
        manifests[resolution_set_id] = EarthObservationIdentityManifest(
            resolution_set_id=resolution_set_id,
            source_id=resolution_set.source_id,
            relative_path=relative.as_posix(),
            sha256=identity_resolution_sha256(resolution_set),
            record_count=len(resolution_set.resolutions),
            generated_by=resolution_set.generated_by,
        )
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-output", type=Path)
    args = parser.parse_args()

    sets = build_resolution_sets()
    manifests = build_manifests(sets, output_dir=args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for resolution_set_id, resolution_set in sets.items():
        output = args.output_dir / SET_SPECS[resolution_set_id]["filename"]
        output.write_text(
            json.dumps(
                resolution_set.model_dump(mode="json"),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    summary = {
        "resolution_set_count": len(sets),
        "resolution_count": sum(len(item.resolutions) for item in sets.values()),
        "sets": {
            set_id: {
                "record_count": manifests[set_id].record_count,
                "sha256": manifests[set_id].sha256,
            }
            for set_id in sets
        },
    }
    print(json.dumps(summary, indent=2))

    if args.manifest_output:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_text(
            json.dumps(
                {
                    set_id: manifest.model_dump(mode="json")
                    for set_id, manifest in manifests.items()
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
