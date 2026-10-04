"""Extract factual structural features from canonical FIFA structural evidence.

This script produces audit features only. It does not convert milestones into
quality scores or canonical country ratings. Held-out validation countries remain
explicitly excluded from model fitting.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.build_fifa_country_evidence_index import build_index
from scripts.reconcile_fifa_big_count_identities import DEFAULT_EARTH_ROOT

FEATURE_YEAR = 2026

PATHWAY_TYPES = {
    "academy_foundation",
    "academy_milestone",
    "development_pathway_launch",
    "development_framework_launch",
}
TRAINING_CENTRE_TYPES = {
    "training_centre_opening",
    "training_centre_milestone",
}
INFRASTRUCTURE_TYPES = {
    "infrastructure_milestone",
    "infrastructure_project_start",
}
PROGRAMME_OR_STRATEGY_TYPES = {
    "grassroots_programme_launch",
    "development_programme_launch",
    "development_programme_milestone",
    "development_strategy_launch",
    "development_framework_launch",
    "infrastructure_project_start",
}
NEGATIVE_BREAK_TYPES = {
    "competition_discontinuity",
    "governance_discontinuity",
}
TRANSITION_TYPES = {
    "governance_transition",
    "international_reintegration",
}
PROVISIONAL_FLAGS = {
    "programme_launch_not_outcome",
    "strategy_launch_not_outcome",
    "regulatory_framework_not_outcome",
    "project_start_not_completed_outcome",
    "programme_event_not_outcome",
    "partial_2026_evidence",
}


def _event_type(event: dict[str, Any]) -> str:
    event_type = event.get("comparability_group")
    if not isinstance(event_type, str) or not event_type:
        raise ValueError(
            f"structural event {event['observation_id']!r} lacks event type"
        )
    return event_type


def _years(events: list[dict[str, Any]]) -> list[int]:
    return sorted(
        int(event["observation_year"])
        for event in events
        if event["observation_year"] is not None
    )


def _first_year(events: list[dict[str, Any]], allowed_types: set[str]) -> int | None:
    years = [
        int(event["observation_year"])
        for event in events
        if event["observation_year"] is not None
        and _event_type(event) in allowed_types
    ]
    return min(years) if years else None


def _years_for_types(
    events: list[dict[str, Any]], allowed_types: set[str]
) -> list[int]:
    return sorted(
        int(event["observation_year"])
        for event in events
        if event["observation_year"] is not None
        and _event_type(event) in allowed_types
    )


def _dimension_events(
    structural: list[dict[str, Any]],
    dimension: str,
) -> list[dict[str, Any]]:
    return sorted(
        [
            event
            for event in structural
            if f"supports_{dimension}" in event["quality_flags"]
        ],
        key=lambda event: (
            event["observation_year"]
            if event["observation_year"] is not None
            else 9999,
            event["observation_id"],
        ),
    )


def _validation_role(structural: list[dict[str, Any]]) -> str:
    if any(
        "held_out_validation_country" in event["quality_flags"]
        for event in structural
    ):
        if any(
            "held_out_validation_country" not in event["quality_flags"]
            for event in structural
        ):
            raise ValueError("country mixes review and held-out structural evidence")
        return "held_out_validation"
    return "review" if structural else "none"


def _conflict_groups(events: list[dict[str, Any]]) -> list[str]:
    prefix = "conflict_group:"
    return sorted(
        {
            flag[len(prefix) :]
            for event in events
            for flag in event["quality_flags"]
            if flag.startswith(prefix)
        }
    )


def build_features(
    *,
    earth_root: Path = DEFAULT_EARTH_ROOT,
) -> dict[str, Any]:
    evidence = build_index()
    earth_index = json.loads((earth_root / "index.json").read_text(encoding="utf-8"))
    earth_codes = sorted(earth_index["country_codes"])

    countries: dict[str, Any] = {}
    role_counts = {"review": 0, "held_out_validation": 0, "none": 0}

    for code in earth_codes:
        structural = sorted(
            [
                fact
                for fact in evidence["countries"].get(code, [])
                if fact["measurement_type"] == "football_structural_event"
            ],
            key=lambda event: (
                event["observation_year"]
                if event["observation_year"] is not None
                else 9999,
                event["observation_id"],
            ),
        )
        role = _validation_role(structural)
        role_counts[role] += 1

        tradition = _dimension_events(structural, "squash_tradition")
        development = _dimension_events(structural, "development_quality")
        elite = _dimension_events(structural, "elite_support")
        competition = _dimension_events(structural, "competition_quality")

        tradition_years = _years(tradition)
        development_years = _years(development)
        elite_years = _years(elite)
        competition_years = _years(competition)

        earliest_tradition = min(tradition_years) if tradition_years else None
        latest_development = max(development_years) if development_years else None

        provisional_development = sorted(
            int(event["observation_year"])
            for event in development
            if event["observation_year"] is not None
            and any(flag in PROVISIONAL_FLAGS for flag in event["quality_flags"])
        )

        countries[code] = {
            "validation_role": role,
            "fit_allowed": role == "review",
            "rating_ready": False,
            "structural_event_count": len(structural),
            "structural_observation_ids": [
                event["observation_id"] for event in structural
            ],
            "conflict_groups": _conflict_groups(structural),
            "tradition": {
                "evidence_present": bool(tradition),
                "earliest_event_year": earliest_tradition,
                "latest_event_year": max(tradition_years)
                if tradition_years
                else None,
                "evidence_span_years_to_2026": (
                    FEATURE_YEAR - earliest_tradition
                    if earliest_tradition is not None
                    else None
                ),
                "pre_1955_evidence_present": any(
                    year < 1955 for year in tradition_years
                ),
                "pre_1955_event_count": sum(
                    year < 1955 for year in tradition_years
                ),
                "institutional_foundation_year": _first_year(
                    tradition, {"institutional_foundation"}
                ),
                "first_competition_year": _first_year(
                    tradition, {"competition_launch"}
                ),
                "first_club_year": _first_year(
                    tradition, {"club_foundation_milestone"}
                ),
                "transition_years": _years_for_types(
                    tradition, TRANSITION_TYPES
                ),
                "observation_ids": [
                    event["observation_id"] for event in tradition
                ],
            },
            "development": {
                "evidence_present": bool(development),
                "first_event_year": min(development_years)
                if development_years
                else None,
                "latest_event_year": latest_development,
                "years_since_latest_evidence": (
                    FEATURE_YEAR - latest_development
                    if latest_development is not None
                    else None
                ),
                "first_pathway_or_academy_year": _first_year(
                    development, PATHWAY_TYPES
                ),
                "first_training_centre_year": _first_year(
                    development, TRAINING_CENTRE_TYPES
                ),
                "first_infrastructure_year": _first_year(
                    development, INFRASTRUCTURE_TYPES
                ),
                "programme_or_strategy_years": _years_for_types(
                    development, PROGRAMME_OR_STRATEGY_TYPES
                ),
                "provisional_not_outcome_years": provisional_development,
                "event_types": sorted({_event_type(event) for event in development}),
                "observation_ids": [
                    event["observation_id"] for event in development
                ],
            },
            "elite_support_context": {
                "evidence_present": bool(elite),
                "first_event_year": min(elite_years) if elite_years else None,
                "latest_event_year": max(elite_years) if elite_years else None,
                "training_centre_years": _years_for_types(
                    elite, TRAINING_CENTRE_TYPES
                ),
                "negative_break_years": _years_for_types(
                    elite, NEGATIVE_BREAK_TYPES
                ),
                "transition_years": _years_for_types(elite, TRANSITION_TYPES),
                "observation_ids": [
                    event["observation_id"] for event in elite
                ],
            },
            "competition_context": {
                "evidence_present": bool(competition),
                "first_event_year": min(competition_years)
                if competition_years
                else None,
                "latest_event_year": max(competition_years)
                if competition_years
                else None,
                "competition_launch_years": _years_for_types(
                    competition, {"competition_launch"}
                ),
                "negative_break_years": _years_for_types(
                    competition, NEGATIVE_BREAK_TYPES
                ),
                "transition_years": _years_for_types(
                    competition, TRANSITION_TYPES
                ),
                "observation_ids": [
                    event["observation_id"] for event in competition
                ],
            },
        }

    return {
        "schema_version": "fifa_structural_features.v1",
        "world_id": "fifa_earth",
        "feature_year": FEATURE_YEAR,
        "rating_ready": False,
        "country_count": len(countries),
        "validation_role_counts": role_counts,
        "countries": countries,
        "limitations": [
            "Structural features describe dated evidence, not country quality scores.",
            "Held-out validation countries have fit_allowed=false.",
            "Absence of curated evidence means unknown, not zero capability.",
            "Feature recency does not imply causal effect size.",
            "Conflicting source dates remain explicit and block automatic timing assumptions.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--earth-root", type=Path, default=DEFAULT_EARTH_ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_features(earth_root=args.earth_root)
    print(
        json.dumps(
            {
                "country_count": result["country_count"],
                "validation_role_counts": result["validation_role_counts"],
                "rating_ready": result["rating_ready"],
            },
            indent=2,
        )
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
