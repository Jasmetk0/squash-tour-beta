"""Build reviewed Earth sport histories without inventing missing country ratings."""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.application.earth_research_observations import (
    EarthObservationDatasetManifest,
    observation_dataset_id,
)
from beta_engine.domain.countries import Country, CountriesConfig
from beta_engine.domain.countries.rating_history import CountryRatingHistory, GAME_ATTRIBUTE_NAMES, RATING_SCALE_V2
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore


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


def build_earth_package(*, base_package: Path, research: EarthSportResearch, output: Path) -> dict:
    """All-or-nothing build into a new directory; shared sources are never changed."""
    base_package = base_package.resolve()
    output = output.resolve()
    if output.is_relative_to(base_package):
        raise ValueError("output must be outside the base package; recursive self-copy is forbidden")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
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
            payload.update(rating_scale=RATING_SCALE_V2, rating_history=history.model_dump(),
                           rating_effective_year=None, court_count=None)
            converted.append(Country.model_validate(payload))
        WorldPackageCountryStore(staged).replace_dataset(CountriesConfig(countries=converted))
        metadata = json.loads((staged / "world.json").read_text())
        metadata.update(world_id=research.world_id,
                        name="FIFA Earth Package" if research.world_id == "fifa_earth" else "ATP Earth Package",
                        description="Historical sporting environment estimates, 1955–2026; project-authored, not a federation endorsement.",
                        version="v1", type="official", source="built_in", editable=False,
                        deletable=False, archivable=False, rating_scale=RATING_SCALE_V2,
                        rating_years={"from": 1955, "to": 2026}, data_cutoff=research.data_cutoff.isoformat())
        (staged / "world.json").write_text(json.dumps(metadata, indent=2) + "\n")
        generation = staged / "generation"
        generation.mkdir(exist_ok=True)
        (generation / "country_rating_sources.json").write_text(json.dumps(
            {key: value.model_dump(mode="json") for key, value in research.sources.items()}, indent=2
        ) + "\n")
        (generation / "country_rating_observation_datasets.json").write_text(json.dumps(
            {
                key: value.model_dump(mode="json")
                for key, value in research.observation_datasets.items()
            },
            indent=2,
        ) + "\n")
        (generation / "country_rating_coverage.json").write_text(json.dumps(report, indent=2) + "\n")
        # Round-trip the actual persisted country source before publishing the directory.
        if WorldPackageCountryStore(staged).load_config().countries != converted:
            raise ValueError("Earth package did not round-trip")
        staged.rename(output)
        return report
    finally:
        if staged.exists():
            shutil.rmtree(staged)
