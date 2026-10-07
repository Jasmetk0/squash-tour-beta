from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.application.earth_package_builder import load_earth_research_bundle
from beta_engine.domain.countries.rating_history import GAME_ATTRIBUTE_NAMES


RESEARCH = Path("config/earth_research/atp_earth.json")
PACKAGE_HISTORY_ROOT = Path("config/world_packages/atp_earth/generation/country_histories")

ANCHORS = {
    "QAT": [1955, 1971, 2000, 2020, 2026],
    "PYF": [1955, 1957, 2000, 2020, 2026],
    "ARE": [1955, 1971, 2000, 2020, 2026],
}

BATCH3_ANCHORS = {
    "XKX": [1955, 2026],
    "TWN": [1955, 2026],
    "COG": [1955, 2026],
    "MHL": [1955, 1986, 2026],
}


@lru_cache(maxsize=1)
def _bundle():
    return load_earth_research_bundle(RESEARCH)


def test_reviewed_gap5_models_use_explicit_anchor_interpolation() -> None:
    bundle = _bundle()

    for code, anchor_years in ANCHORS.items():
        history = bundle.research.countries[code]
        model_id = f"atp-earth-{code.lower()}-reviewed-structure.v1"
        model = bundle.calibration_models[model_id]

        assert model["construction"]["kind"] == "explicit_anchor_linear_interpolation"
        assert sorted(int(year) for year in model["anchor_values"][code]) == anchor_years

        for year in anchor_years:
            expected = model["anchor_values"][code][str(year)]
            actual = [
                history.years[year].ratings[attribute].value
                for attribute in GAME_ATTRIBUTE_NAMES
            ]
            assert actual == expected

        for attribute in GAME_ATTRIBUTE_NAMES:
            deltas = [
                abs(
                    history.years[year].ratings[attribute].value
                    - history.years[year - 1].ratings[attribute].value
                )
                for year in range(1956, 2027)
            ]
            assert max(deltas) < 0.5, (code, attribute, max(deltas))


def test_reviewed_gap5_interpolation_does_not_backdate_evidence() -> None:
    bundle = _bundle()

    for code in ANCHORS:
        history = bundle.research.countries[code]

        before_2020 = history.years[2019].ratings["squash_access"].observation_ids
        at_2020 = history.years[2020].ratings["squash_access"].observation_ids
        before_2026 = history.years[2025].ratings["development_quality"].observation_ids
        at_2026 = history.years[2026].ratings["development_quality"].observation_ids

        assert not any("return-2020" in ref for ref in before_2020)
        assert any("return-2020" in ref for ref in at_2020)
        assert not any("association-2026" in ref for ref in before_2026)
        assert any("association-2026" in ref for ref in at_2026)


def test_reviewed_gap5_distributed_histories_match_research_exactly() -> None:
    bundle = _bundle()

    for code in ANCHORS:
        packaged = json.loads((PACKAGE_HISTORY_ROOT / f"{code}.json").read_text())
        assert packaged == bundle.research.countries[code].model_dump(mode="json")


def test_reviewed_batch3_models_use_explicit_anchor_interpolation() -> None:
    bundle = _bundle()

    for code, anchor_years in BATCH3_ANCHORS.items():
        history = bundle.research.countries[code]
        model_id = f"atp-earth-{code.lower()}-reviewed-structure.v1"
        model = bundle.calibration_models[model_id]

        assert model["construction"]["kind"] == "explicit_anchor_linear_interpolation"
        assert sorted(int(year) for year in model["anchor_values"][code]) == anchor_years

        for year in anchor_years:
            expected = model["anchor_values"][code][str(year)]
            actual = [
                history.years[year].ratings[attribute].value
                for attribute in GAME_ATTRIBUTE_NAMES
            ]
            assert actual == expected

        for attribute in GAME_ATTRIBUTE_NAMES:
            values = [
                history.years[year].ratings[attribute].value
                for year in range(1955, 2027)
            ]
            deltas = [
                abs(current - previous)
                for previous, current in zip(values, values[1:])
            ]
            assert max(deltas) < 0.5, (code, attribute, max(deltas))

            longest_flat_run = 1
            current_flat_run = 1
            for previous, current in zip(values, values[1:]):
                if current == previous:
                    current_flat_run += 1
                    longest_flat_run = max(longest_flat_run, current_flat_run)
                else:
                    current_flat_run = 1
            assert longest_flat_run < 12, (code, attribute, longest_flat_run)


def test_reviewed_batch3_interpolation_does_not_backdate_2026_evidence() -> None:
    bundle = _bundle()

    for code in BATCH3_ANCHORS:
        history = bundle.research.countries[code]
        before_2026 = history.years[2025].ratings["squash_access"].observation_ids
        at_2026 = history.years[2026].ratings["squash_access"].observation_ids

        assert not any("association-2026" in ref for ref in before_2026)
        assert any("association-2026" in ref for ref in at_2026)


def test_reviewed_batch3_distributed_histories_match_research_exactly() -> None:
    bundle = _bundle()

    for code in BATCH3_ANCHORS:
        packaged = json.loads((PACKAGE_HISTORY_ROOT / f"{code}.json").read_text())
        assert packaged == bundle.research.countries[code].model_dump(mode="json")
