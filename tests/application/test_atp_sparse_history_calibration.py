from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.domain.countries.rating_history import GAME_ATTRIBUTE_NAMES


RESEARCH = Path("config/earth_research/atp_earth.json")
PACKAGE_HISTORY_ROOT = Path("config/world_packages/atp_earth/generation/country_histories")

SPARSE_HISTORY_ANCHORS = {
    "GUM": (
        1973,
        "atp-itf-affiliated-associations-2015-v1#gum-association-1973",
    ),
    "KIR": (
        1979,
        "atp-itf-affiliated-associations-2015-v1#kir-association-1979",
    ),
    "FSM": (
        1995,
        "atp-itf-affiliated-associations-2015-v1#fsm-association-1995",
    ),
    "MNP": (
        1998,
        "atp-itf-affiliated-associations-2015-v1#mnp-association-1998",
    ),
    "TLS": (
        2021,
        "atp-itf-timor-leste-membership-2021-v1#tls-itf-membership-2021",
    ),
}


def test_sparse_history_sources_are_verified_and_resolvable() -> None:
    bundle = load_earth_research_bundle(RESEARCH)

    assert "atp-itf-affiliated-associations-2015-v1" in bundle.datasets
    assert "atp-itf-timor-leste-membership-2021-v1" in bundle.datasets
    assert len(bundle.datasets) == 488
    assert len(bundle.observations) == 1039

    for code, (anchor_year, observation_id) in SPARSE_HISTORY_ANCHORS.items():
        history = bundle.research.countries[code]
        assert observation_id in bundle.observations
        assert observation_id in {
            item
            for rating in history.years[anchor_year].ratings.values()
            for item in rating.observation_ids
        }


def test_sparse_histories_replace_false_2026_cliffs_with_explicit_reconstruction() -> None:
    bundle = load_earth_research_bundle(RESEARCH)

    for code, (anchor_year, observation_id) in SPARSE_HISTORY_ANCHORS.items():
        history = bundle.research.countries[code]
        model_ids = {
            rating.calibration_model_id
            for year in history.years.values()
            for rating in year.ratings.values()
        }
        assert len(model_ids) == 1
        model_id = next(iter(model_ids))
        model = bundle.calibration_models[model_id]
        assert model["construction"]["kind"] == "documented_anchor_linear_interpolation"
        assert str(anchor_year) in model["anchor_values"][code]

        for attribute in GAME_ATTRIBUTE_NAMES:
            deltas = [
                abs(
                    history.years[year].ratings[attribute].value
                    - history.years[year - 1].ratings[attribute].value
                )
                for year in range(anchor_year + 1, 2027)
            ]
            assert max(deltas) < 1.0, (code, attribute, max(deltas))

        assert observation_id in history.years[anchor_year].ratings["squash_access"].observation_ids
        assert observation_id in history.years[2026].ratings["squash_access"].observation_ids

        old_cliff = abs(
            history.years[2026].ratings["squash_access"].value
            - history.years[2025].ratings["squash_access"].value
        )
        assert old_cliff < 1.0, (code, old_cliff)


def test_timor_leste_keeps_membership_and_first_development_visit_distinct() -> None:
    bundle = load_earth_research_bundle(RESEARCH)
    tls = bundle.research.countries["TLS"]

    membership = "atp-itf-timor-leste-membership-2021-v1#tls-itf-membership-2021"
    first_visit = "atp-itf-timor-leste-membership-2021-v1#tls-first-itf-visit-2022"

    assert membership in tls.years[2021].ratings["squash_access"].observation_ids
    assert first_visit not in tls.years[2021].ratings["development_quality"].observation_ids
    assert first_visit in tls.years[2022].ratings["development_quality"].observation_ids


def test_distributed_sparse_histories_match_research_exactly() -> None:
    bundle = load_earth_research_bundle(RESEARCH)

    for code in SPARSE_HISTORY_ANCHORS:
        packaged = json.loads((PACKAGE_HISTORY_ROOT / f"{code}.json").read_text())
        assert packaged == bundle.research.countries[code].model_dump(mode="json")
