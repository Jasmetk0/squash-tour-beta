from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

from pydantic import ValidationError

from beta_engine.domain.countries import Country, CountryTalentModel, CountriesConfig
from beta_engine.domain.countries.rating_history import CountryRatingHistory, GAME_ATTRIBUTE_NAMES, RATING_SCALE_V2
from beta_engine.infrastructure.world_package_storage import WorldPackageCountryStore
from beta_engine.application.earth_package_builder import (
    EarthResearchBundle,
    EarthSportResearch,
    audit_earth_research,
    build_earth_package,
)
from beta_engine.application.earth_research_observations import (
    EarthObservationDataset,
    observation_dataset_sha256,
)


DATASET_ID = "synthetic-observations"
OBSERVATION_ID = f"{DATASET_ID}#test"


def evidence(value, year):
    return dict(
        value=value,
        method="sourced_estimate",
        confidence="low",
        source_ids=["test"],
        observation_ids=[OBSERVATION_ID],
        rationale="Synthetic test data; not real country research.",
        anchor_years=[year],
    )


def history(year_values):
    return CountryRatingHistory.model_validate(dict(
        reference_year=min(year_values), data_cutoff="2026-10-03",
        years={year: dict(historical_entity="TEST", territory_mapping_note="Synthetic unchanged territory",
                         ratings={name: evidence(value, year) for name in GAME_ATTRIBUTE_NAMES})
               for year, value in year_values.items()},
    ))


def country(h=None, **extra):
    fields = dict(code="AAA", name="Test", region="TEST", population=1_000_000,
                  population_by_year={year: 1_000_000 for year in range(1955, 2051)},
                  default_population_year=2020, default_population=1_000_000)
    fields.update({name: 3 for name in GAME_ATTRIBUTE_NAMES})
    if h:
        fields.update(rating_history=h, rating_scale=RATING_SCALE_V2)
        fields.update({name: rating.value for name, rating in h.years[h.reference_year].ratings.items()})
    fields.update(extra)
    return Country.model_validate(fields)


def observation_dataset():
    return EarthObservationDataset.model_validate(dict(
        dataset_id=DATASET_ID,
        source_id="test",
        source_url="https://example.com/test",
        generated_by="tests",
        scope="Synthetic package provenance test",
        limitations="Not real country data",
        observations=[dict(
            observation_id=OBSERVATION_ID,
            source_id="test",
            source_entity="Synthetic source",
            earth_country_code="AAA",
            observation_year=2026,
            measurement_type="synthetic_fact",
            text_value="Synthetic evidence",
            unit="event",
            collection_method="official_narrative",
            coverage_scope="national",
            definition_notes="Synthetic observation used only by tests.",
        )],
    ))


def research(h, world_id="fifa_earth"):
    dataset = observation_dataset()
    return EarthSportResearch.model_validate(dict(
        world_id=world_id,
        data_cutoff="2026-10-03",
        countries={"AAA": h.model_dump()},
        sources={
            "test": dict(
                title="Synthetic test",
                url="https://example.com/test",
                accessed_on="2026-10-03",
                scope="Only synthetic test evidence",
                limitations="Not real country data",
            )
        },
        observation_datasets={
            DATASET_ID: dict(
                dataset_id=DATASET_ID,
                source_id="test",
                relative_path="observations/synthetic.json",
                sha256=observation_dataset_sha256(dataset),
                record_count=1,
                generated_by="tests",
            )
        },
    ))


def research_bundle(h, world_id="fifa_earth", calibration_models=None):
    dataset = observation_dataset()
    profile = research(h, world_id)
    return EarthResearchBundle(
        research=profile,
        datasets={DATASET_ID: dataset},
        observations={OBSERVATION_ID: dataset.observations[0]},
        calibration_models=calibration_models or {},
    )


class CountryRatingHistoryTests(unittest.TestCase):
    def test_builder_rejects_output_inside_source_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with self.assertRaisesRegex(ValueError, "outside the base"):
                build_earth_package(
                    base_package=base,
                    bundle=research_bundle(history({1955: 3})),
                    output=base / "nested" / "earth",
                )
            self.assertEqual(list(base.iterdir()), [])

    def test_legacy_serialization_and_math_are_unchanged(self):
        c = country(competition_quality=4.75)
        self.assertNotIn("rating_scale", c.model_dump())
        self.assertNotIn("rating_history", c.model_dump())
        self.assertNotIn("rating_effective_year", c.model_dump())
        self.assertEqual(c.competition_quality_norm, 0.9375)
        self.assertEqual(CountryTalentModel().participation_factor(c), 0.36)
        self.assertIs(c.at_rating_year(2000), c)

    def test_new_scale_requires_explicit_version(self):
        with self.assertRaises(ValidationError):
            country(squash_popularity=7.4)
        c = country(rating_scale=RATING_SCALE_V2, squash_popularity=7.4)
        self.assertEqual(c.squash_popularity, 7.4)
        self.assertEqual(c.rating_maximum, 10)

    def test_new_scale_rejects_false_precision_and_non_numbers(self):
        for value in (0, 10.1, 7.41, True, "7.4", float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                country(rating_scale=RATING_SCALE_V2, squash_popularity=value)

    def test_endpoints_and_tenths(self):
        for value in (1, 1.1, 7.4, 10):
            c = country(rating_scale=RATING_SCALE_V2, squash_popularity=value)
            self.assertGreaterEqual(c.squash_popularity_norm, 0)
            self.assertLessEqual(c.squash_popularity_norm, 1)

    def test_year_resolution_is_nonmutating_and_reports_source(self):
        h = history({1955: 1, 2000: 5, 2026: 10})
        original = country(h)
        self.assertEqual(original.at_rating_year(2000).squash_popularity, 5)
        self.assertEqual(original.squash_popularity, 1)
        self.assertEqual(h.resolve(2050)[0], 2026)
        self.assertEqual(h.resolve(1954)[0], 1955)
        self.assertEqual(h.resolve(2013)[0], 2000)
        self.assertEqual(original.at_rating_year(2050).rating_effective_year, 2050)

    def test_missing_attributes_are_rejected_not_filled(self):
        raw = history({1955: 3}).model_dump()
        del raw["years"][1955]["ratings"]["elite_support"]
        with self.assertRaises(ValidationError):
            CountryRatingHistory.model_validate(raw)

    def test_evidence_and_interpolation_boundaries_are_validated(self):
        raw = history({1955: 3}).model_dump()
        raw["years"][1955]["ratings"]["elite_support"]["method"] = "interpolated"
        with self.assertRaises(ValidationError):
            CountryRatingHistory.model_validate(raw)

    def test_derived_estimate_requires_calibration_model(self):
        raw = history({1955: 3}).model_dump()
        rating = raw["years"][1955]["ratings"]["elite_support"]
        rating["method"] = "derived_estimate"
        with self.assertRaises(ValidationError):
            CountryRatingHistory.model_validate(raw)
        rating["calibration_model_id"] = "football-country-calibration.v1"
        CountryRatingHistory.model_validate(raw)

    def test_observation_ids_are_required_and_namespaced(self):
        raw = history({1955: 3}).model_dump()
        rating = raw["years"][1955]["ratings"]["elite_support"]
        rating["observation_ids"] = []
        with self.assertRaises(ValidationError):
            CountryRatingHistory.model_validate(raw)
        rating["observation_ids"] = ["not-namespaced"]
        with self.assertRaises(ValidationError):
            CountryRatingHistory.model_validate(raw)

    def test_history_cannot_be_attached_to_legacy_scale(self):
        with self.assertRaises(ValidationError):
            country(rating_history=history({1955: 3}))

    def test_scalar_and_history_must_agree(self):
        with self.assertRaises(ValidationError):
            country(history({1955: 3}), squash_popularity=4)

    def test_court_count_is_not_a_new_scale_input(self):
        with self.assertRaises(ValidationError):
            country(rating_scale=RATING_SCALE_V2, court_count=12)

    def test_storage_roundtrip_and_no_court_file(self):
        with tempfile.TemporaryDirectory() as d:
            store = WorldPackageCountryStore(Path(d))
            c = country(history({1955: 1.2, 2026: 9.8}))
            store.replace_dataset(CountriesConfig(countries=[c]))
            self.assertEqual(store.load_country("AAA"), c)
            self.assertFalse((Path(d) / "countries/AAA/attributes/court_count.json").exists())
            self.assertEqual(store.load_country("AAA").at_rating_year(2026).elite_support, 9.8)

    def test_unknown_rating_context_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            store = WorldPackageCountryStore(Path(d))
            store.replace_dataset(CountriesConfig(countries=[country()]))
            (Path(d) / "countries/AAA/attributes/rating_context.json").write_text("{}")
            with self.assertRaises(ValueError):
                store.load_country("AAA")

    def test_coverage_is_all_72_years_not_2000_onwards(self):
        partial = research(history({year: 3 for year in range(2000, 2027)}))
        report = audit_earth_research(partial, [country()])
        self.assertFalse(report["coverage_complete"])
        self.assertEqual(report["missing_years"]["AAA"], list(range(1955, 2000)))
        self.assertEqual(report["required_rating_count"], 432)
        self.assertEqual(report["observation_dataset_count"], 1)
        self.assertEqual(report["observation_record_count"], 1)

    def test_unknown_source_is_rejected(self):
        raw = research(history({1955: 3})).model_dump()
        raw["sources"] = {}
        with self.assertRaises(ValidationError):
            EarthSportResearch.model_validate(raw)

    def test_unknown_observation_dataset_is_rejected(self):
        raw = research(history({1955: 3})).model_dump()
        raw["countries"]["AAA"]["years"][1955]["ratings"]["elite_support"]["observation_ids"] = [
            "missing-dataset#observation"
        ]
        with self.assertRaises(ValidationError):
            EarthSportResearch.model_validate(raw)

    def test_observation_dataset_source_must_be_cited(self):
        raw = research(history({1955: 3})).model_dump()
        raw["sources"]["other"] = dict(
            title="Other source",
            url="https://example.com/other",
            accessed_on="2026-10-03",
            scope="Other synthetic evidence",
            limitations="Not real country data",
        )
        raw["observation_datasets"][DATASET_ID]["source_id"] = "other"
        with self.assertRaises(ValidationError):
            EarthSportResearch.model_validate(raw)

    def test_both_builders_roundtrip_complete_history_and_preserve_base(self):
        for world_id in ("fifa_earth", "atp_earth"):
            with self.subTest(world_id=world_id), tempfile.TemporaryDirectory() as d:
                base, output = Path(d) / "base", Path(d) / world_id
                WorldPackageCountryStore(base).replace_dataset(CountriesConfig(countries=[country()]))
                (base / "world.json").write_text(json.dumps({"world_id": "real_world"}))
                before = {str(p.relative_to(base)): p.read_bytes() for p in base.rglob("*") if p.is_file()}
                report = build_earth_package(
                    base_package=base,
                    bundle=research_bundle(
                        history({year: 7.4 for year in range(1955, 2027)}),
                        world_id,
                    ),
                    output=output,
                )
                self.assertTrue(report["coverage_complete"])
                self.assertEqual(len(WorldPackageCountryStore(output).load_country("AAA").rating_history.years), 72)
                self.assertTrue((output / "generation/country_rating_observation_datasets.json").is_file())
                self.assertEqual(before, {str(p.relative_to(base)): p.read_bytes() for p in base.rglob("*") if p.is_file()})
                with self.assertRaises(FileExistsError):
                    build_earth_package(
                        base_package=base,
                        bundle=research_bundle(history({1955: 3}), world_id),
                        output=output,
                    )

    def test_incomplete_research_never_creates_output(self):
        with tempfile.TemporaryDirectory() as d:
            base, output = Path(d) / "base", Path(d) / "fifa_earth"
            WorldPackageCountryStore(base).replace_dataset(CountriesConfig(countries=[country()]))
            with self.assertRaises(ValueError):
                build_earth_package(
                    base_package=base,
                    bundle=research_bundle(history({2000: 3})),
                    output=output,
                )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
