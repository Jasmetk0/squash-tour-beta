"""Export reproducible FIFA calibration review artifacts for CI/manual inspection."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Running a file as `python scripts/foo.py` puts `scripts/` rather than the
# repository root on sys.path. Add the root explicitly so sibling `scripts.*`
# imports work both from CLI and when imported by pytest.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.audit_fifa_dimension_scores_against_prototype import (
    build_audit as build_dimension_score_audit,
)
from scripts.audit_fifa_prototype_against_signals import (
    build_audit as build_signal_audit,
)
from scripts.build_fifa_dimension_evidence_scores import (
    build_dimension_evidence_scores,
)
from scripts.review_fifa_dimension_evidence_v2 import (
    build_review as build_dimension_v2_review,
)
from scripts.build_fifa_structural_features import (
    build_features as build_structural_features,
)
from scripts.audit_fifa_structural_features_heldout import (
    build_audit as build_structural_heldout_audit,
)
from scripts.audit_fifa_structural_feature_hypotheses import (
    build_audit as build_structural_hypothesis_audit,
)
from scripts.audit_fifa_development_evidence_gaps import (
    build_gap_audit as build_development_gap_audit,
)


def export_review(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    dimension_scores = build_dimension_evidence_scores()
    signal_audit = build_signal_audit()
    dimension_score_audit = build_dimension_score_audit()
    dimension_v2_review = build_dimension_v2_review()
    structural_features = build_structural_features()
    structural_heldout_audit = build_structural_heldout_audit()
    structural_hypothesis_audit = build_structural_hypothesis_audit()
    development_gap_audit = build_development_gap_audit()

    files = {
        "dimension_scores": output_dir / "fifa_dimension_evidence_scores.json",
        "signal_audit": output_dir / "fifa_prototype_signal_audit.json",
        "dimension_score_audit": output_dir / "fifa_dimension_score_prototype_audit.json",
        "dimension_v2_review": output_dir / "fifa_dimension_evidence_v2_review.json",
        "structural_features": output_dir / "fifa_structural_features.json",
        "structural_heldout_audit": output_dir / "fifa_structural_heldout_audit.json",
        "structural_hypothesis_audit": output_dir / "fifa_structural_feature_hypothesis_audit.json",
        "development_gap_audit": output_dir / "fifa_development_evidence_gap_audit.json",
    }
    payloads = {
        "dimension_scores": dimension_scores,
        "signal_audit": signal_audit,
        "dimension_score_audit": dimension_score_audit,
        "dimension_v2_review": dimension_v2_review,
        "structural_features": structural_features,
        "structural_heldout_audit": structural_heldout_audit,
        "structural_hypothesis_audit": structural_hypothesis_audit,
        "development_gap_audit": development_gap_audit,
    }

    for key, path in files.items():
        path.write_text(
            json.dumps(payloads[key], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    summary = {
        "schema_version": "fifa_calibration_review_bundle.v1",
        "rating_ready": False,
        "country_count": dimension_scores["country_count"],
        "evidence_model_id": dimension_scores["model_id"],
        "dimension_recipe_observed_counts": dimension_scores["recipe_observed_counts"],
        "signal_audit": {
            key: {
                "sample_count": value["sample_count"],
                "spearman_rho": value["spearman_rho"],
                "review_inversion_count": value["review_inversion_count"],
            }
            for key, value in signal_audit["comparisons"].items()
        },
        "dimension_score_audit": {
            key: {
                "sample_count": value["sample_count"],
                "mean_absolute_delta": value["mean_absolute_delta"],
                "mean_signed_delta": value["mean_signed_delta"],
                "maximum_absolute_delta": value["maximum_absolute_delta"],
                "review_count": value["review_count"],
                "review_country_codes": value["review_country_codes"],
            }
            for key, value in dimension_score_audit["recipes"].items()
        },
        "dimension_v2_review": {
            "review_pass": dimension_v2_review["review_pass"],
            "policy_checks_pass": dimension_v2_review["policy_checks_pass"],
            "regression_checks_pass": dimension_v2_review["regression_checks_pass"],
            "measured_improvement": dimension_v2_review["measured_improvement"],
        },
        "structural_features": {
            "country_count": structural_features["country_count"],
            "validation_role_counts": structural_features["validation_role_counts"],
        },
        "structural_heldout_audit": {
            "review_country_codes": structural_heldout_audit["review_country_codes"],
            "heldout_country_codes": structural_heldout_audit["heldout_country_codes"],
            "reference_sample_sizes": structural_heldout_audit["reference_sample_sizes"],
        },
        "structural_hypothesis_audit": {
            key: {
                "sample_count": value["sample_count"],
                "spearman_rho": value["spearman_rho"],
                "decision": value["decision"],
            }
            for key, value in structural_hypothesis_audit["hypotheses"].items()
        },
        "development_gap_audit": {
            "development_facet_coverage": development_gap_audit["development_facet_coverage"],
            "tradition_facet_coverage": development_gap_audit["tradition_facet_coverage"],
            "next_source_priorities": development_gap_audit["next_source_priorities"],
        },
        "files": {key: path.name for key, path in files.items()},
    }

    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    summary = export_review(args.output_dir)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
