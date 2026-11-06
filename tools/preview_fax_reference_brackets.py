"""Read-only preview of the 80 real FAX fixture's Main and Q bracket geometry.

This never mutates points files, Run/Branch, entrants, match logs or the
reference World/Calendar. Its JSON is NOT a playable/simulated season.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from beta_engine.application.pre_alpha_fax_acceptance_calendar_source import (
    PRE_ALPHA_FAX_ACCEPTANCE_SEASON,
    PreAlphaFaxAcceptanceCalendarSource,
)
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_category_points_service import SeasonCategoryPointsService
from beta_engine.application.tournament_templates_service import TournamentTemplatesConfigService
from beta_engine.domain.tournaments.fax_reference_bracket_topology import (
    summarise_fax_reference_geometries,
)


def build_report(
    *,
    templates_path: Path = Path("config/tournament_templates/mvp_templates.json"),
    points_registry_path: Path = Path("config/simulation/season_category_points.json"),
) -> dict:
    templates = TournamentTemplatesConfigService(config_path=templates_path)
    points = SeasonCategoryPointsService(templates, registry_path=points_registry_path)
    source = PreAlphaFaxAcceptanceCalendarSource(
        template_service=templates,
        calendar_validation_service=SeasonCalendarService(
            template_service=templates, category_points_service=points,
        ),
    )
    original = source.build_calendar(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)
    result = summarise_fax_reference_geometries(original.events)
    if original.metadata is None or (
        result["source_calendar_fingerprint"] != original.metadata.build_fingerprint
    ):
        raise ValueError("Unbound FAX Calendar source")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview original 80 FAX Main/Qualification bracket geometry without simulation"
    )
    parser.add_argument("--templates", type=Path,
                        default=Path("config/tournament_templates/mvp_templates.json"))
    parser.add_argument("--category-points", type=Path,
                        default=Path("config/simulation/season_category_points.json"))
    parser.add_argument("--output", type=Path, help="Only explicit write is JSON report")
    args = parser.parse_args(argv)
    report = build_report(
        templates_path=args.templates,
        points_registry_path=args.category_points,
    )
    encoded = json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.write_text(encoded, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
