"""Build reviewed Earth sport histories without inventing missing country ratings."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.application.earth_research_observations import (
    EarthObservation,
    EarthObservationDataset,
    EarthObservationDatasetManifest,
    load_normalized_observation_dataset,
    observation_dataset_id,
    observation_dataset_sha256,
)
from beta_engine.application.package_evidence_files import canonical_json_sha256
from beta_engine.domain.countries import Country, CountriesConfig
from beta_engine.domain.countries.rating_history import CountryRatingHistory, GAME_ATTRIBUTE_NAMES, RATING_SCALE_V2
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore


EARTH_COUNTRY_CODE_ALIASES: dict[str, str] = {
    # Legacy football/tennis association codes -> canonical Earth/ISO package codes.
    "ANG": "AGO",
    "CHA": "TCD",
    "EQG": "GNQ",
    "GAM": "GMB",
    "LES": "LSO",
    "SEY": "SYC",
    "NED": "NLD",
    "SUI": "CHE",
    "CRO": "HRV",
    "GRE": "GRC",
    "DEN": "DNK",
}


def _canonical_earth_country_code(code: str | None) -> str | None:
    if code is None:
        return None
    return EARTH_COUNTRY_CODE_ALIASES.get(code, code)


class EarthSource(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1)
    url: str = Field(pattern=r"^https://")
    accessed_on: date
    scope: str = Field(min_length=1)
    limitations: str = Field(min_length=1)


class EarthSportResearch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["earth_sport_research.v2"] = "earth_sport_research.v2"
    world_id: Literal["fifa_earth", "atp_earth"]
    data_cutoff: date
    sources: dict[str, EarthSource]
    observation_datasets: dict[str, EarthObservationDatasetManifest]
    countries: dict[str, CountryRatingHistory]

    @model_validator(mode="after")
    def references_exist(self) -> "EarthSportResearch":
        for dataset_id, manifest in self.observation_datasets.items():
            if dataset_id != manifest.dataset_id:
                raise ValueError(f"observation dataset key {dataset_id!r} must match manifest dataset_id")
            if manifest.source_id not in self.sources:
                raise ValueError(
                    f"observation dataset {dataset_id!r} references unknown source {manifest.source_id!r}"
                )
        for code, history in self.countries.items():
            if len(code) != 3 or not code.isascii() or not code.isalpha() or not code.isupper():
                raise ValueError(f"invalid country code {code!r}")
            if history.data_cutoff != self.data_cutoff:
                raise ValueError(f"{code}: history and dataset cutoffs must agree")
            for entry in history.years.values():
                for evidence in entry.ratings.values():
                    missing = set(evidence.source_ids) - self.sources.keys()
                    if missing:
                        raise ValueError(f"{code}: unknown sources {sorted(missing)}")
                    for observation_id in evidence.observation_ids:
                        dataset_id = observation_dataset_id(observation_id)
                        manifest = self.observation_datasets.get(dataset_id)
                        if manifest is None:
                            raise ValueError(
                                f"{code}: observation {observation_id!r} references unknown dataset {dataset_id!r}"
                            )
                        if manifest.source_id not in evidence.source_ids:
                            raise ValueError(
                                f"{code}: observation {observation_id!r} comes from source "
                                f"{manifest.source_id!r}, which is not cited by the rating evidence"
                            )
        return self


@dataclass(frozen=True)
class EarthResearchBundle:
    """File-verified research document plus portable provenance inputs."""

    research: EarthSportResearch
    datasets: dict[str, EarthObservationDataset]
    observations: dict[str, EarthObservation]
    calibration_models: dict[str, dict]


def _load_research_shards(*, research_path: Path, payload: dict) -> dict:
    """Merge optional source, observation-manifest and country-history shards."""

    world_id = payload.get("world_id")
    if world_id not in {"fifa_earth", "atp_earth"}:
        return payload

    root = research_path.parent
    merged = dict(payload)

    source_dir = root / "sources" / world_id
    sources = dict(payload.get("sources") or {})
    if source_dir.exists():
        if not source_dir.is_dir():
            raise ValueError(f"research source shard path is not a directory: {source_dir}")
        for shard_path in sorted(source_dir.glob("*.json")):
            source_id = shard_path.stem
            if not source_id or any(ch.isspace() for ch in source_id):
                raise ValueError(f"invalid research source shard filename {shard_path.name!r}")
            if source_id in sources:
                raise ValueError(f"duplicate research source {source_id!r} in inline research and shards")
            try:
                shard_payload = json.loads(shard_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"{source_id}: research source shard is unavailable or invalid") from exc
            sources[source_id] = EarthSource.model_validate(shard_payload).model_dump(mode="json")
    merged["sources"] = sources

    manifest_dir = root / "observation_manifests" / world_id
    manifests = dict(payload.get("observation_datasets") or {})
    if manifest_dir.exists():
        if not manifest_dir.is_dir():
            raise ValueError(
                f"observation manifest shard path is not a directory: {manifest_dir}"
            )
        for shard_path in sorted(manifest_dir.glob("*.json")):
            dataset_id = shard_path.stem
            if not dataset_id or any(ch.isspace() for ch in dataset_id):
                raise ValueError(f"invalid observation manifest shard filename {shard_path.name!r}")
            if dataset_id in manifests:
                raise ValueError(
                    f"duplicate observation dataset {dataset_id!r} in inline research and shards"
                )
            try:
                shard_payload = json.loads(shard_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(
                    f"{dataset_id}: observation manifest shard is unavailable or invalid"
                ) from exc
            manifest = EarthObservationDatasetManifest.model_validate(shard_payload)
            if manifest.dataset_id != dataset_id:
                raise ValueError(
                    f"observation manifest shard {dataset_id!r} declares "
                    f"{manifest.dataset_id!r}"
                )
            manifests[dataset_id] = manifest.model_dump(mode="json")
    merged["observation_datasets"] = manifests

    country_dir = root / "countries" / world_id
    countries: dict[str, dict] = {}
    for stored_code, history_payload in dict(payload.get("countries") or {}).items():
        code = _canonical_earth_country_code(stored_code)
        if code in countries:
            raise ValueError(
                f"duplicate canonical Earth country history {code!r} "
                f"after normalizing stored code {stored_code!r}"
            )
        countries[code] = history_payload
    if country_dir.exists():
        if not country_dir.is_dir():
            raise ValueError(f"country history shard path is not a directory: {country_dir}")
        for shard_path in sorted(country_dir.glob("*.json")):
            stored_code = shard_path.stem
            if (
                len(stored_code) != 3
                or not stored_code.isascii()
                or not stored_code.isalpha()
                or not stored_code.isupper()
            ):
                raise ValueError(f"invalid country history shard filename {shard_path.name!r}")
            code = _canonical_earth_country_code(stored_code)
            if code in countries:
                raise ValueError(
                    f"duplicate canonical Earth country history {code!r} "
                    f"after normalizing stored code {stored_code!r}"
                )
            try:
                shard_payload = json.loads(shard_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValueError(f"{stored_code}: country history shard is unavailable or invalid") from exc
            countries[code] = CountryRatingHistory.model_validate(shard_payload).model_dump(mode="json")
    merged["countries"] = countries

    return merged



def _required_calibration_models(research: EarthSportResearch) -> dict[str, set[str]]:
    required: dict[str, set[str]] = {}
    for code, history in research.countries.items():
        for entry in history.years.values():
            for rating in entry.ratings.values():
                if rating.calibration_model_id:
                    required.setdefault(rating.calibration_model_id, set()).add(code)
    return required


def _load_calibration_models(root: Path, research: EarthSportResearch) -> dict[str, dict]:
    """Resolve every referenced calibration definition from checked-in research."""

    required = _required_calibration_models(research)
    if not required:
        return {}
    calibration_root = root / "calibration"
    if not calibration_root.is_dir():
        raise ValueError("referenced calibration models exist but calibration directory is missing")

    models: dict[str, dict] = {}
    for path in sorted(calibration_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid calibration definition {path.name!r}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"calibration definition {path.name!r} must contain an object")
        declared_ids = [
            value for value in (
                payload.get("calibration_model_id"),
                payload.get("model_id"),
            )
            if isinstance(value, str) and value.strip()
        ]
        if not declared_ids:
            continue
        if len(set(declared_ids)) != 1:
            raise ValueError(f"calibration definition {path.name!r} declares conflicting model IDs")
        model_id = declared_ids[0]
        if model_id not in required:
            continue
        if model_id in models:
            raise ValueError(f"duplicate calibration definition for {model_id!r}")
        world_id = payload.get("world_id")
        if world_id is not None and world_id != research.world_id:
            raise ValueError(
                f"calibration model {model_id!r} targets {world_id!r}, not {research.world_id!r}"
            )
        countries = payload.get("countries")
        if countries is not None:
            if not isinstance(countries, list) or any(not isinstance(code, str) for code in countries):
                raise ValueError(f"calibration model {model_id!r} has invalid countries list")
            missing_countries = required[model_id] - set(countries)
            if missing_countries:
                raise ValueError(
                    f"calibration model {model_id!r} does not declare countries "
                    f"{sorted(missing_countries)}"
                )
        models[model_id] = payload

    missing = sorted(set(required) - models.keys())
    if missing:
        raise ValueError(f"missing calibration model definitions: {missing}")
    return models


def load_earth_research_bundle(path: Path) -> EarthResearchBundle:
    """Load a research file and fail closed on stale/tampered observation manifests."""

    research_path = path.resolve()
    root = research_path.parent
    payload = json.loads(research_path.read_text(encoding="utf-8"))
    payload = _load_research_shards(research_path=research_path, payload=payload)
    research = EarthSportResearch.model_validate(payload)
    datasets: dict[str, EarthObservationDataset] = {}
    observations: dict[str, EarthObservation] = {}

    for dataset_id, manifest in sorted(research.observation_datasets.items()):
        candidate = (root / manifest.relative_path).resolve()
        if not candidate.is_relative_to(root):
            raise ValueError(
                f"{dataset_id}: observation dataset path escapes the research directory"
            )
        try:
            dataset = load_normalized_observation_dataset(candidate)
        except OSError as exc:
            raise ValueError(
                f"{dataset_id}: observation dataset file is unavailable: {candidate}"
            ) from exc

        if dataset.dataset_id != dataset_id:
            raise ValueError(
                f"{dataset_id}: dataset file declares {dataset.dataset_id!r}"
            )
        if dataset.source_id != manifest.source_id:
            raise ValueError(
                f"{dataset_id}: dataset source {dataset.source_id!r} differs from manifest"
            )
        if len(dataset.observations) != manifest.record_count:
            raise ValueError(
                f"{dataset_id}: manifest record_count {manifest.record_count} "
                f"!= dataset count {len(dataset.observations)}"
            )
        if dataset.source_document_sha256 != manifest.source_document_sha256:
            raise ValueError(
                f"{dataset_id}: source document SHA-256 differs from manifest"
            )
        if dataset.input_artifact_sha256 != manifest.input_artifact_sha256:
            raise ValueError(
                f"{dataset_id}: input artifact SHA-256 differs from manifest"
            )
        if dataset.generated_by != manifest.generated_by:
            raise ValueError(
                f"{dataset_id}: generated_by differs from manifest"
            )
        actual_hash = observation_dataset_sha256(dataset)
        if actual_hash != manifest.sha256:
            raise ValueError(
                f"{dataset_id}: semantic SHA-256 mismatch; "
                f"manifest={manifest.sha256}, actual={actual_hash}"
            )

        # Keep the verified dataset object byte/semantic-identical to its manifest,
        # but expose canonical Earth identity through the resolved observation index.
        datasets[dataset_id] = dataset
        for observation in dataset.observations:
            canonical_code = _canonical_earth_country_code(observation.earth_country_code)
            resolved_observation = (
                observation
                if canonical_code == observation.earth_country_code
                else observation.model_copy(update={"earth_country_code": canonical_code})
            )
            if resolved_observation.observation_id in observations:
                raise ValueError(
                    f"duplicate observation ID across datasets: "
                    f"{resolved_observation.observation_id!r}"
                )
            observations[resolved_observation.observation_id] = resolved_observation

    for code, history in research.countries.items():
        for year in history.years.values():
            for evidence in year.ratings.values():
                for observation_id in evidence.observation_ids:
                    if observation_id not in observations:
                        raise ValueError(
                            f"{code}: rating references missing normalized observation "
                            f"{observation_id!r}"
                        )

    calibration_models = _load_calibration_models(root, research)

    return EarthResearchBundle(
        research=research,
        datasets=datasets,
        observations=observations,
        calibration_models=calibration_models,
    )


def audit_earth_research(research: EarthSportResearch, countries: list[Country]) -> dict:
    """Coverage is not proof of accuracy; missing evidence is an explicit release blocker."""
    required = {country.code for country in countries}
    missing_countries = sorted(required - research.countries.keys())
    extra_countries = sorted(research.countries.keys() - required)
    missing_years = {
        code: history.missing_earth_years
        for code, history in sorted(research.countries.items())
        if history.missing_earth_years
    }
    method_counts: dict[str, int] = {}
    confidence_counts: dict[str, int] = {}
    for history in research.countries.values():
        for year in history.years.values():
            for rating in year.ratings.values():
                method_counts[rating.method] = method_counts.get(rating.method, 0) + 1
                confidence_counts[rating.confidence] = confidence_counts.get(rating.confidence, 0) + 1
    return {
        "world_id": research.world_id,
        "coverage_complete": not (missing_countries or extra_countries or missing_years),
        "required_years": {"from": 1955, "to": 2026},
        "required_country_count": len(required),
        "required_rating_count": len(required) * 72 * len(GAME_ATTRIBUTE_NAMES),
        "authored_rating_count": sum(method_counts.values()),
        "missing_countries": missing_countries,
        "unexpected_countries": extra_countries,
        "missing_years": missing_years,
        "methods": method_counts,
        "confidence": confidence_counts,
        "observation_dataset_count": len(research.observation_datasets),
        "observation_record_count": sum(
            manifest.record_count for manifest in research.observation_datasets.values()
        ),
        "data_cutoff": research.data_cutoff.isoformat(),
        "realism_validated": False,
    }


def build_earth_package(*, base_package: Path, bundle: EarthResearchBundle, output: Path) -> dict:
    """Build a self-contained historical package atomically without touching its source."""

    research = bundle.research
    base_package = base_package.resolve()
    output = output.resolve()
    if output.is_relative_to(base_package):
        raise ValueError("output must be outside the base package; recursive self-copy is forbidden")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    if set(bundle.datasets) != set(research.observation_datasets):
        raise ValueError("verified observation datasets do not match the research manifest catalogue")
    required_models = set(_required_calibration_models(research))
    if set(bundle.calibration_models) != required_models:
        raise ValueError("verified calibration definitions do not match referenced calibration models")

    countries = WorldPackageCountryStore(base_package).load_config().countries
    report = audit_earth_research(research, countries)
    if not report["coverage_complete"]:
        raise ValueError("Earth research is incomplete; run audit_earth_research for missing countries/years")

    output.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".earth-build-", dir=output.parent))
    try:
        shutil.copytree(base_package, staged, dirs_exist_ok=True)
        converted = []
        for country in countries:
            history = research.countries[country.code]
            entry = history.years[history.reference_year]
            payload = country.model_dump()
            payload.update({name: entry.ratings[name].value for name in GAME_ATTRIBUTE_NAMES})
            payload.update(
                rating_scale=RATING_SCALE_V2,
                rating_history=history.model_dump(),
                rating_effective_year=None,
                court_count=None,
            )
            converted.append(Country.model_validate(payload))
        WorldPackageCountryStore(staged).replace_dataset(CountriesConfig(countries=converted))

        metadata = json.loads((staged / "world.json").read_text(encoding="utf-8"))
        metadata.update(
            world_id=research.world_id,
            name="FIFA Earth Package" if research.world_id == "fifa_earth" else "ATP Earth Package",
            description=(
                "Historical sporting environment estimates, 1955–2026; "
                "project-authored, not a federation endorsement."
            ),
            version="v1",
            type="official",
            source="built_in",
            editable=False,
            deletable=False,
            archivable=False,
            rating_scale=RATING_SCALE_V2,
            rating_years={"from": 1955, "to": 2026},
            data_cutoff=research.data_cutoff.isoformat(),
        )
        (staged / "world.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        generation = staged / "generation"
        generation.mkdir(exist_ok=True)
        (generation / "country_rating_sources.json").write_text(
            json.dumps(
                {key: value.model_dump(mode="json") for key, value in research.sources.items()},
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        observation_root = generation / "observations"
        observation_root.mkdir(exist_ok=True)
        packaged_manifests: dict[str, dict] = {}
        for dataset_id, manifest in sorted(research.observation_datasets.items()):
            dataset = bundle.datasets[dataset_id]
            relative_path = f"generation/observations/{dataset_id}.json"
            (staged / relative_path).write_text(
                json.dumps(dataset.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            packaged_manifests[dataset_id] = manifest.model_copy(
                update={"relative_path": relative_path}
            ).model_dump(mode="json")
        (generation / "country_rating_observation_datasets.json").write_text(
            json.dumps(packaged_manifests, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        calibration_root = generation / "calibration"
        calibration_root.mkdir(exist_ok=True)
        calibration_catalog: dict[str, dict] = {}
        for model_id, model in sorted(bundle.calibration_models.items()):
            if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", model_id) is None:
                raise ValueError(f"unsafe calibration model ID {model_id!r}")
            relative_path = f"generation/calibration/{model_id}.json"
            (staged / relative_path).write_text(
                json.dumps(model, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            calibration_catalog[model_id] = {
                "relative_path": relative_path,
                "sha256": canonical_json_sha256(model),
            }
        (generation / "country_rating_calibration_models.json").write_text(
            json.dumps(
                {
                    "schema_version": "earth_country_calibration_catalog.v1",
                    "models": calibration_catalog,
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        (generation / "country_rating_coverage.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        if WorldPackageCountryStore(staged).load_config().countries != converted:
            raise ValueError("Earth package did not round-trip")

        from beta_engine.application.country_history_validation import country_history_errors

        persisted_errors = country_history_errors(staged, metadata, converted)
        if persisted_errors:
            raise ValueError(
                "built Earth package provenance validation failed: "
                + "; ".join(persisted_errors[:10])
            )

        staged.rename(output)
        return report
    finally:
        if staged.exists():
            shutil.rmtree(staged)
