"""Validate persisted history declarations and their evidence catalogue."""
from __future__ import annotations

import json
from pathlib import Path

from beta_engine.application.earth_research_observations import (
    EarthObservationDatasetManifest,
    observation_dataset_id,
)
from beta_engine.domain.countries import Country
from beta_engine.domain.countries.rating_history import RATING_SCALE_V2


def country_history_errors(root: Path, metadata: dict, countries: list[Country]) -> list[str]:
    histories = [country for country in countries if country.rating_history is not None]
    declaration = metadata.get("rating_years")
    if declaration is None and not histories:
        return []  # Existing worlds keep their legacy contract.
    errors = []
    required: set[int] = set()
    if declaration is not None:
        if (not isinstance(declaration, dict)
                or set(declaration) != {"from", "to"}
                or any(type(value) is not int for value in declaration.values())
                or not 1955 <= declaration["from"] <= declaration["to"] <= 2026):
            errors.append("rating_years must declare an ordered interval within 1955–2026")
        else:
            required = set(range(declaration["from"], declaration["to"] + 1))
        if metadata.get("rating_scale") != RATING_SCALE_V2:
            errors.append("a historical package must declare the 1–10 rating scale")
    try:
        sources = json.loads((root / "generation/country_rating_sources.json").read_text())
        if not isinstance(sources, dict) or not sources:
            raise ValueError("source catalogue must be a non-empty object")
        # Reuse the source contract used by the builder, including URL and date types.
        from beta_engine.application.earth_package_builder import EarthSource
        for value in sources.values():
            EarthSource.model_validate(value)
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"invalid country rating source catalogue: {exc}")
        sources = {}
    try:
        raw_manifests = json.loads(
            (root / "generation/country_rating_observation_datasets.json").read_text()
        )
        if not isinstance(raw_manifests, dict) or not raw_manifests:
            raise ValueError("observation dataset catalogue must be a non-empty object")
        manifests: dict[str, EarthObservationDatasetManifest] = {}
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
        manifests = {}
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
        unknown = {source for entry in history.years.values() for rating in entry.ratings.values()
                   for source in rating.source_ids if source not in sources}
        if unknown:
            errors.append(f"{country.code}: unknown rating sources {sorted(unknown)}")
        for entry in history.years.values():
            for rating in entry.ratings.values():
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
                    elif manifest.source_id not in rating.source_ids:
                        errors.append(
                            f"{country.code}: observation {observation_id!r} source "
                            f"{manifest.source_id!r} is not cited by the rating evidence"
                        )
    return errors
