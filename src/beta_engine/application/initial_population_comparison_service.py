"""Player Lab Test Sessions over the production initial-pool generator, never Run state."""

from __future__ import annotations

import csv
import hashlib
import inspect
import io
import json
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select

from beta_engine.application.talent_calibration_service import (
    _percentile,
    _stats,
    _variability,
)
from beta_engine.application.world_package_run_adapter import (
    WORLD_COUNTRY_ENTITY_KIND,
    WORLD_PLAYER_IDENTITY_ENTITY_KIND,
    WorldPackageRunAdapter,
)
from beta_engine.domain.calendar.season_weeks import (
    completed_weeks_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.countries.population_resolver import (
    resolve_effective_population,
)
from beta_engine.domain.countries.rating_history import GAME_ATTRIBUTE_NAMES
from beta_engine.domain.players.initial_pool import (
    STAGE_AGE_RANGES,
    STAGE_WEIGHTS,
    GeneratedPlayerAttributes,
    InitialPlayerPoolGenerator,
    initial_pool_age_weights,
    initial_pool_birth_year_weights,
)
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import PlayerLabPopulationSessionModel
from beta_engine.infrastructure.world_config import PlayerIdentityConfig

SCHEMA_VERSION = "player_lab_initial_population_comparison.v1"
GENERATION_POLICY = "initial_pool_preopening_fifteen.v2"


class PopulationComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    world_ids: tuple[str, str] = ("fifa_earth", "atp_earth")
    season: str = "2000/2001"
    player_count: int = Field(default=1000, ge=1, le=2000, strict=True)
    seeds: tuple[Annotated[int, Field(strict=True, ge=0, le=2**32 - 1)], ...] = Field(
        default=(101, 202, 303, 404, 505), min_length=1, max_length=10
    )

    @field_validator("season")
    @classmethod
    def normalize_season(cls, value):
        parts = value.split("/")
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError("season must be YYYY/YYYY or YYYY/YY")
        year = int(parts[0])
        if not 2000 <= year <= 2049 or parts[1] not in (
            str(year + 1),
            f"{(year + 1) % 100:02d}",
        ):
            raise ValueError("supported initial seasons are 2000/01 through 2049/50")
        return f"{year}/{year + 1}"

    @model_validator(mode="after")
    def validate_experiment(self):
        if set(self.world_ids) != {"fifa_earth", "atp_earth"}:
            raise ValueError(
                "select FIFA Earth and ATP Earth once each; no FAX fallback"
            )
        if len(set(self.seeds)) != len(self.seeds) or any(
            type(seed) is not int or not 0 <= seed <= 2**32 - 1 for seed in self.seeds
        ):
            raise ValueError(
                "seeds must be distinct integers from 0 through 4294967295"
            )
        return self


def distribution(values: list[int]) -> dict:
    """Reuse the existing Lab quantiles; intervals are analytical bins, not talents."""
    result = asdict(_stats(values))
    result.update(
        count=len(values),
        missing_count=0,
        p95=_percentile(sorted(values), 0.95) if values else None,
        p99=_percentile(sorted(values), 0.99) if values else None,
        histogram=[
            {
                "lower": lo,
                "upper": min(lo + 9, 99),
                "count": sum(lo <= value <= min(lo + 9, 99) for value in values),
            }
            for lo in range(0, 100, 10)
        ],
    )
    return result


def summarize(players: list[dict], countries: list[dict]) -> dict:
    counts = Counter(player["country_code"] for player in players)
    n = len(players)
    metrics = {
        "age": distribution([p["age_at_generation"] for p in players]),
        "potential_ability": distribution([p["potential_ability"] for p in players]),
        "current_ability": distribution([p["current_ability"] for p in players]),
        **{
            name: distribution([p["attributes"][name] for p in players])
            for name in GeneratedPlayerAttributes.model_fields
        },
    }
    return {
        "player_count": n,
        "countries": [
            {
                "code": c["code"],
                "name": c["name"],
                "count": counts[c["code"]],
                "share": counts[c["code"]] / n if n else None,
            }
            for c in countries
        ],
        "metrics": metrics,
        "potential_tiers": {
            tier: sum(p["potential_tier"] == tier for p in players)
            for tier in ("S", "A", "B", "C", "D")
        },
        "tour_registration": {
            "before_entry": None,
            "after_entry": None,
            "reason": "Stored initial profiles have no authoritative Tour registration history; age and career stage cannot substitute for the first valid application.",
        },
    }


def engine_provenance() -> dict:
    root = Path(__file__).resolve().parents[3]
    source = root / "src"
    digest = hashlib.sha256()
    for path in sorted(source.rglob("*.py")):
        digest.update(path.relative_to(source).as_posix().encode())
        digest.update(path.read_bytes())
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        dirty = (
            subprocess.run(
                ["git", "diff", "--quiet", "HEAD", "--", "src"], cwd=root, check=False
            ).returncode
            != 0
        )
    except (OSError, subprocess.SubprocessError):
        commit, dirty = None, None
    return {
        "commit": commit,
        "source_fingerprint": digest.hexdigest(),
        "uncommitted_source": dirty,
    }


@dataclass
class InitialPopulationComparisonService:
    adapter: WorldPackageRunAdapter
    session_factory: object

    def list_sessions(self):
        with self.session_factory() as session:
            rows = session.scalars(
                select(PlayerLabPopulationSessionModel).order_by(
                    PlayerLabPopulationSessionModel.session_id
                )
            ).all()
            return [
                {
                    "session_id": row.session_id,
                    "request": self._decode(row)["request"],
                    "fingerprint": row.fingerprint,
                }
                for row in rows
            ]

    @staticmethod
    def _decode(row):
        try:
            data = json.loads(row.payload_json)
            if (
                data["session_id"] != row.session_id
                or data["schema_version"] != SCHEMA_VERSION
                or data["fingerprint"] != row.fingerprint
                or canonical_hash({k: v for k, v in data.items() if k != "fingerprint"})
                != row.fingerprint
            ):
                raise ValueError("Player Lab population session integrity mismatch")
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid saved Player Lab population session") from exc
        return data

    def load(self, session_id):
        with self.session_factory() as session:
            row = session.get(PlayerLabPopulationSessionModel, session_id)
            if row is None:
                raise KeyError("Player Lab population session not found")
            return self._decode(row)

    def run(self, request: PopulationComparisonRequest):
        started = perf_counter()
        engine = engine_provenance()
        # Existing source adapter produces independent typed in-memory input copies.
        documents = [self.adapter.build_document(world) for world in request.world_ids]
        for world, doc in zip(request.world_ids, documents, strict=True):
            if doc.package_id != world:
                raise ValueError("World identity differs from requested input")
        input_key = canonical_hash(
            {
                "schema": SCHEMA_VERSION,
                "request": request.model_dump(mode="json"),
                "engine_source": engine["source_fingerprint"],
                "sources": [doc.source_fingerprint for doc in documents],
            }
        )
        session_id = "player-population-" + input_key
        with self.session_factory() as session:
            existing = session.get(PlayerLabPopulationSessionModel, session_id)
            if existing is not None:
                return self._decode(existing), True
        sources, runs = [], []
        year = int(request.season[:4])
        birth_weights = initial_pool_birth_year_weights(year)
        for doc in documents:
            countries = [
                Country.model_validate(e.payload)
                for e in doc.entities
                if e.entity_kind == WORLD_COUNTRY_ENTITY_KIND
            ]
            identity = [
                PlayerIdentityConfig.model_validate(e.payload)
                for e in doc.entities
                if e.entity_kind == WORLD_PLAYER_IDENTITY_ENTITY_KIND
            ]
            if len(identity) != 1 or not countries:
                raise ValueError(
                    "World snapshot requires countries and exactly one production identity configuration"
                )
            country_rows = [{"code": c.code, "name": c.name} for c in countries]
            used_inputs = []
            for country in countries:
                years = []
                for requested_year in sorted({*birth_weights, year}):
                    rating_year = (
                        country.rating_history.resolve(requested_year)[0]
                        if country.rating_history
                        else None
                    )
                    effective = country.at_rating_year(requested_year)
                    population = resolve_effective_population(country, requested_year)
                    years.append(
                        {
                            "requested_year": requested_year,
                            "rating_source_year": rating_year,
                            "rating_fallback": rating_year != requested_year,
                            "ratings": {
                                name: getattr(effective, name)
                                for name in GAME_ATTRIBUTE_NAMES
                            },
                            "population": asdict(population),
                        }
                    )
                used_inputs.append(
                    {
                        "code": country.code,
                        "name": country.name,
                        "factual_configuration": country.model_dump(
                            mode="json", exclude={"rating_history"}
                        ),
                        "years": years,
                    }
                )
            sources.append(
                {
                    "world_id": doc.package_id,
                    "version": doc.provenance["source_world_version"],
                    "package_fingerprint": doc.provenance["source_world_fingerprint"],
                    "snapshot_fingerprint": doc.source_fingerprint,
                    "country_count": len(countries),
                    "identity_configuration": identity[0].model_dump(mode="json"),
                    "effective_country_inputs": used_inputs,
                }
            )
            generator = InitialPlayerPoolGenerator(identity_config=identity[0])
            for seed in request.seeds:
                run_started = perf_counter()
                result = generator.generate(
                    countries=countries,
                    season=request.season,
                    seed=seed,
                    target_pool_size=request.player_count,
                    dry_run=True,
                    existing_locked_players=[],
                )
                elapsed = perf_counter() - run_started
                position = season_week_to_calendar_position(year, 1)
                for player in result.players:
                    weeks = completed_weeks_at_calendar_position(
                        birth_year=player.birth_year,
                        birth_year_week=player.birth_year_week,
                        calendar_year=position.calendar_year,
                        year_week=position.year_week,
                    )
                    if weeks <= 15 * 61 or not 15 <= player.age_at_generation <= 45:
                        raise ValueError(
                            "Generated player is not fifteen before opening Week 1"
                        )
                if len(result.players) != request.player_count:
                    raise ValueError(
                        "Production generator returned an unexpected player count"
                    )
                players = [p.model_dump(mode="json") for p in result.players]
                runs.append(
                    {
                        "world_id": doc.package_id,
                        "seed": seed,
                        "duration_seconds": elapsed,
                        "gameplay_fingerprint": canonical_hash(players),
                        "generation_metadata": result.metadata.model_dump(mode="json"),
                        "summary": summarize(players, country_rows),
                        "players": players,
                    }
                )
        aggregate = []
        for source in sources:
            selected = [run for run in runs if run["world_id"] == source["world_id"]]
            pooled = [p for run in selected for p in run["players"]]
            summary = summarize(pooled, source["effective_country_inputs"])
            country_variability = {
                country["code"]: asdict(
                    _variability(
                        [
                            next(
                                c["count"]
                                for c in run["summary"]["countries"]
                                if c["code"] == country["code"]
                            )
                            for run in selected
                        ]
                    )
                )
                for country in summary["countries"]
            }
            aggregate.append(
                {
                    "world_id": source["world_id"],
                    "summary": summary,
                    "between_seed_countries": country_variability,
                    "between_seed_metrics": {
                        name: {
                            stat: asdict(
                                _variability(
                                    [
                                        run["summary"]["metrics"][name][stat]
                                        for run in selected
                                    ]
                                )
                            )
                            for stat in ("mean", "p50", "p99", "maximum")
                        }
                        for name in summary["metrics"]
                    },
                    "between_seed_tiers": {
                        tier: asdict(
                            _variability(
                                [
                                    run["summary"]["potential_tiers"][tier]
                                    for run in selected
                                ]
                            )
                        )
                        for tier in ("S", "A", "B", "C", "D")
                    },
                }
            )
        left, right = aggregate
        comparison = {
            "left_world": left["world_id"],
            "right_world": right["world_id"],
            "metric_deltas": {
                name: {
                    stat: right["summary"]["metrics"][name][stat]
                    - left["summary"]["metrics"][name][stat]
                    for stat in ("mean", "p50", "p99", "maximum")
                }
                for name in left["summary"]["metrics"]
            },
        }
        data = {
            "schema_version": SCHEMA_VERSION,
            "session_id": session_id,
            "request": request.model_dump(mode="json"),
            "engine": engine,
            "sources": sources,
            "runs": runs,
            "aggregates": aggregate,
            "comparison": comparison,
            "duration_seconds": perf_counter() - started,
            "effective_configuration": {
                "policy": GENERATION_POLICY,
                "stage_weights": STAGE_WEIGHTS,
                "stage_age_ranges": STAGE_AGE_RANGES,
                "birth_year_weights": birth_weights,
                "country_code": None,
                "region": None,
                "locked_players": [],
                "dry_run": True,
                "potential_model_source": inspect.getsource(
                    InitialPlayerPoolGenerator._potential
                ),
                "generator_source": inspect.getsource(InitialPlayerPoolGenerator),
                "country_model_source": inspect.getsource(CountryTalentModel),
                "population_resolver_source": inspect.getsource(
                    resolve_effective_population
                ),
                "age_weights": initial_pool_age_weights(),
            },
            "interpretation": {
                "rng": "v1 BLAKE2b child seed (seed, season scope, initial_pool, season, country code, sequence); World ID is absent. Shared country/sequence can share latent draws, but allocation/identity/environment differ; do not assume whole-population paired samples.",
                "country_counts": "Deterministic largest-remainder allocation; seed-independent. Allocation shares are model weights, not probabilities from repeated random sampling.",
                "history": "Country quantity uses birth-cohort historical population and ratings; current ability uses season-start development environment. Source years and fallbacks are recorded for every used year.",
                "expected_distribution": "No analytical potential expectation supplied here; pooled observed means are not theoretical probabilities.",
                "scope": "Initial population only; no annual intake, Run mutation, retirement simulation or realism validation.",
            },
        }
        data["fingerprint"] = canonical_hash(data)
        with self.session_factory.begin() as session:
            # A duplicate concurrent request must reuse the exact already saved session.
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            existing = session.get(PlayerLabPopulationSessionModel, session_id)
            if existing is not None:
                return self._decode(existing), True
            session.add(
                PlayerLabPopulationSessionModel(
                    session_id=session_id,
                    fingerprint=data["fingerprint"],
                    payload_json=json.dumps(data, ensure_ascii=False),
                )
            )
        return data, False

    @staticmethod
    def overview(data, *, cached=False):
        return {
            **{k: v for k, v in data.items() if k not in ("sources", "runs")},
            "cached": cached,
            "sources": [
                {k: v for k, v in source.items() if k != "effective_country_inputs"}
                for source in data["sources"]
            ],
            "runs": [
                {k: v for k, v in run.items() if k != "players"} for run in data["runs"]
            ],
        }

    def csv_export(self, session_id):
        data = self.load(session_id)
        output = io.StringIO()
        columns = [
            "session_id",
            "world_id",
            "seed",
            "engine_commit",
            "package_fingerprint",
            "gameplay_fingerprint",
            "player_id",
            "name",
            "country_code",
            "birth_year",
            "birth_year_week",
            "age_at_generation",
            "potential_ability",
            "potential_tier",
            "current_ability",
            *GeneratedPlayerAttributes.model_fields,
            "career_stage",
            "play_style",
            "archetype",
            "generation_seed",
            "hidden_career_traits",
        ]
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        for run in data["runs"]:
            source = next(
                s for s in data["sources"] if s["world_id"] == run["world_id"]
            )
            for player in run["players"]:
                row = {key: player.get(key) for key in columns if key in player}
                row.update(
                    session_id=session_id,
                    world_id=run["world_id"],
                    seed=run["seed"],
                    engine_commit=data["engine"]["commit"],
                    package_fingerprint=source["package_fingerprint"],
                    gameplay_fingerprint=run["gameplay_fingerprint"],
                    **player["attributes"],
                    hidden_career_traits=json.dumps(
                        player["hidden_career_traits"], sort_keys=True
                    ),
                )
                writer.writerow(row)
        return output.getvalue()
