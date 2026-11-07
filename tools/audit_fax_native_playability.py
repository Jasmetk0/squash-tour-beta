"""Read-only: identify concrete gaps between 80 copied FAX Calendar Editions
and the production configured native Tour's *supported* knockout executor.

The legacy v2 executor probe and canonical Q/Main source prerequisites are
separate. An 80-Edition calendar is NOT 80 playable or actually played Editions.
Do not generate replacement 4/8-player fixtures, qualify players silently,
fill missing Category point awards, write into the Run, or re-date SW1 events.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from beta_engine.application.pre_alpha_fax_acceptance_calendar_source import (
    PRE_ALPHA_FAX_ACCEPTANCE_EDITION_COUNT,
    PRE_ALPHA_FAX_ACCEPTANCE_SEASON,
    PreAlphaFaxAcceptanceCalendarSource,
)
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_category_points_service import (
    SeasonCategoryPointsService,
)
from beta_engine.application.tournament_templates_service import (
    TournamentTemplatesConfigService,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.points import is_valid_ranking_point
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarTourEdition,
    required_stages,
)
from beta_engine.domain.tournaments.fax_reference_bracket_topology import (
    build_fax_reference_bracket_topology,
)
from beta_engine.domain.tournaments.models import SeasonCalendarEvent

SCHEMA = "fax_native_playability_gap_audit.v1"
# This is the documented initial native Tour bootstrap checkpoint, not an
# implicit assertion about every Run; expose it as an explicit CLI parameter.
INITIAL_NATIVE_TOUR_WEEK = 2
NATIVE_MAIN_ONLY_SIZES = frozenset((4, 8))


def _native_probe(event: SeasonCalendarEvent, *, clock: RunCalendar) -> str | None:
    """Try the actual immutable native v2 domain constructor; no simulation."""
    size = event.main_draw_size
    stages = required_stages(size)
    table = event.ranking_points_table
    try:
        CalendarTourEdition(
            schema_version="calendar_tournament_edition.v2",
            edition_id=event.event_id,
            name=event.event_name,
            week=RunWeekPosition(calendar=clock, season_index=0, week=event.season_week),
            announcement_week=RunWeekPosition(
                calendar=clock, season_index=0, week=event.season_week - 1
            ),
            start_slot=1,
            simulation_seed=1,
            main_entrant_count=size,
            ranked=True,
            point_table={stage: table[stage] for stage in stages},
            validity_weeks=clock.weeks_per_year,
        )
    except (ValueError, KeyError, TypeError) as exc:
        return str(exc)[:240]
    return None


def classify_event(
    event: SeasonCalendarEvent,
    *,
    initial_native_week: int,
    clock: RunCalendar,
) -> dict[str, Any]:
    """Do not erase geometry/points/publication mismatches with a loose mapping.

    A native v2-compatible main draw is only a structural candidate; authentic
    Entry eligibility, 80 played matches, source-to-native ownership and the
    original FAX tournament semantics are NOT established by this tool.
    """
    if not 1 <= initial_native_week < clock.weeks_per_year:
        raise ValueError("Initial native Tour week must be within this Run")
    if event.season != PRE_ALPHA_FAX_ACCEPTANCE_SEASON:
        raise ValueError("This source audit requires the original 2000/2001 FAX season")
    if not 1 <= event.season_week <= clock.weeks_per_year:
        raise ValueError("FAX source has a week outside the exact Run calendar")

    blocked: list[str] = []
    if event.main_draw_size not in NATIVE_MAIN_ONLY_SIZES:
        blocked.append("main_field_not_supported_by_native_v2_executor")
    if event.qualification_draw_size or event.qualifier_spots:
        blocked.append("qualification_structure_not_modelled_by_native_v2")
    if event.wild_cards or event.byes:
        blocked.append("wild_card_bye_geometry_not_losslessly_mapped")
    if event.duration_in_season_weeks != 1:
        blocked.append("multiweek_edition_timing_not_losslessly_mapped")
    # At native W2, an Edition created now must announce on a *future*
    # Week Transition AND leave a complete announced week before operations.
    if event.season_week < initial_native_week + 2:
        blocked.append("announcement_not_future_from_native_bootstrap")
    if event.missing_required_point_stages:
        blocked.append("required_category_point_awards_missing")
    # The legacy FAX points authority has names round_of_16/32 while the
    # supported native knockout stages are round16/32; never invent a map.
    stages = required_stages(event.main_draw_size)
    if any(stage not in event.ranking_points_table for stage in stages):
        blocked.append("legacy_and_native_point_stages_need_explicit_mapping")
    if not blocked:
        domain_error = _native_probe(event, clock=clock)
        if domain_error:
            blocked.append("native_v2_domain_rejected_event")
    else:
        domain_error = None

    return {
        "event_id": event.event_id,
        "source_template_id": event.template_id,
        "source_season_week": event.season_week,
        "source_main_draw_size": event.main_draw_size,
        "source_qualification_draw_size": event.qualification_draw_size,
        "source_qualifier_spots": event.qualifier_spots,
        "source_wild_cards": event.wild_cards,
        "source_byes": event.byes,
        "source_duration_weeks": event.duration_in_season_weeks,
        "missing_required_category_stages": list(event.missing_required_point_stages),
        "native_v2_domain_error": domain_error,
        "blocker_codes": blocked,
        "structurally_compatible_only": not blocked,
    }


def _canonical_source_prerequisites(event: SeasonCalendarEvent) -> dict[str, Any]:
    """Read exact bracket and point inputs, without inferring an announcement."""
    topology = build_fax_reference_bracket_topology(event)
    ranked = event.ranking_status == "ranked"
    required = topology.ranked_point_stages if ranked else ()
    missing = [stage for stage in required if stage not in event.ranking_points_table]
    invalid = [
        stage for stage in required
        if stage in event.ranking_points_table
        and not is_valid_ranking_point(event.ranking_points_table[stage])
    ]
    # The first match sets only an upper bound. Entry, WC or Draw can require
    # an earlier announcement. SW1 has no preceding in-Run week at all.
    return {
        "expected_real_match_count": topology.actual_match_count_if_fully_played,
        "required_ranked_point_stages": list(required),
        "missing_ranked_point_stages": missing,
        "invalid_ranked_point_stages": invalid,
        "authored_ranked_point_values_complete": (
            not missing and not invalid and not event.ranking_configuration_legacy
        ) if ranked else None,
        "source_has_explicit_native_announcement": (
            event.event_level_overrides.get("native_announcement_week") is not None
        ),
        "latest_in_run_announcement_week_from_play_only": event.season_week - 1 or None,
    }


def audit(
    events: Sequence[SeasonCalendarEvent],
    *,
    source_fingerprint: str,
    initial_native_week: int = INITIAL_NATIVE_TOUR_WEEK,
    calendar: RunCalendar | None = None,
) -> dict[str, Any]:
    """Pure read-only audit on captured, versioned source Calendar objects."""
    clock = calendar or RunCalendar(61, 37, 2000, 50)
    if clock.weeks_per_year != 61 or clock.season_start_year_week != 37:
        raise ValueError("This exact FAX reference source requires W61 offset 37")
    if len(source_fingerprint) != 64 or any(c not in "0123456789abcdef" for c in source_fingerprint):
        raise ValueError("Expected exact 64-character canonical source fingerprint")
    if len(events) != PRE_ALPHA_FAX_ACCEPTANCE_EDITION_COUNT:
        raise ValueError("Only the original 80-Edition release reference can be audited")
    if len({event.event_id for event in events}) != len(events):
        raise ValueError("Duplicate FAX Edition identities must not be conflated")
    if any(event.tour_level != "WORLD_TOUR" or not event.is_world_tour
           or event.is_elite_tour for event in events):
        raise ValueError("Non-World-Tour input in the reference World Tour audit")

    rows = []
    for event in sorted(events, key=lambda item: (item.season_week, item.event_id)):
        row = classify_event(event, initial_native_week=initial_native_week, clock=clock)
        row["canonical_q_main_source_prerequisites"] = _canonical_source_prerequisites(event)
        rows.append(row)
    reasons = Counter(code for row in rows for code in row["blocker_codes"])
    categories = Counter(event.category for event in events)
    compatible = sum(row["structurally_compatible_only"] for row in rows)
    # This tool cannot certify playable/played Editions even if all structural
    # checks someday pass: production Entry source and match execution remain.
    return {
        "schema_version": SCHEMA,
        "source": "copied_fax_world_tour_release_fixture_not_sporting_canon",
        "source_calendar_fingerprint": source_fingerprint,
        "run_calendar": {
            "weeks_per_year": clock.weeks_per_year,
            "season_start_year_week": clock.season_start_year_week,
            "season_count": clock.season_count,
        },
        "initial_native_tour_week_assumption": initial_native_week,
        "source_edition_count": len(rows),
        "structurally_compatible_edition_count": compatible,
        "structurally_blocked_edition_count": len(rows) - compatible,
        "actually_played_edition_count_proven": 0,
        "playability_certified": False,
        "blocker_counts": dict(sorted(reasons.items())),
        "category_counts": dict(sorted(categories.items())),
        "editions": rows,
        "limitations": [
            "No Run/Branch was read or modified; this is the copied source calendar only.",
            "No Entry AI policy, qualification, Field, Draw, MatchEngine, Save or season execution was run.",
            "No 80-played-Edition or 50-season evidence is claimed.",
            "An event structurally accepted by native v2 is NOT a faithful FAX conversion.",
            "Native v3 group/hybrid formats are not a silent substitute for FAX knockout geometry.",
            "Missing qualification and main point awards are never filled with zero.",
        ],
    }


def build_current_source_report(
    *,
    templates_path: Path = Path("config/tournament_templates/mvp_templates.json"),
    category_registry_path: Path = Path("config/simulation/season_category_points.json"),
    initial_native_week: int = INITIAL_NATIVE_TOUR_WEEK,
) -> dict[str, Any]:
    """Resolve the real checked-in FAX 80 fixture and current points, without writes."""
    templates = TournamentTemplatesConfigService(config_path=templates_path)
    points = SeasonCategoryPointsService(
        templates, registry_path=category_registry_path,
    )
    source = PreAlphaFaxAcceptanceCalendarSource(
        template_service=templates,
        calendar_validation_service=SeasonCalendarService(
            template_service=templates, category_points_service=points,
        ),
    )
    calendar = source.build_calendar(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)
    if calendar.metadata is None or not calendar.metadata.build_fingerprint:
        raise ValueError("Versioned FAX calendar is missing canonical source fingerprint")
    return audit(
        calendar.events,
        source_fingerprint=calendar.metadata.build_fingerprint,
        initial_native_week=initial_native_week,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only FAX 80 Edition vs native Tour structural playability gate"
    )
    parser.add_argument("--templates", type=Path,
                        default=Path("config/tournament_templates/mvp_templates.json"))
    parser.add_argument("--category-points", type=Path,
                        default=Path("config/simulation/season_category_points.json"))
    parser.add_argument("--initial-native-week", type=int, default=2)
    parser.add_argument("--output", type=Path,
                        help="Write deterministic JSON report (never changes authoritative inputs)")
    args = parser.parse_args(argv)
    report = build_current_source_report(
        templates_path=args.templates,
        category_registry_path=args.category_points,
        initial_native_week=args.initial_native_week,
    )
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        # Intentionally no storage/config/API edits: operator chooses output.
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    print(
        f"FAX native audit: {report['structurally_blocked_edition_count']}"
        f"/{report['source_edition_count']} structurally blocked,"
        " ZERO actual matches executed.",
        file=__import__("sys").stderr,
    )
    return 2 if report["structurally_blocked_edition_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
