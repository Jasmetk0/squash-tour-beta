"""Build a country-indexed FIFA evidence view from canonical observations/resolutions.

This is a research/calibration input, not a rating generator. It never invents
aggregate values: UK/home-association facts remain explicit aggregate-member
components, and manual/unresolved identity facts stay outside country evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.application.earth_research_identity import identity_resolution_sha256
from scripts.build_fifa_observation_identity_resolutions import (
    RESEARCH,
    build_resolution_sets,
)


def _fact(observation, resolution) -> dict[str, Any]:
    return {
        "observation_id": observation.observation_id,
        "source_id": observation.source_id,
        "source_entity": observation.source_entity,
        "source_page": observation.source_page,
        "observation_year": observation.observation_year,
        "measurement_type": observation.measurement_type,
        "comparability_group": observation.comparability_group,
        "numeric_value": observation.numeric_value,
        "text_value": observation.text_value,
        "unit": observation.unit,
        "identity_status": resolution.status,
        "identity_method": resolution.method,
        "identity_confidence": resolution.confidence,
        "earth_country_code": resolution.earth_country_code,
        "candidate_earth_codes": list(resolution.candidate_earth_codes),
        "identity_reason": resolution.reason,
        "quality_flags": list(observation.quality_flags),
    }


def _project_assumption_fact(observation) -> dict[str, Any]:
    """Keep project priors auditable without treating them as empirical evidence."""

    if (
        observation.earth_country_code is None
        or observation.measurement_type != "project_authored_assumption"
        or observation.collection_method != "modelled_source_estimate"
        or observation.cross_country_comparable is not False
        or observation.is_direct_observation is not False
        or observation.is_statistically_modelled is not False
        or "project_authored_assumption_not_external_observation"
        not in observation.quality_flags
    ):
        raise ValueError(
            f"observation {observation.observation_id!r} is not a reviewed project assumption"
        )

    return {
        "observation_id": observation.observation_id,
        "source_id": observation.source_id,
        "source_entity": observation.source_entity,
        "source_page": observation.source_page,
        "observation_year": observation.observation_year,
        "measurement_type": observation.measurement_type,
        "comparability_group": observation.comparability_group,
        "numeric_value": observation.numeric_value,
        "text_value": observation.text_value,
        "unit": observation.unit,
        "identity_status": "project_assumption",
        "identity_method": "explicit_earth_code_project_prior",
        "identity_confidence": "high",
        "earth_country_code": observation.earth_country_code,
        "candidate_earth_codes": [],
        "identity_reason": (
            "Explicit project-authored prior is grouped by its declared Earth code for "
            "auditability only; it is not empirical calibration evidence."
        ),
        "quality_flags": list(observation.quality_flags),
    }


def _context_only_fact(observation) -> dict[str, Any]:
    """Keep non-sport territorial/context facts auditable but out of calibration."""

    notes = (observation.definition_notes or "").lower()
    explicitly_non_sport = (
        "not a sports measurement" in notes
        or "not sports evidence" in notes
        or "constitutional_status_not_sports_measurement" in observation.quality_flags
    )
    if (
        observation.earth_country_code is None
        or observation.measurement_type != "structural_event"
        or observation.territory_mapping_method is not None
        or observation.numeric_value is not None
        or observation.cross_country_comparable is not False
        or observation.is_direct_observation is not True
        or observation.is_statistically_modelled is not False
        or observation.competition_scope is not None
        or not explicitly_non_sport
    ):
        raise ValueError(
            f"observation {observation.observation_id!r} is not reviewed context-only evidence"
        )
    return {
        "observation_id": observation.observation_id,
        "source_id": observation.source_id,
        "source_entity": observation.source_entity,
        "source_page": observation.source_page,
        "observation_year": observation.observation_year,
        "measurement_type": observation.measurement_type,
        "comparability_group": observation.comparability_group,
        "numeric_value": observation.numeric_value,
        "text_value": observation.text_value,
        "unit": observation.unit,
        "identity_status": "context_only",
        "identity_method": "explicit_earth_code_context_only",
        "identity_confidence": "high",
        "earth_country_code": observation.earth_country_code,
        "candidate_earth_codes": [],
        "identity_reason": (
            "Explicit territorial/context fact is retained for auditability only and "
            "is excluded from empirical sport calibration evidence."
        ),
        "quality_flags": list(observation.quality_flags),
    }


def _direct_mapped_fact(observation) -> dict[str, Any]:
    mapping = observation.territory_mapping_method
    if observation.earth_country_code is None:
        raise ValueError(
            f"observation {observation.observation_id!r} lacks canonical identity handling"
        )

    if (
        observation.measurement_type in {"football_structural_event", "sport_structural_event"}
        and mapping == "explicit_reviewed_event_to_earth"
    ):
        reason = (
            "Canonical structural observation carries an explicit reviewed Earth mapping."
        )
    elif (
        observation.measurement_type == "fifa_mens_year_end_world_rank"
        and mapping == "explicit_reviewed_outcome_to_earth"
        and "outcome_validation_only" in observation.quality_flags
    ):
        reason = (
            "Canonical FIFA outcome-validation observation carries an explicit "
            "reviewed Earth mapping."
        )
    elif (
        mapping == "explicit_reviewed_fact_to_earth"
        and "explicit_reviewed_country_fact" in observation.quality_flags
        and observation.cross_country_comparable is False
    ):
        reason = (
            "Canonical country-specific fact carries an explicit reviewed Earth "
            "mapping and is explicitly non-comparable across countries."
        )
    else:
        raise ValueError(
            f"observation {observation.observation_id!r} lacks canonical identity handling"
        )

    return {
        "observation_id": observation.observation_id,
        "source_id": observation.source_id,
        "source_entity": observation.source_entity,
        "source_page": observation.source_page,
        "observation_year": observation.observation_year,
        "measurement_type": observation.measurement_type,
        "comparability_group": observation.comparability_group,
        "numeric_value": observation.numeric_value,
        "text_value": observation.text_value,
        "unit": observation.unit,
        "identity_status": "direct",
        "identity_method": mapping,
        "identity_confidence": "high",
        "earth_country_code": observation.earth_country_code,
        "candidate_earth_codes": [],
        "identity_reason": reason,
        "quality_flags": list(observation.quality_flags),
    }


def build_index(research_path: Path = RESEARCH) -> dict[str, Any]:
    bundle = load_earth_research_bundle(research_path)
    resolution_sets = build_resolution_sets()

    resolutions = {}
    for resolution_set in resolution_sets.values():
        for resolution in resolution_set.resolutions:
            if resolution.observation_id in resolutions:
                raise ValueError(
                    f"duplicate resolution for {resolution.observation_id!r}"
                )
            resolutions[resolution.observation_id] = resolution

    extra = sorted(set(resolutions) - set(bundle.observations))
    if extra:
        raise ValueError(
            f"identity resolutions reference observations not in research bundle: {extra}"
        )

    countries: dict[str, list[dict[str, Any]]] = {}
    manual_review: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    project_assumptions: list[dict[str, Any]] = []
    context_only: list[dict[str, Any]] = []
    direct_mapped_observation_count = 0

    for observation_id in sorted(bundle.observations):
        observation = bundle.observations[observation_id]
        resolution = resolutions.get(observation_id)

        if resolution is None:
            if observation.measurement_type == "project_authored_assumption":
                project_assumptions.append(_project_assumption_fact(observation))
                continue
            if observation.measurement_type == "structural_event":
                context_only.append(_context_only_fact(observation))
                continue
            fact = _direct_mapped_fact(observation)
            countries.setdefault(fact["earth_country_code"], []).append(fact)
            direct_mapped_observation_count += 1
            continue

        fact = _fact(observation, resolution)

        if resolution.status in {"direct", "aggregate_member"}:
            if resolution.earth_country_code is None:
                raise ValueError(
                    f"safe resolution lacks Earth target: {observation_id}"
                )
            countries.setdefault(resolution.earth_country_code, []).append(fact)
        elif resolution.status == "manual_review":
            manual_review.append(fact)
        elif resolution.status == "unresolved":
            unresolved.append(fact)
        else:
            raise ValueError(
                f"unsupported identity status {resolution.status!r}"
            )

    countries = {
        code: sorted(facts, key=lambda item: item["observation_id"])
        for code, facts in sorted(countries.items())
    }
    manual_review.sort(key=lambda item: item["observation_id"])
    unresolved.sort(key=lambda item: item["observation_id"])
    project_assumptions.sort(key=lambda item: item["observation_id"])
    context_only.sort(key=lambda item: item["observation_id"])

    safe_count = sum(len(facts) for facts in countries.values())
    total_count = (
        safe_count
        + len(manual_review)
        + len(unresolved)
        + len(project_assumptions)
        + len(context_only)
    )
    if total_count != len(bundle.observations):
        raise ValueError("country evidence partition lost or duplicated observations")

    return {
        "schema_version": "fifa_country_evidence_index.v1",
        "world_id": "fifa_earth",
        "observation_count": len(bundle.observations),
        "safe_country_evidence_count": safe_count,
        "manual_review_count": len(manual_review),
        "unresolved_count": len(unresolved),
        "project_assumption_count": len(project_assumptions),
        "context_only_count": len(context_only),
        "country_count_with_safe_evidence": len(countries),
        "direct_mapped_observation_count": direct_mapped_observation_count,
        "input_observation_dataset_sha256s": {
            dataset_id: manifest.sha256
            for dataset_id, manifest in sorted(
                bundle.research.observation_datasets.items()
            )
        },
        "input_identity_resolution_sha256s": {
            set_id: identity_resolution_sha256(resolution_set)
            for set_id, resolution_set in sorted(resolution_sets.items())
        },
        "countries": countries,
        "manual_review": manual_review,
        "unresolved": unresolved,
        "project_assumptions": project_assumptions,
        "context_only": context_only,
        "rating_ready": False,
        "limitations": [
            "Safe evidence is grouped by Earth identity but is not a country rating.",
            "Aggregate-member facts remain source components; no synthetic aggregate is created here.",
            "Manual-review, unresolved and project-authored assumption observations are excluded from empirical country evidence.",
            "Project-authored assumptions remain separately indexed for provenance and never feed the empirical calibration signals.",
            "Territorial/demographic context-only facts remain separately indexed and never feed empirical sport calibration signals.",
            "Structural and validation-only outcome observations may bypass separate identity-resolution sets only when their canonical observation carries an explicit reviewed Earth mapping.",
            "Cross-country comparability flags and source-definition limitations remain authoritative.",
        ],
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research", type=Path, default=RESEARCH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_index(args.research)
    summary = {
        key: result[key]
        for key in (
            "observation_count",
            "safe_country_evidence_count",
            "manual_review_count",
            "unresolved_count",
            "project_assumption_count",
            "context_only_count",
            "country_count_with_safe_evidence",
            "direct_mapped_observation_count",
        )
    }
    print(json.dumps(summary, indent=2))

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
