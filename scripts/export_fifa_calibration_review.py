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


def export_review(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    dimension_scores = build_dimension_evidence_scores()
    signal_audit = build_signal_audit()
    dimension_score_audit = build_dimension_score_audit()

    files = {
        "dimension_scores": output_dir / "fifa_dimension_evidence_scores.json",
        "signal_audit": output_dir / "fifa_prototype_signal_audit.json",
        "dimension_score_audit": output_dir / "fifa_dimension_score_prototype_audit.json",
    }
    payloads = {
        "dimension_scores": dimension_scores,
        "signal_audit": signal_audit,
        "dimension_score_audit": dimension_score_audit,
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
