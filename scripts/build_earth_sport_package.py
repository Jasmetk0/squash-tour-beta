"""Audit Earth research, or build a complete source package (never overwrite one)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from beta_engine.application.earth_package_builder import audit_earth_research, build_earth_package, load_earth_research_bundle
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("research", type=Path)
    parser.add_argument("--base", type=Path, default=Path("config/world_packages/real_world"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    bundle = load_earth_research_bundle(args.research)
    research = bundle.research
    report = audit_earth_research(research, WorldPackageCountryStore(args.base).load_config().countries)
    print(json.dumps(report, indent=2))
    if args.output:
        build_earth_package(base_package=args.base, bundle=bundle, output=args.output)


if __name__ == "__main__":
    main()
