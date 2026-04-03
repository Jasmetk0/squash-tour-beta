"""File-backed countries dataset management over canonical world config."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from beta_engine.domain.countries import CountriesConfig, Country
from beta_engine.infrastructure.world_config import load_countries_config


@dataclass(frozen=True)
class CountriesDatasetMetadata:
    dataset_status: str | None
    country_count: int
    source_path: str


@dataclass(slots=True)
class CountriesConfigService:
    """CRUD management for countries backed by canonical JSON config."""

    config_path: Path = Path("config/world/countries.json")

    def __post_init__(self) -> None:
        if not isinstance(self.config_path, Path):
            self.config_path = Path(self.config_path)

    def list_countries(self) -> list[Country]:
        return self._load().countries

    def get_country(self, code: str) -> Country | None:
        normalized = code.upper()
        return next((country for country in self._load().countries if country.code == normalized), None)

    def get_metadata(self) -> CountriesDatasetMetadata:
        config = self._load()
        return CountriesDatasetMetadata(
            dataset_status=config.dataset_status,
            country_count=len(config.countries),
            source_path=str(self.config_path),
        )

    def create_country(self, payload: Country) -> Country:
        config = self._load()
        if any(country.code == payload.code for country in config.countries):
            raise ValueError(f"country with code '{payload.code}' already exists")

        updated = CountriesConfig(
            dataset_status=config.dataset_status,
            countries=[*config.countries, payload],
        )
        self._save(updated)
        return payload

    def update_country(self, code: str, payload: Country) -> Country:
        normalized = code.upper()
        config = self._load()

        if payload.code != normalized and any(country.code == payload.code for country in config.countries):
            raise ValueError(f"country with code '{payload.code}' already exists")

        replaced = False
        updated_countries: list[Country] = []
        for country in config.countries:
            if country.code == normalized:
                updated_countries.append(payload)
                replaced = True
            else:
                updated_countries.append(country)

        if not replaced:
            raise LookupError(f"country '{normalized}' was not found")

        updated = CountriesConfig(dataset_status=config.dataset_status, countries=updated_countries)
        self._save(updated)
        return payload

    def delete_country(self, code: str) -> None:
        normalized = code.upper()
        config = self._load()
        remaining = [country for country in config.countries if country.code != normalized]

        if len(remaining) == len(config.countries):
            raise LookupError(f"country '{normalized}' was not found")

        updated = CountriesConfig(dataset_status=config.dataset_status, countries=remaining)
        self._save(updated)

    def replace_dataset(self, payload: CountriesConfig) -> CountriesConfig:
        seen: set[str] = set()
        for country in payload.countries:
            if country.code in seen:
                raise ValueError(f"duplicate country code '{country.code}' in dataset")
            seen.add(country.code)

        self._save(payload)
        return payload

    def _load(self) -> CountriesConfig:
        return load_countries_config(self.config_path)

    def _save(self, payload: CountriesConfig) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        target = self.config_path
        tmp_path = target.with_suffix(f"{target.suffix}.tmp")
        with tmp_path.open("w", encoding="utf-8") as fh:
            json.dump(payload.model_dump(mode="json"), fh, indent=2)
            fh.write("\n")
        tmp_path.replace(target)
