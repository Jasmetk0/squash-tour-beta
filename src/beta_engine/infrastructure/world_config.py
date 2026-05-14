"""Loaders for world data configs used by generation pipelines."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from beta_engine.domain.countries.models import CountriesConfig
    from beta_engine.domain.players import ManualPlayerOverridesRegistry


class PlayerIdentityConfig(BaseModel):
    given_names: list[str] = Field(min_length=1)
    family_names: list[str] = Field(min_length=1)
    play_styles: list[str] = Field(min_length=1)
    archetypes: list[str] = Field(min_length=1)
    growth_curves: list[str] = Field(min_length=1)



MANUAL_PLAYER_OVERRIDE_TABULAR_FIELDS = (
    "override_id",
    "season",
    "country_code",
    "player_name",
    "player_slug",
    "player_id",
    "age",
    "profile_tier",
    "quality_band_override",
    "is_exceptional",
    "enabled",
    "notes",
    "attribute_technique",
    "attribute_movement",
    "attribute_physical",
    "attribute_mental",
    "attribute_consistency",
    "attribute_clutch",
    "attribute_recovery",
    "trait_potential_ceiling",
    "trait_growth_curve",
    "trait_professionalism",
    "trait_ambition",
    "trait_travel_tolerance",
    "trait_schedule_aggression",
    "trait_injury_proneness",
    "trait_resilience",
)

COUNTRY_TABULAR_FIELDS = (
    "code",
    "name",
    "flag_asset",
    "region",
    "population",
    "wealth_support",
    "squash_popularity",
    "squash_tradition",
    "system_quality",
)

COUNTRY_OPTIONAL_TABULAR_FIELDS = (
    "competition_density",
    "federation_quality",
    "court_count",
)

COUNTRY_EXPORT_TABULAR_FIELDS = (*COUNTRY_TABULAR_FIELDS, *COUNTRY_OPTIONAL_TABULAR_FIELDS)


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path: str | Path, payload: dict) -> None:
    with Path(path).open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def load_countries_config(path: str | Path = "config/world/countries.json") -> "CountriesConfig":
    from beta_engine.domain.countries.models import CountriesConfig

    return CountriesConfig.model_validate(_load_json(path))


def load_player_identity_config(
    path: str | Path = "config/world/player_identity.json",
) -> PlayerIdentityConfig:
    return PlayerIdentityConfig.model_validate(_load_json(path))


def load_manual_player_overrides_config(
    path: str | Path = "config/world/manual_player_overrides.json",
) -> "ManualPlayerOverridesRegistry":
    from beta_engine.domain.players import ManualPlayerOverridesRegistry

    return ManualPlayerOverridesRegistry.model_validate(_load_json(path))


def export_countries_to_csv(
    *,
    json_path: str | Path = "config/world/countries.json",
    csv_path: str | Path = "config/world/countries.seed.demo.csv",
) -> Path:
    countries_config = load_countries_config(json_path)
    target = Path(csv_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COUNTRY_EXPORT_TABULAR_FIELDS)
        writer.writeheader()
        for country in countries_config.countries:
            writer.writerow(
                {
                    "code": country.code,
                    "name": country.name,
                    "flag_asset": country.flag_asset or "",
                    "region": country.region,
                    "population": country.population,
                    "wealth_support": country.wealth_support,
                    "squash_popularity": country.squash_popularity,
                    "squash_tradition": country.squash_tradition,
                    "system_quality": country.system_quality,
                    "competition_density": country.competition_density,
                    "federation_quality": country.federation_quality,
                    "court_count": country.court_count if country.court_count is not None else "",
                }
            )
    return target


def import_countries_from_csv(
    *,
    csv_path: str | Path,
    json_path: str | Path = "config/world/countries.json",
) -> "CountriesConfig":
    from beta_engine.domain.countries.models import CountriesConfig

    source = Path(csv_path)
    with source.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [field for field in COUNTRY_TABULAR_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"countries csv is missing required columns: {', '.join(missing)}")

        countries: list[dict[str, object]] = []
        for row in reader:
            country_payload: dict[str, object] = {
                "code": row["code"],
                "name": row["name"],
                "flag_asset": row["flag_asset"] or None,
                "region": row["region"],
                "population": int(row["population"]),
                "wealth_support": int(row["wealth_support"]),
                "squash_popularity": int(row["squash_popularity"]),
                "squash_tradition": int(row["squash_tradition"]),
                "system_quality": int(row["system_quality"]),
            }
            for optional_float_field in ("competition_density", "federation_quality"):
                raw_optional = (row.get(optional_float_field) or "").strip()
                if raw_optional:
                    country_payload[optional_float_field] = float(raw_optional)
            raw_court_count = (row.get("court_count") or "").strip()
            if raw_court_count:
                country_payload["court_count"] = int(raw_court_count)
            countries.append(country_payload)

    countries_config = CountriesConfig.model_validate({"countries": countries})
    _write_json(json_path, countries_config.model_dump(mode="json"))
    return countries_config
