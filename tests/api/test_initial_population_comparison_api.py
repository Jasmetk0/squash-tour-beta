"""Small real HTTP / generator / SQLite regression; synthetic source fixtures only."""

import csv
import hashlib
import io
import json
import statistics
import threading
from urllib.request import urlopen

import pytest
import uvicorn
from pydantic import ValidationError
from starlette.requests import Request
from test_simulation_api import ApiServer, _free_port, _request

from beta_engine.api.deps import get_world_package_run_adapter
from beta_engine.application.initial_population_comparison_service import (
    PopulationComparisonRequest,
)
from beta_engine.domain.countries import CountriesConfig, Country
from beta_engine.domain.countries.rating_history import (
    GAME_ATTRIBUTE_NAMES,
    CountryRatingHistory,
)
from beta_engine.domain.players.initial_pool import InitialPlayerPoolGenerator
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import PlayerLabPopulationSessionModel
from beta_engine.infrastructure.world_config import PlayerIdentityConfig
from beta_engine.main import create_app
from tests.support.world_packages import materialize_test_world_package

pytestmark = pytest.mark.pr_critical
ROOT = "/admin/labs/player/population-comparisons"


def tree_hash(root):
    return hashlib.sha256(
        b"".join(
            p.relative_to(root).as_posix().encode() + p.read_bytes()
            for p in sorted(root.rglob("*"))
            if p.is_file()
        )
    ).hexdigest()


def write_sources(root):
    for world, label, rating in (("fifa_earth", "Fifa", 2), ("atp_earth", "Atp", 8)):
        history = CountryRatingHistory.model_validate(
            {
                "reference_year": 2026,
                "data_cutoff": "2026-10-03",
                "years": {
                    year: {
                        "historical_entity": "TEST",
                        "territory_mapping_note": "Synthetic test",
                        "ratings": {
                            name: {
                                "value": value,
                                "method": "sourced_estimate",
                                "confidence": "low",
                                "source_ids": ["test"],
                                "observation_ids": ["fixture#one"],
                                "rationale": "Synthetic regression",
                                "anchor_years": [year],
                            }
                            for name in GAME_ATTRIBUTE_NAMES
                        },
                    }
                    for year, value in ((1955, 1), (2000, rating), (2026, 9))
                },
            }
        )
        countries = [
            Country(
                code=f"X{chr(65 + i // 26)}{chr(65 + i % 26)}",
                name=f"Test {i}",
                region="TEST",
                population=1_000_000 + i * 1000,
                default_population_year=2020,
                default_population=1_000_000 + i * 1000,
                population_by_year={
                    1955: 500_000 + i * 1000,
                    2000: 900_000 + i * 1000,
                    2020: 1_000_000 + i * 1000,
                },
                rating_scale="country_ratings_1_10.v2",
                rating_history=history,
                **{name: 9 for name in GAME_ATTRIBUTE_NAMES},
            )
            for i in range(64)
        ]
        path = materialize_test_world_package(
            root, CountriesConfig(countries=countries), world_id=world
        )
        meta = json.loads((path / "world.json").read_text())
        meta.update(type="official", source="built_in")
        (path / "world.json").write_text(json.dumps(meta))
        (path / "generation").mkdir()
        (path / "generation/player_identity.json").write_text(
            json.dumps(
                {
                    "given_names": [label],
                    "family_names": ["Fixture"],
                    "play_styles": ["attacking"],
                    "archetypes": ["explosive shotmaker"],
                    "growth_curves": ["balanced"],
                }
            )
        )


class PopulationServer(ApiServer):
    def __init__(self, database_url, worlds):
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.app = create_app(
            database_url=database_url, world_packages_root=str(worlds)
        )
        self.server = uvicorn.Server(
            uvicorn.Config(
                self.app, host="127.0.0.1", port=self.port, log_level="error"
            )
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)


def test_real_comparison_export_replay_restart_and_integrity(tmp_path, monkeypatch):
    worlds = tmp_path / "worlds"
    write_sources(worlds)
    before = tree_hash(worlds)
    db = f"sqlite:///{tmp_path / 'populations.sqlite'}"
    payload = {
        "world_ids": ["fifa_earth", "atp_earth"],
        "season": "2000/01",
        "player_count": 32,
        "seeds": [101, 202],
    }
    with PopulationServer(db, worlds) as server:
        status, overview = _request("POST", server.base_url + ROOT, payload)
        assert status == 201, overview
        session_id = overview["session_id"]
        endpoint = server.base_url + ROOT + "/" + session_id
        status, exported = _request("GET", endpoint + "/export")
        assert status == 200
        assert len(exported["runs"]) == 4
        assert {s["world_id"] for s in exported["sources"]} == {
            "fifa_earth",
            "atp_earth",
        }
        for source in exported["sources"]:
            years = source["effective_country_inputs"][0]["years"]
            assert (
                next(y for y in years if y["requested_year"] == 2000)[
                    "rating_source_year"
                ]
                == 2000
            )
            assert (
                next(y for y in years if y["requested_year"] == 1954)["population"][
                    "source_year"
                ]
                == 1955
            )
            assert all(y["rating_source_year"] != 2026 for y in years)
        for run in exported["runs"]:
            players, summary = run["players"], run["summary"]
            assert len(players) == summary["player_count"] == 32
            assert sum(c["count"] for c in summary["countries"]) == 32
            assert len(summary["countries"]) == 64
            assert any(c["count"] == 0 for c in summary["countries"])
            assert summary["tour_registration"]["before_entry"] is None
            assert all(
                p["name"].startswith(
                    "Fifa" if run["world_id"] == "fifa_earth" else "Atp"
                )
                for p in players
            )
            for metric, stats in summary["metrics"].items():
                values = [
                    p["age_at_generation"]
                    if metric == "age"
                    else p[metric]
                    if metric in p
                    else p["attributes"][metric]
                    for p in players
                ]
                assert stats["mean"] == statistics.mean(values)
                assert stats["p50"] == statistics.median(values)
                assert sum(bin["count"] for bin in stats["histogram"]) == 32
            status, raw = _request(
                "GET", endpoint + f"/players/{run['world_id']}/{run['seed']}"
            )
            assert status == 200 and raw["players"] == players
        with urlopen(endpoint + "/export?format=csv") as response:
            rows = list(csv.DictReader(io.StringIO(response.read().decode())))
        assert len(rows) == 128
        assert sum(int(row["potential_ability"]) for row in rows) == sum(
            p["potential_ability"] for r in exported["runs"] for p in r["players"]
        )
        assert _request("GET", endpoint + "/players/official_fax_world/101")[0] == 404
        assert _request("GET", endpoint + "/export?format=invalid")[0] == 422
        # Real regeneration independently replays the first gameplay fingerprint.
        first = exported["runs"][0]
        document = get_world_package_run_adapter(
            Request({"type": "http", "app": server.app})
        ).build_document(first["world_id"])
        replay = InitialPlayerPoolGenerator(
            identity_config=PlayerIdentityConfig.model_validate(
                next(
                    e.payload
                    for e in document.entities
                    if e.entity_kind == "world.player_identity.v1"
                )
            )
        ).generate(
            countries=[
                Country.model_validate(e.payload)
                for e in document.entities
                if e.entity_kind == "world.country.v1"
            ],
            season="2000/2001",
            seed=101,
            target_pool_size=32,
        )
        assert (
            canonical_hash([p.model_dump(mode="json") for p in replay.players])
            == first["gameplay_fingerprint"]
        )

        def forbidden(*args, **kwargs):
            raise AssertionError(
                "Saved reads and identical input must not generate again"
            )

        monkeypatch.setattr(InitialPlayerPoolGenerator, "generate", forbidden)
        status, cached = _request("POST", server.base_url + ROOT, payload)
        assert status == 201 and cached["cached"] is True
        assert cached["fingerprint"] == overview["fingerprint"]
        assert _request("GET", server.base_url + "/run-containers")[1] == {
            "run_containers": []
        }
    with PopulationServer(db, worlds) as restarted:
        endpoint = restarted.base_url + ROOT + "/" + session_id
        assert _request("GET", endpoint)[1]["fingerprint"] == overview["fingerprint"]
        assert _request("GET", endpoint + "/export")[1] == exported
        with restarted.app.state.runtime.repository._session_factory.begin() as session:
            row = session.get(PlayerLabPopulationSessionModel, session_id)
            broken = json.loads(row.payload_json)
            broken["fingerprint"] = "0" * 64
            row.payload_json = json.dumps(broken)
        assert _request("GET", endpoint)[0] == 409
        assert _request("GET", restarted.base_url + ROOT)[0] == 409
    assert tree_hash(worlds) == before


@pytest.mark.parametrize(
    "updates",
    [
        {"seeds": [True]},
        {"seeds": [1.0]},
        {"seeds": [101, 101]},
        {"seeds": []},
        {"world_ids": ["fifa_earth", "fifa_earth"]},
        {"world_ids": ["official_fax_world", "atp_earth"]},
        {"season": "1999/00"},
        {"season": "2000/02"},
        {"player_count": True},
    ],
)
def test_invalid_experiment_inputs_fail_closed(updates):
    with pytest.raises(ValidationError):
        PopulationComparisonRequest.model_validate(updates)
