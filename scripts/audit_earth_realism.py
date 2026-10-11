"""Audit FIFA Earth and ATP Earth rating histories for calibration-review signals."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.application.earth_realism_audit import audit_earth_realism


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fifa",
        type=Path,
        default=Path("config/earth_research/fifa_earth.json"),
    )
    parser.add_argument(
        "--atp",
        type=Path,
        default=Path("config/earth_research/atp_earth.json"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--low-confidence-share", type=float, default=0.75)
    parser.add_argument("--large-annual-jump", type=float, default=1.5)
    parser.add_argument("--long-flat-run-years", type=int, default=12)
    args = parser.parse_args()

    if not 0 <= args.low_confidence_share <= 1:
        parser.error("--low-confidence-share must be between 0 and 1")
    if args.large_annual_jump <= 0:
        parser.error("--large-annual-jump must be positive")
    if args.long_flat_run_years < 2:
        parser.error("--long-flat-run-years must be at least 2")

    fifa = load_earth_research_bundle(args.fifa).research
    atp = load_earth_research_bundle(args.atp).research
    report = audit_earth_realism(
        fifa_countries=fifa.countries,
        atp_countries=atp.countries,
        low_confidence_share=args.low_confidence_share,
        large_annual_jump=args.large_annual_jump,
        long_flat_run_years=args.long_flat_run_years,
    )
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
