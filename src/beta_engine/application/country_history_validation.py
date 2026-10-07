"""Validate persisted history declarations and their complete portable provenance."""
from __future__ import annotations

import json
from pathlib import Path

from beta_engine.application.earth_research_observations import (
    EarthObservation,
    EarthObservationDatasetManifest,
    load_normalized_observation_dataset,
    observation_dataset_id,
    observation_dataset_sha256,
)
from beta_engine.application.package_evidence_files import (
    canonical_json_sha256,
    load_json_object,
    safe_package_file,
)
from beta_engine.domain.countries import Country
from beta_engine.domain.countries.rating_history import RATING_SCALE_V2


def _calibration_model_id(payload: dict) -> str | None:
    values = [
        value
        for value in (payload.get("calibration_model_id"), payload.get("model_id"))
        if isinstance(value, str) and value.strip()
    ]
    if not values:
        return None
    if len(set(values)) != 1:
        raise ValueError("calibration definition declares conflicting model IDs")
    return values[0]


def country_history_errors(root: Path, metadata: dict, countries: list[Country]) -> list[str]:
    histories = [country for country in countries if country.rating_history is not None]
    declaration = metadata.get("rating_years")
    if declaration is None and not histories:
        return []  # Existing worlds keep their legacy contract.

    errors: list[str] = []
    required: set[int] = set()
    if declaration is not None:
        if (
            not isinstance(declaration, dict)
            or set(declaration) != {"from", "to"}
            or any(type(value) is not int for value in declaration.values())
            or not 1955 <= declaration["from"] <= declaration["to"] <= 2026
        ):
            errors.append("rating_years must declare an ordered interval within 1955–2026")
        else:
            required = set(range(declaration["from"], declaration["to"] + 1))
        if metadata.get("rating_scale") != RATING_SCALE_V2:
            errors.append("a historical package must declare the 1–10 rating scale")

    sources: dict = {}
    try:
        raw_sources = load_json_object(root / "generation/country_rating_sources.json")
        if not raw_sources:
            raise ValueError("source catalogue must be a non-empty object")
        from beta_engine.application.earth_package_builder import EarthSource

        sources = {
            source_id: EarthSource.model_validate(value)
            for source_id, value in raw_sources.items()
        }
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"invalid country rating source catalogue: {exc}")

    manifests: dict[str, EarthObservationDatasetManifest] = {}
    try:
        raw_manifests = load_json_object(
            root / "generation/country_rating_observation_datasets.json"
        )
        if not raw_manifests:
            raise ValueError("observation dataset catalogue must be a non-empty object")
        for dataset_id, value in raw_manifests.items():
            manifest = EarthObservationDatasetManifest.model_validate(value)
            if dataset_id != manifest.dataset_id:
                raise ValueError(
                    f"observation dataset key {dataset_id!r} must match manifest dataset_id"
                )
            if manifest.source_id not in sources:
                raise ValueError(
                    f"observation dataset {dataset_id!r} references unknown source "
                    f"{manifest.source_id!r}"
                )
            manifests[dataset_id] = manifest
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"invalid country rating observation dataset catalogue: {exc}")

    observations: dict[str, EarthObservation] = {}
    for dataset_id, manifest in sorted(manifests.items()):
        try:
            dataset_path = safe_package_file(root, manifest.relative_path)
            dataset = load_normalized_observation_dataset(dataset_path)
            if dataset.dataset_id != dataset_id:
                raise ValueError(
                    f"dataset file declares {dataset.dataset_id!r}, expected {dataset_id!r}"
                )
            if dataset.source_id != manifest.source_id:
                raise ValueError(
                    f"dataset source {dataset.source_id!r} differs from manifest "
                    f"{manifest.source_id!r}"
                )
            source = sources.get(manifest.source_id)
            if source is None:
                raise ValueError(f"dataset references unavailable source {manifest.source_id!r}")
            if dataset.source_url != source.url:
                raise ValueError(
                    f"dataset source URL {dataset.source_url!r} differs from source catalogue"
                )
            if len(dataset.observations) != manifest.record_count:
                raise ValueError(
                    f"manifest record_count {manifest.record_count} != "
                    f"dataset count {len(dataset.observations)}"
                )
            if dataset.source_document_sha256 != manifest.source_document_sha256:
                raise ValueError("source document SHA-256 differs from manifest")
            if dataset.input_artifact_sha256 != manifest.input_artifact_sha256:
                raise ValueError("input artifact SHA-256 differs from manifest")
            if dataset.generated_by != manifest.generated_by:
                raise ValueError("generated_by differs from manifest")
            actual_hash = observation_dataset_sha256(dataset)
            if actual_hash != manifest.sha256:
                raise ValueError(
                    f"semantic SHA-256 mismatch; manifest={manifest.sha256}, actual={actual_hash}"
                )
            for observation in dataset.observations:
                if observation.observation_id in observations:
                    raise ValueError(
                        f"duplicate observation ID {observation.observation_id!r}"
                    )
                observations[observation.observation_id] = observation
        except (OSError, ValueError, TypeError) as exc:
            errors.append(f"observation dataset {dataset_id!r} is invalid: {exc}")

    required_models = {
        rating.calibration_model_id
        for country in histories
        for entry in country.rating_history.years.values()
        for rating in entry.ratings.values()
        if rating.calibration_model_id
    }
    calibration_models: dict[str, dict] = {}
    calibration_catalog_path = root / "generation/country_rating_calibration_models.json"
    if required_models or calibration_catalog_path.exists():
        try:
            catalog = load_json_object(calibration_catalog_path)
            if catalog.get("schema_version") != "earth_country_calibration_catalog.v1":
                raise ValueError("unsupported calibration catalogue schema")
            raw_models = catalog.get("models")
            if not isinstance(raw_models, dict):
                raise ValueError("calibration catalogue models must be an object")
            for model_id, declaration_value in raw_models.items():
                if not isinstance(model_id, str) or not model_id:
                    raise ValueError("calibration model IDs must be non-empty strings")
                if not isinstance(declaration_value, dict):
                    raise ValueError(f"calibration entry {model_id!r} must be an object")
                relative_path = declaration_value.get("relative_path")
                expected_hash = declaration_value.get("sha256")
                if not isinstance(relative_path, str):
                    raise ValueError(f"calibration entry {model_id!r} lacks relative_path")
                if (
                    not isinstance(expected_hash, str)
                    or len(expected_hash) != 64
                    or any(ch not in "0123456789abcdef" for ch in expected_hash)
                ):
                    raise ValueError(f"calibration entry {model_id!r} has invalid sha256")
                model_path = safe_package_file(root, relative_path)
                model = load_json_object(model_path)
                if _calibration_model_id(model) != model_id:
                    raise ValueError(
                        f"calibration file for {model_id!r} declares another model ID"
                    )
                actual_hash = canonical_json_sha256(model)
                if actual_hash != expected_hash:
                    raise ValueError(
                        f"calibration model {model_id!r} SHA-256 mismatch; "
                        f"catalogue={expected_hash}, actual={actual_hash}"
                    )
                world_id = model.get("world_id")
                if world_id is not None and world_id != metadata.get("world_id"):
                    raise ValueError(
                        f"calibration model {model_id!r} targets {world_id!r}, "
                        f"not {metadata.get('world_id')!r}"
                    )
                calibration_models[model_id] = model
        except (OSError, ValueError, TypeError) as exc:
            errors.append(f"invalid country rating calibration catalogue: {exc}")

    missing_models = sorted(required_models - calibration_models.keys())
    if missing_models:
        errors.append(f"missing calibration model definitions {missing_models}")

    for country in countries:
        history = country.rating_history
        if history is None:
            if required:
                errors.append(f"{country.code}: missing declared rating history")
            continue
        missing = required - history.years.keys()
        if missing:
            errors.append(f"{country.code}: missing declared rating years {sorted(missing)}")
        if metadata.get("data_cutoff") != history.data_cutoff.isoformat():
            errors.append(f"{country.code}: history cutoff differs from package cutoff")
        unknown = {
            source
            for entry in history.years.values()
            for rating in entry.ratings.values()
            for source in rating.source_ids
            if source not in sources
        }
        if unknown:
            errors.append(f"{country.code}: unknown rating sources {sorted(unknown)}")
        for entry in history.years.values():
            for rating in entry.ratings.values():
                if rating.calibration_model_id:
                    model = calibration_models.get(rating.calibration_model_id)
                    countries_declared = model.get("countries") if model else None
                    if (
                        isinstance(countries_declared, list)
                        and country.code not in countries_declared
                    ):
                        errors.append(
                            f"{country.code}: calibration model "
                            f"{rating.calibration_model_id!r} does not declare this country"
                        )
                for observation_id in rating.observation_ids:
                    try:
                        dataset_id = observation_dataset_id(observation_id)
                    except ValueError as exc:
                        errors.append(f"{country.code}: invalid observation reference: {exc}")
                        continue
                    manifest = manifests.get(dataset_id)
                    if manifest is None:
                        errors.append(
                            f"{country.code}: observation {observation_id!r} references "
                            f"unknown dataset {dataset_id!r}"
                        )
                        continue
                    observation = observations.get(observation_id)
                    if observation is None:
                        errors.append(
                            f"{country.code}: rating references missing normalized observation "
                            f"{observation_id!r}"
                        )
                        continue
                    if observation.source_id != manifest.source_id:
                        errors.append(
                            f"{country.code}: observation {observation_id!r} source differs "
                            "from its dataset manifest"
                        )
                    if manifest.source_id not in rating.source_ids:
                        errors.append(
                            f"{country.code}: observation {observation_id!r} source "
                            f"{manifest.source_id!r} is not cited by the rating evidence"
                        )
    return errors
