"""Canonical directory-backed storage for World Package countries."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, StrictInt, field_validator

from beta_engine.domain.countries import CountriesConfig, Country

COUNTRIES_INDEX_SCHEMA = "world_package_countries_index.v1"
COUNTRY_IDENTITY_SCHEMA = "world_package_country.v1"
COUNTRY_ATTRIBUTE_SCHEMA = "country_attribute.v1"
COUNTRY_POPULATION_SCHEMA = "country_population.v1"
PACKAGE_FORMAT_VERSION = "world_package_directory.v1"

# Canonical Country V1 storage.  Factual fields and game ratings intentionally
# share the same modular attribute envelope, but only the six game fields are
# authored simulation ratings.
COUNTRY_DATA_ATTRIBUTE_NAMES = (
    "area_km2",
    "region",
    "travel_region",
    "court_count",
)
COUNTRY_GAME_ATTRIBUTE_NAMES = (
    "squash_popularity",
    "squash_access",
    "development_quality",
    "competition_quality",
    "elite_support",
    "squash_tradition",
)
ATTRIBUTE_NAMES = (*COUNTRY_DATA_ATTRIBUTE_NAMES, *COUNTRY_GAME_ATTRIBUTE_NAMES)

# Read-only migration bridge for World Packages authored before Country V1.
# New writes never recreate these files.
LEGACY_ATTRIBUTE_FALLBACKS: dict[str, tuple[str, ...]] = {
    "squash_access": ("wealth_support",),
    "development_quality": ("system_quality",),
    "competition_quality": ("competition_density", "system_quality"),
    "elite_support": ("federation_quality", "wealth_support"),
}
LEGACY_ATTRIBUTE_NAMES = (
    "wealth_support",
    "system_quality",
    "competition_density",
    "federation_quality",
    "style_dna",
)


class CountriesIndex(BaseModel):
    schema_version: str = COUNTRIES_INDEX_SCHEMA
    dataset_status: str | None = None
    country_codes: list[str] = Field(min_length=1)


class CountryIdentity(BaseModel):
    schema_version: str = COUNTRY_IDENTITY_SCHEMA
    code: str
    name: str
    flag_asset: str | None = None
    notes: str | None = None


class CountryAttribute(BaseModel):
    schema_version: str = COUNTRY_ATTRIBUTE_SCHEMA
    value: Any


class CountryPopulation(BaseModel):
    schema_version: str = COUNTRY_POPULATION_SCHEMA
    default_year: int
    values_by_year: dict[int, StrictInt]

    @field_validator("values_by_year")
    @classmethod
    def validate_timeline(cls, value: dict[int, int]) -> dict[int, int]:
        if 2020 not in value:
            raise ValueError("population timeline must contain default year 2020")
        if any(year < 1955 or year > 2050 for year in value):
            raise ValueError("population years must be between 1955 and 2050")
        if any(isinstance(population, bool) or population <= 0 for population in value.values()):
            raise ValueError("population values must be positive integers")
        return value


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"{path} is missing") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as fh:
        json.dump(payload, fh, indent=2, sort_keys=False)
        fh.write("\n")
        temporary = Path(fh.name)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _coerce_rating(value: Any, *, field_name: str) -> int:
    try:
        rating = int(round(float(value)))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"legacy {field_name} value {value!r} cannot be migrated to a 1..5 rating") from exc
    if not 1 <= rating <= 5:
        raise ValueError(f"legacy {field_name} value {value!r} is outside the supported 1..5 range")
    return rating


@dataclass(slots=True)
class WorldPackageCountryStore:
    """Translate modular package files to and from the typed country domain."""

    package_root: Path

    def __post_init__(self) -> None:
        self.package_root = Path(self.package_root)

    @property
    def countries_root(self) -> Path:
        return self.package_root / "countries"

    @property
    def index_path(self) -> Path:
        return self.countries_root / "index.json"

    def load_index(self) -> CountriesIndex:
        index = CountriesIndex.model_validate(_read_object(self.index_path))
        if index.schema_version != COUNTRIES_INDEX_SCHEMA:
            raise ValueError(f"{self.index_path} has unsupported schema_version {index.schema_version!r}")
        if len(index.country_codes) != len(set(index.country_codes)):
            raise ValueError(f"{self.index_path} contains duplicate country codes")
        for code in index.country_codes:
            if len(code) != 3 or not code.isascii() or not code.isalpha() or code != code.upper():
                raise ValueError(f"{self.index_path} contains invalid country code {code!r}")
        return index

    def _load_attribute(self, country_root: Path, name: str) -> Any:
        candidates = (name, *LEGACY_ATTRIBUTE_FALLBACKS.get(name, ()))
        for candidate in candidates:
            path = country_root / "attributes" / f"{candidate}.json"
            if not path.is_file():
                continue
            envelope = CountryAttribute.model_validate(_read_object(path))
            if envelope.schema_version != COUNTRY_ATTRIBUTE_SCHEMA:
                raise ValueError(f"{path} has unsupported schema_version {envelope.schema_version!r}")
            if candidate != name and name in COUNTRY_GAME_ATTRIBUTE_NAMES:
                return _coerce_rating(envelope.value, field_name=candidate)
            return envelope.value
        canonical = country_root / "attributes" / f"{name}.json"
        raise ValueError(f"{canonical} is missing and no supported legacy fallback exists")

    def load_country(self, code: str) -> Country:
        country_root = self.countries_root / code
        identity_path = country_root / "country.json"
        identity = CountryIdentity.model_validate(_read_object(identity_path))
        if identity.schema_version != COUNTRY_IDENTITY_SCHEMA:
            raise ValueError(f"{identity_path} has unsupported schema_version {identity.schema_version!r}")
        if identity.code != code:
            raise ValueError(f"{identity_path} code {identity.code!r} does not match directory {code!r}")
        attributes = {name: self._load_attribute(country_root, name) for name in ATTRIBUTE_NAMES}
        population_path = country_root / "attributes" / "population.json"
        population = CountryPopulation.model_validate(_read_object(population_path))
        if population.schema_version != COUNTRY_POPULATION_SCHEMA:
            raise ValueError(f"{population_path} has unsupported schema_version {population.schema_version!r}")
        if population.default_year not in population.values_by_year:
            raise ValueError(f"{population_path} default_year {population.default_year} is absent from values_by_year")
        default_population = population.values_by_year[population.default_year]
        return Country.model_validate({
            **identity.model_dump(exclude={"schema_version"}),
            **attributes,
            "population": default_population,
            "default_population": default_population,
            "default_population_year": population.default_year,
            "population_by_year": population.values_by_year,
        })

    def load_config(self) -> CountriesConfig:
        index = self.load_index()
        return CountriesConfig(dataset_status=index.dataset_status, countries=[self.load_country(code) for code in index.country_codes])

    def semantic_payload(self) -> list[dict[str, Any]]:
        return sorted((c.model_dump(mode="json") for c in self.load_config().countries), key=lambda c: c["code"])

    def write_country(self, country: Country) -> None:
        root = self.countries_root / country.code
        identity = {"schema_version": COUNTRY_IDENTITY_SCHEMA, **country.model_dump(mode="json", include={"code", "name", "flag_asset", "notes"})}
        _write_json_atomic(root / "country.json", identity)
        if country.population_by_year is not None:
            timeline = country.population_by_year
            default_year = country.default_population_year
        elif country.default_population_year is not None and country.default_population is not None:
            default_year = country.default_population_year
            timeline = {default_year: country.default_population}
        else:
            default_year = 2020
            timeline = {default_year: country.population}
        _write_json_atomic(root / "attributes" / "population.json", {
            "schema_version": COUNTRY_POPULATION_SCHEMA,
            "default_year": default_year,
            "values_by_year": {str(year): value for year, value in sorted(timeline.items())},
        })
        dumped = country.model_dump(mode="json")
        for name in ATTRIBUTE_NAMES:
            _write_json_atomic(
                root / "attributes" / f"{name}.json",
                {"schema_version": COUNTRY_ATTRIBUTE_SCHEMA, "value": dumped.get(name)},
            )
        # A direct write into an existing scratch directory should not leave a
        # mixed old/new country behind. Normal replace flows already stage fresh.
        for legacy_name in LEGACY_ATTRIBUTE_NAMES:
            (root / "attributes" / f"{legacy_name}.json").unlink(missing_ok=True)

    def create_country(self, country: Country) -> bytes:
        """Create one country and update the index, returning exact old index bytes."""
        index = self.load_index()
        live = self.countries_root / country.code
        if country.code in index.country_codes or live.exists():
            raise FileExistsError(f"country {country.code!r} already exists")
        original = self.index_path.read_bytes()
        stage = Path(tempfile.mkdtemp(prefix=f".{country.code}-create-", dir=self.countries_root))
        staged = WorldPackageCountryStore(stage)
        promoted = False
        try:
            staged.countries_root.mkdir()
            staged.write_country(country)
            if staged.load_country(country.code) != country:
                raise ValueError(f"staged country {country.code} did not round-trip")
            staged.countries_root.joinpath(country.code).rename(live)
            promoted = True
            _write_json_atomic(self.index_path, {
                "schema_version": index.schema_version, "dataset_status": index.dataset_status,
                "country_codes": sorted([*index.country_codes, country.code]),
            })
            self.load_config()
            return original
        except Exception:
            if promoted:
                shutil.rmtree(live, ignore_errors=True)
            self._restore_index(original)
            raise
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def rollback_create(self, code: str, original_index: bytes) -> None:
        shutil.rmtree(self.countries_root / code, ignore_errors=True)
        self._restore_index(original_index)

    def delete_country(self, code: str) -> tuple[bytes, Path]:
        """Stage deletion of one country. Caller must finalize or roll it back."""
        index = self.load_index()
        live = self.countries_root / code
        if code not in index.country_codes or not live.is_dir():
            raise FileNotFoundError(f"country {code!r} does not exist")
        original = self.index_path.read_bytes()
        backup = Path(tempfile.mkdtemp(prefix=f".{code}-delete-backup-", dir=self.countries_root))
        backup.rmdir()
        live.rename(backup)
        try:
            _write_json_atomic(self.index_path, {
                "schema_version": index.schema_version, "dataset_status": index.dataset_status,
                "country_codes": [item for item in index.country_codes if item != code],
            })
            self.load_config()
            return original, backup
        except Exception:
            self._restore_index(original)
            if backup.exists() and not live.exists():
                backup.rename(live)
            raise

    def rollback_delete(self, code: str, original_index: bytes, backup: Path) -> None:
        self._restore_index(original_index)
        live = self.countries_root / code
        if backup.exists() and not live.exists():
            backup.rename(live)

    @staticmethod
    def finalize_delete(backup: Path) -> None:
        shutil.rmtree(backup)

    def _restore_index(self, original: bytes) -> None:
        with tempfile.NamedTemporaryFile("wb", dir=self.index_path.parent, prefix=".index.json.", delete=False) as fh:
            fh.write(original)
            temporary = Path(fh.name)
        try:
            temporary.replace(self.index_path)
        finally:
            temporary.unlink(missing_ok=True)

    def replace_country(self, country: Country) -> None:
        """Atomically replace one indexed country, restoring the live copy on failure."""
        if country.code not in self.load_index().country_codes:
            raise ValueError(f"country {country.code!r} does not exist")
        live = self.countries_root / country.code
        stage = Path(tempfile.mkdtemp(prefix=f".{country.code}-stage-", dir=self.countries_root))
        backup = self.countries_root / f".{country.code}-backup"
        staged_store = WorldPackageCountryStore(stage)
        try:
            staged_store.countries_root.mkdir(parents=True)
            staged_store.write_country(country)
            reloaded = staged_store.load_country(country.code)
            if reloaded.code != country.code:
                raise ValueError(f"staged country {country.code} did not round-trip")
            if backup.exists():
                shutil.rmtree(backup)
            live.rename(backup)
            try:
                staged_store.countries_root.joinpath(country.code).rename(live)
            except Exception:
                if backup.exists() and not live.exists():
                    backup.rename(live)
                raise
            shutil.rmtree(backup)
        finally:
            shutil.rmtree(stage, ignore_errors=True)

    def replace_population(self, country_code: str, values_by_year: dict[int, int], default_year: int = 2020) -> bytes:
        """Atomically replace only population.json and return its original bytes."""
        code = country_code.upper()
        if code not in self.load_index().country_codes:
            raise ValueError(f"country {code!r} does not exist")
        payload = CountryPopulation(default_year=default_year, values_by_year=values_by_year)
        path = self.countries_root / code / "attributes" / "population.json"
        original = path.read_bytes()
        current = CountryPopulation.model_validate(_read_object(path))
        if current.model_dump() == payload.model_dump():
            return original
        _write_json_atomic(path, {
            "schema_version": COUNTRY_POPULATION_SCHEMA,
            "default_year": default_year,
            "values_by_year": {str(year): value for year, value in sorted(values_by_year.items())},
        })
        try:
            self.load_country(code)
        except Exception:
            self.restore_population(code, original)
            raise
        return original

    def restore_population(self, country_code: str, original: bytes) -> None:
        """Restore exact population bytes using an atomic promotion."""
        path = self.countries_root / country_code.upper() / "attributes" / "population.json"
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as fh:
            fh.write(original)
            temporary = Path(fh.name)
        temporary.replace(path)

    def replace_dataset(self, config: CountriesConfig) -> None:
        parent = self.countries_root.parent
        parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".countries-stage-", dir=parent))
        staged_store = WorldPackageCountryStore(stage.parent / stage.name)
        try:
            staged_store.countries_root.mkdir(parents=True)
            for country in sorted(config.countries, key=lambda c: c.code):
                staged_store.write_country(country)
            _write_json_atomic(staged_store.index_path, {
                "schema_version": COUNTRIES_INDEX_SCHEMA,
                "dataset_status": config.dataset_status,
                "country_codes": sorted(c.code for c in config.countries),
            })
            staged_store.load_config()
            backup = parent / ".countries-backup"
            if backup.exists():
                shutil.rmtree(backup)
            moved_live_dataset = False
            if self.countries_root.exists():
                self.countries_root.rename(backup)
                moved_live_dataset = True
            try:
                staged_store.countries_root.rename(self.countries_root)
            except Exception:
                if moved_live_dataset and backup.exists() and not self.countries_root.exists():
                    backup.rename(self.countries_root)
                raise
            if backup.exists():
                shutil.rmtree(backup)
        finally:
            shutil.rmtree(stage, ignore_errors=True)
