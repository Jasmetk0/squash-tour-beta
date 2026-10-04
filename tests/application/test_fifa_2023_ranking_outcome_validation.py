from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.application.earth_research_observations import (
    EarthObservationDataset,
    observation_dataset_sha256,
)
from scripts.audit_fifa_competition_against_2023_ranking import build_audit
from scripts.build_fifa_country_evidence_index import build_index
from scripts.normalize_fifa_mens_ranking_2023 import (
    DATASET_ID,
    DEFAULT_OUTPUT,
    DEFAULT_SEED,
    SOURCE_ID,
    build_dataset,
    build_manifest,
)


RESEARCH = Path("config/earth_research/fifa_earth.json")


def test_fifa_2023_ranking_dataset_is_reproducible_and_registered() -> None:
    generated = build_dataset()
    checked_in = EarthObservationDataset.model_validate_json(
        DEFAULT_OUTPUT.read_text(encoding="utf-8")
    )
    research = json.loads(RESEARCH.read_text(encoding="utf-8"))

    assert generated == checked_in
    assert len(checked_in.observations) == 13
    assert checked_in.source_id == SOURCE_ID
    assert (
        observation_dataset_sha256(checked_in)
        == "0c1dd57c57235157e6dda57dec1853ab66ef94aecc32f6258b211aa5764eeb26"
    )

    manifest = build_manifest(
        checked_in,
        relative_path=DEFAULT_OUTPUT.relative_to(
            Path("config/earth_research")
        ).as_posix(),
    )
    assert research["observation_datasets"][DATASET_ID] == manifest.model_dump(
        mode="json"
    )

    bundle = load_earth_research_bundle(RESEARCH)
    assert bundle.datasets[DATASET_ID] == checked_in
    assert len(bundle.observations) == 1378


def test_ranking_seed_preserves_exact_review_and_heldout_2023_values() -> None:
    seed = json.loads(DEFAULT_SEED.read_text(encoding="utf-8"))
    by_code = {
        row["earth_country_code"]: row
        for row in seed["countries"]
    }

    assert len(by_code) == 13
    assert {
        code
        for code, row in by_code.items()
        if row["validation_role"] == "review"
    } == {"CZE", "FRO", "IND", "JPN", "MAR", "SEN", "SVK", "USA", "ZAF"}
    assert {
        code
        for code, row in by_code.items()
        if row["validation_role"] == "held_out_validation"
    } == {"BRA", "DEU", "ISL", "SMR"}

    assert {
        code: row["final_rank"]
        for code, row in by_code.items()
    } == {
        "BRA": 5,
        "CZE": 39,
        "DEU": 16,
        "FRO": 135,
        "IND": 102,
        "ISL": 71,
        "JPN": 17,
        "MAR": 13,
        "SEN": 20,
        "SMR": 210,
        "SVK": 45,
        "USA": 12,
        "ZAF": 66,
    }


def test_ranking_observations_are_validation_only_direct_mapped_outcomes() -> None:
    dataset = build_dataset()

    for observation in dataset.observations:
        assert observation.measurement_type == "fifa_mens_year_end_world_rank"
        assert observation.observation_year == 2023
        assert observation.unit == "rank_1_is_best"
        assert observation.cross_country_comparable is True
        assert observation.is_direct_observation is True
        assert observation.is_statistically_modelled is True
        assert (
            observation.territory_mapping_method
            == "explicit_reviewed_outcome_to_earth"
        )
        assert "supports_competition_quality" in observation.quality_flags
        assert "outcome_validation_only" in observation.quality_flags
        assert "not_domestic_competition_quality_directly" in observation.quality_flags


def test_country_evidence_admits_ranking_outcomes_without_changing_manual_partition() -> None:
    evidence = build_index()

    assert evidence["observation_count"] == 1410
    assert evidence["safe_country_evidence_count"] == 1388
    assert evidence["manual_review_count"] == 22
    assert evidence["unresolved_count"] == 0
    assert evidence["direct_mapped_observation_count"] == 125

    ranking_facts = [
        fact
        for facts in evidence["countries"].values()
        for fact in facts
        if fact["measurement_type"] == "fifa_mens_year_end_world_rank"
    ]
    assert len(ranking_facts) == 13
    assert all(fact["identity_status"] == "direct" for fact in ranking_facts)
    assert all(
        fact["identity_method"] == "explicit_reviewed_outcome_to_earth"
        for fact in ranking_facts
    )


def test_competition_outcome_audit_keeps_review_and_heldout_separate() -> None:
    audit = build_audit()

    assert audit["schema_version"] == "fifa_competition_outcome_validation.v1"
    assert audit["outcome_year"] == 2023
    assert audit["competition_recipe"] == "competition_quality@2023"
    assert audit["rating_ready"] is False
    assert audit["fit_allowed"] is False

    review = audit["groups"]["review"]
    heldout = audit["groups"]["held_out_validation"]

    assert review["ranking_outcome_count"] == 9
    assert review["numeric_comparison_count"] == 6
    assert review["missing_competition_score_country_codes"] == [
        "MAR",
        "SEN",
        "FRO",
    ] or set(review["missing_competition_score_country_codes"]) == {
        "FRO",
        "MAR",
        "SEN",
    }

    assert heldout["ranking_outcome_count"] == 4
    assert heldout["numeric_comparison_count"] == 3
    assert heldout["missing_competition_score_country_codes"] == ["SMR"]

    for payload in (review, heldout):
        rho = payload["spearman_score_vs_better_rank"]
        assert rho is not None
        assert -1 <= rho <= 1
        assert payload["pairwise"]["concordance_rate"] is not None
        assert 0 <= payload["pairwise"]["concordance_rate"] <= 1
        assert all(country["fit_allowed"] is False for country in payload["countries"])


def test_heldout_ranking_outcomes_do_not_enter_model_component_provenance() -> None:
    audit = build_audit()
    heldout = audit["groups"]["held_out_validation"]

    for country in heldout["countries"]:
        ranking_id = country["ranking_observation_id"]
        assert ranking_id.startswith(
            "fifa-mens-year-end-ranking-2023-review-heldout-v1#"
        )
        assert ranking_id not in country["competition_component_observation_ids"]
