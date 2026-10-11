"""Measured production initial-pool comparison, separate from the small CI regression.

Run from the repository root. Raw exports and disposable SQLite stay in work/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from beta_engine.application.initial_population_comparison_service import (
    InitialPopulationComparisonService,
    PopulationComparisonRequest,
)
from beta_engine.application.world_package_registry_service import (
    WorldPackageRegistryService,
)
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.infrastructure.db import (
    DatabaseSettings,
    SimulationPersistenceRepository,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.main import create_app


def source_tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def isolated_app(root: Path, worlds: Path):
    """All mutable stores are disposable; built-in sources are read-only inputs."""
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        name: str(root / f"{name}.json")
        for name in (
            "countries_config_path",
            "manual_player_overrides_config_path",
            "tournament_templates_config_path",
            "initial_player_pool_config_path",
            "season_active_players_config_path",
            "season_calendar_registry_path",
            "season_category_points_registry_path",
            "planning_season_calendar_registry_path",
            "calendar_templates_registry_path",
            "season_builder_apply_audit_log_path",
            "planning_calendar_apply_audit_log_path",
            "season_entry_lists_registry_path",
            "season_draws_registry_path",
            "season_matches_registry_path",
            "season_event_results_registry_path",
            "season_point_awards_registry_path",
            "season_ranking_snapshots_registry_path",
            "points_config_path",
            "entry_tuning_config_path",
        )
    }
    return create_app(
        database_url=f"sqlite:///{root / 'populations.sqlite'}",
        world_packages_root=str(worlds),
        calendar_config_dir=str(root / "legacy"),
        planning_calendar_apply_backup_dir=str(root / "backups"),
        **paths,
    )


def measure(root: Path, worlds: Path, request: PopulationComparisonRequest):
    root.mkdir(parents=True, exist_ok=True)
    before = {world: source_tree_hash(worlds / world) for world in request.world_ids}
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{root / 'populations.sqlite'}")
    )
    factory = create_session_factory(engine)
    repository = SimulationPersistenceRepository(engine=engine, session_factory=factory)
    repository.bootstrap_schema()
    service = InitialPopulationComparisonService(
        WorldPackageRunAdapter(WorldPackageRegistryService(world_packages_root=worlds)),
        factory,
    )
    data, cached = service.run(request)
    assert before == {
        world: source_tree_hash(worlds / world) for world in request.world_ids
    }
    (root / f"{data['session_id']}.json").write_text(
        json.dumps(data, ensure_ascii=False)
    )
    (root / f"{data['session_id']}.csv").write_text(
        service.csv_export(data["session_id"])
    )
    evidence = {
        "session_id": data["session_id"],
        "fingerprint": data["fingerprint"],
        "cached": cached,
        "engine": data["engine"],
        "sources": [
            {k: v for k, v in source.items() if k != "effective_country_inputs"}
            for source in data["sources"]
        ],
        "source_tree_hashes_unchanged": before,
        "request": data["request"],
        "duration_seconds": data["duration_seconds"],
        "runs": [
            {
                k: v
                for k, v in run.items()
                if k not in ("players", "generation_metadata")
            }
            for run in data["runs"]
        ],
        "aggregates": data["aggregates"],
        "comparison": data["comparison"],
    }
    (root / "measured-summary.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2)
    )
    print(
        json.dumps(
            {
                "session_id": data["session_id"],
                "cached": cached,
                "seconds": data["duration_seconds"],
                "runs": [
                    {
                        "world": run["world_id"],
                        "seed": run["seed"],
                        "players": len(run["players"]),
                        "seconds": run["duration_seconds"],
                    }
                    for run in data["runs"]
                ],
            },
            indent=2,
        ),
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("work/earth-population/production")
    )
    parser.add_argument("--worlds", type=Path, default=Path("config/world_packages"))
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--players", type=int, default=1000)
    parser.add_argument(
        "--seeds", type=int, nargs="+", default=[101, 202, 303, 404, 505]
    )
    parser.add_argument("--season", default="2000/01")
    args = parser.parse_args()
    root, worlds = args.root.resolve(), args.worlds.resolve()
    if args.serve:
        import uvicorn

        uvicorn.run(isolated_app(root, worlds), host="127.0.0.1", port=args.port)
    else:
        measure(
            root,
            worlds,
            PopulationComparisonRequest(
                season=args.season, player_count=args.players, seeds=tuple(args.seeds)
            ),
        )


if __name__ == "__main__":
    main()
