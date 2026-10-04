"""Place held-out FIFA structural features into review-set reference distributions.

The nine-country review set defines the reference distributions. Germany, Brazil,
Iceland and San Marino are projected into those distributions without affecting
them. The output is diagnostic only and never produces country ratings.
"""
from __future__ import annotations

import json
from typing import Any

from scripts.build_fifa_structural_features import build_features

REVIEW_ROLE = "review"
HELDOUT_ROLE = "held_out_validation"


def _midrank_percentile(value: float, reference: list[float], *, higher_is_more: bool = True) -> float | None:
    if not reference:
        return None
    ordered = sorted(reference)
    if not higher_is_more:
        ordered = sorted((-item for item in reference))
        probe = -value
    else:
        probe = value
    positions = [index + 1 for index, candidate in enumerate(ordered) if candidate == probe]
    if positions:
        midrank = sum(positions) / len(positions)
    else:
        lower = sum(candidate < probe for candidate in ordered)
        equal = sum(candidate == probe for candidate in ordered)
        midrank = lower + (equal + 1) / 2
    n = len(ordered)
    percentile = 50.0 if n == 1 else (midrank - 1) / (n - 1) * 100
    return round(max(0.0, min(100.0, percentile)), 2)


def _feature_payload(country: dict[str, Any]) -> dict[str, Any]:
    tradition = country["tradition"]
    development = country["development"]
    tradition_span = tradition["evidence_span_years_to_2026"]
    development_span = (
        None
        if development["first_event_year"] is None
        else 2026 - int(development["first_event_year"])
    )
    recency = development["years_since_latest_evidence"]

    return {
        "tradition_span_years": tradition_span,
        "pre_1955_tradition_event_count": tradition["pre_1955_event_count"],
        "institutional_foundation_year": tradition["institutional_foundation_year"],
        "first_competition_year": tradition["first_competition_year"],
        "development_history_span_years": development_span,
        "development_years_since_latest_evidence": recency,
        "development_pathway_year": development["first_pathway_or_academy_year"],
        "development_training_centre_year": development["first_training_centre_year"],
        "development_infrastructure_year": development["first_infrastructure_year"],
        "development_event_types": list(development["event_types"]),
        "structural_observation_ids": list(country["structural_observation_ids"]),
    }


def build_audit() -> dict[str, Any]:
    features = build_features()
    review_codes = sorted(
        code
        for code, country in features["countries"].items()
        if country["validation_role"] == REVIEW_ROLE
    )
    heldout_codes = sorted(
        code
        for code, country in features["countries"].items()
        if country["validation_role"] == HELDOUT_ROLE
    )

    review_payloads = {
        code: _feature_payload(features["countries"][code])
        for code in review_codes
    }
    heldout_payloads = {
        code: _feature_payload(features["countries"][code])
        for code in heldout_codes
    }

    tradition_reference = [
        float(payload["tradition_span_years"])
        for payload in review_payloads.values()
        if payload["tradition_span_years"] is not None
    ]
    development_span_reference = [
        float(payload["development_history_span_years"])
        for payload in review_payloads.values()
        if payload["development_history_span_years"] is not None
    ]
    development_recency_reference = [
        float(payload["development_years_since_latest_evidence"])
        for payload in review_payloads.values()
        if payload["development_years_since_latest_evidence"] is not None
    ]

    heldout: dict[str, Any] = {}
    for code, payload in heldout_payloads.items():
        tradition_span = payload["tradition_span_years"]
        development_span = payload["development_history_span_years"]
        recency = payload["development_years_since_latest_evidence"]

        heldout[code] = {
            **payload,
            "tradition_span_review_percentile": (
                None
                if tradition_span is None
                else _midrank_percentile(
                    float(tradition_span), tradition_reference
                )
            ),
            "development_history_span_review_percentile": (
                None
                if development_span is None
                else _midrank_percentile(
                    float(development_span), development_span_reference
                )
            ),
            "development_recency_review_percentile": (
                None
                if recency is None
                else _midrank_percentile(
                    float(recency),
                    development_recency_reference,
                    higher_is_more=False,
                )
            ),
            "fit_allowed": False,
        }

    return {
        "schema_version": "fifa_structural_heldout_audit.v1",
        "world_id": "fifa_earth",
        "rating_ready": False,
        "review_country_codes": review_codes,
        "heldout_country_codes": heldout_codes,
        "reference_sample_sizes": {
            "tradition_span_years": len(tradition_reference),
            "development_history_span_years": len(development_span_reference),
            "development_recency": len(development_recency_reference),
        },
        "review_features": review_payloads,
        "heldout": heldout,
        "limitations": [
            "Review-set distributions are descriptive references, not fitted rating curves.",
            "Held-out countries do not affect reference distributions or model parameters.",
            "Longer structural history is not equivalent to higher current football quality.",
            "Recent development evidence is not proof of successful development outcomes.",
            "Missing curated evidence remains unknown rather than a low score.",
        ],
    }


def main() -> None:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = build_audit()
    print(
        json.dumps(
            {
                "review_country_codes": result["review_country_codes"],
                "heldout_country_codes": result["heldout_country_codes"],
                "reference_sample_sizes": result["reference_sample_sizes"],
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
