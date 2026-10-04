"""Curate canonical UEFA observations supporting the Czechia 2006 anchor review.

Facts are transcribed from:
- UEFA "Developing football in Czechia" timeline/history page.
- UEFA "First division clubs in Europe 2005/06", Czech Republic page 36,
  information updated 20 July 2005.

This curation does not assign game ratings.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from beta_engine.application.earth_research_observations import (
    EarthObservation,
    EarthObservationDataset,
    EarthObservationDatasetManifest,
    observation_dataset_sha256,
)

HISTORY_SOURCE_ID = "uefa-czechia-history"
HISTORY_DATASET_ID = "uefa-czechia-history-events-v2"
HISTORY_URL = (
    "https://www.uefa.com/news-media/news/0282-1830fd7e681b-"
    "d29c43b082a6-1000--developing-football-in-czechia/"
)

DIRECTORY_SOURCE_ID = "uefa-first-division-clubs-2005-06"
DIRECTORY_DATASET_ID = "uefa-czech-republic-2005-06-snapshot-v2"
DIRECTORY_URL = "https://www.uefa.com/newsfiles/332930.pdf"

DEFAULT_OUTPUT_DIR = Path("config/earth_research/observations/normalized")


def _event(
    *,
    local_id: str,
    year: int,
    text: str,
    locator: str,
    historical_entity: str,
    competition_scope: str,
    flags: list[str] | None = None,
) -> EarthObservation:
    return EarthObservation(
        observation_id=f"{HISTORY_DATASET_ID}#{local_id}",
        source_id=HISTORY_SOURCE_ID,
        source_entity="Czechia / Czech football association history",
        earth_country_code="CZE",
        historical_entity=historical_entity,
        observation_year=year,
        measurement_type="structural_event",
        sex_scope="not_applicable",
        age_scope=None,
        competition_scope=competition_scope,
        text_value=text,
        unit="event",
        collection_method="published_table",
        coverage_scope="association",
        comparability_group=None,
        cross_country_comparable=False,
        is_direct_observation=True,
        is_statistically_modelled=False,
        territory_mapping_method=(
            "UEFA current-association timeline explicitly records predecessor/"
            "Czech-land institutional history."
            if year < 1993
            else None
        ),
        source_locator=locator,
        definition_notes=(
            "Official UEFA association-history/timeline fact. This is a factual "
            "structural/result observation, not a direct 1-10 country rating."
        ),
        quality_flags=list(flags or []),
    )


def build_history_dataset() -> EarthObservationDataset:
    observations = [
        _event(
            local_id="1892-first-prague-club",
            year=1892,
            text="UEFA timeline: Prague's first club, SK Slavia Praha, was founded in 1892.",
            locator="Timeline / Association history / 1892",
            historical_entity="Czech lands in Austria-Hungary",
            competition_scope="institutional_history",
            flags=["predecessor_territory_context"],
        ),
        _event(
            local_id="1901-czech-football-association",
            year=1901,
            text="UEFA timeline: thirteen clubs united in 1901 to form the Czech Football Association.",
            locator="Timeline / Association history / 1901",
            historical_entity="Czech lands in Austria-Hungary",
            competition_scope="institutional_history",
            flags=["predecessor_territory_context"],
        ),
        _event(
            local_id="1954-uefa-founder-member",
            year=1954,
            text="UEFA timeline lists 1954 as the association's UEFA founder-member milestone.",
            locator="Timeline / Association history / 1954",
            historical_entity="Czechoslovakia - Czech lands",
            competition_scope="institutional_history",
            flags=["predecessor_institution_context"],
        ),
        _event(
            local_id="1993-independent-czech-era",
            year=1993,
            text="UEFA states that after the peaceful division of Czechoslovakia in 1993, the Czech association began writing its own football history.",
            locator="Timeline / 1993 independent Czech era",
            historical_entity="Czech Republic",
            competition_scope="institutional_history",
        ),
        _event(
            local_id="1996-euro-runner-up",
            year=1996,
            text="Czech Republic finished runners-up at UEFA EURO 1996.",
            locator="Timeline / National team history / 1996",
            historical_entity="Czech Republic",
            competition_scope="senior_international_competition",
        ),
        _event(
            local_id="2002-u21-european-champion",
            year=2002,
            text="Czech Republic won the UEFA European Under-21 Championship in 2002.",
            locator="Timeline / National team history / 2002",
            historical_entity="Czech Republic",
            competition_scope="mens_under_21_international_competition",
        ),
        _event(
            local_id="2004-euro-semi-final",
            year=2004,
            text="Czech Republic reached the UEFA EURO 2004 semi-finals.",
            locator="Timeline / National team history / 2004",
            historical_entity="Czech Republic",
            competition_scope="senior_international_competition",
        ),
    ]
    return EarthObservationDataset(
        dataset_id=HISTORY_DATASET_ID,
        source_id=HISTORY_SOURCE_ID,
        source_url=HISTORY_URL,
        source_document_sha256=None,
        input_artifact_sha256=None,
        generated_by="scripts/curate_cze_uefa_2006_observations.py",
        scope=(
            "Selected official UEFA Czech association-history events needed for "
            "Czechia rating provenance, from institutional roots through 2004."
        ),
        limitations=(
            "Timeline events establish institutions/results but do not directly "
            "measure popularity, access, coaching quality or elite-support quality. "
            "Pre-1993 entries are predecessor/Czech-land context and must not be "
            "treated as duplicated independent Czech national totals."
        ),
        observations=observations,
    )


def _directory_count(
    *,
    local_id: str,
    measurement_type: str,
    value: int,
    unit: str,
    sex_scope: str,
    locator: str,
    notes: str,
    comparable: bool = True,
) -> EarthObservation:
    return EarthObservation(
        observation_id=f"{DIRECTORY_DATASET_ID}#{local_id}",
        source_id=DIRECTORY_SOURCE_ID,
        source_entity="Czech Republic",
        earth_country_code="CZE",
        historical_entity="Czech Republic",
        observation_year=2005,
        measurement_type=measurement_type,
        sex_scope=sex_scope,
        age_scope=None,
        competition_scope="czech_football_system_2005_06",
        numeric_value=value,
        unit=unit,
        collection_method="published_table",
        coverage_scope="association",
        comparability_group=(
            f"uefa-first-division-clubs-2005-06:{measurement_type}"
            if comparable
            else None
        ),
        cross_country_comparable=comparable,
        is_direct_observation=True,
        is_statistically_modelled=False,
        source_page=36,
        source_locator=locator,
        definition_notes=notes,
        quality_flags=[
            "publication_updated_2005-07-20",
            "pre_anchor_2006_institutional_snapshot",
        ],
    )


def build_directory_dataset() -> EarthObservationDataset:
    observations = [
        _directory_count(
            local_id="professional-non-amateur-players",
            measurement_type="professional_non_amateur_players_reported",
            value=1576,
            unit="players",
            sex_scope="unknown",
            locator="Page 36 / Facts & Figures / Registered Players / Non-amateurs (professionals)",
            notes=(
                "UEFA directory reports 1,576 non-amateur (professional) registered "
                "players. The category is reproduced as published; sex scope is not "
                "made more specific than the source explicitly supports."
            ),
        ),
        _directory_count(
            local_id="amateur-adult-players",
            measurement_type="adult_amateur_players_reported",
            value=377244,
            unit="players",
            sex_scope="unknown",
            locator="Page 36 / Facts & Figures / Registered Players / Amateurs (over 18)",
            notes="UEFA directory reports 377,244 amateur registered players over age 18.",
        ),
        _directory_count(
            local_id="youth-players",
            measurement_type="youth_players_under_18_reported",
            value=229457,
            unit="players",
            sex_scope="unknown",
            locator="Page 36 / Facts & Figures / Registered Players / Youth (under 18)",
            notes="UEFA directory reports 229,457 registered youth players under age 18.",
        ),
        _directory_count(
            local_id="clubs",
            measurement_type="clubs_reported",
            value=3955,
            unit="clubs",
            sex_scope="not_applicable",
            locator="Page 36 / Facts & Figures / Clubs & Teams / Clubs",
            notes="UEFA directory reports 3,955 clubs for the Czech association.",
        ),
        _directory_count(
            local_id="teams",
            measurement_type="teams_reported",
            value=15378,
            unit="teams",
            sex_scope="not_applicable",
            locator="Page 36 / Facts & Figures / Clubs & Teams / Teams",
            notes="UEFA directory reports 15,378 teams for the Czech association.",
        ),
        _directory_count(
            local_id="male-referees",
            measurement_type="male_referees_reported",
            value=3837,
            unit="people",
            sex_scope="male",
            locator="Page 36 / Facts & Figures / Referees / Male",
            notes="UEFA directory reports 3,837 male referees.",
        ),
        _directory_count(
            local_id="female-referees",
            measurement_type="female_referees_reported",
            value=51,
            unit="people",
            sex_scope="female",
            locator="Page 36 / Facts & Figures / Referees / Female",
            notes="UEFA directory reports 51 female referees.",
        ),
        _directory_count(
            local_id="top-division-clubs",
            measurement_type="top_division_clubs_reported",
            value=16,
            unit="clubs",
            sex_scope="not_applicable",
            locator="Page 36 / Domestic Competitions 2004/05 / League Table positions 1-16",
            notes=(
                "The published 2004/05 Czech top-division league table contains "
                "16 positions/clubs. This is competition-structure evidence, not a "
                "direct measure of league quality."
            ),
            comparable=False,
        ),
    ]
    return EarthObservationDataset(
        dataset_id=DIRECTORY_DATASET_ID,
        source_id=DIRECTORY_SOURCE_ID,
        source_url=DIRECTORY_URL,
        source_document_sha256=None,
        input_artifact_sha256=None,
        generated_by="scripts/curate_cze_uefa_2006_observations.py",
        scope=(
            "Czech Republic association facts from UEFA First division clubs in "
            "Europe 2005/06, page 36, including registered-player categories, "
            "clubs/teams, referees and 2004/05 top-division size."
        ),
        limitations=(
            "This is a 2005 UEFA directory snapshot immediately preceding the 2006 "
            "rating checkpoint. Counts describe system scale/structure; they do not "
            "directly measure coaching quality, competition quality or elite-support "
            "quality. Published category definitions are preserved rather than "
            "reinterpreted."
        ),
        observations=observations,
    )


def build_datasets() -> dict[str, EarthObservationDataset]:
    return {
        HISTORY_DATASET_ID: build_history_dataset(),
        DIRECTORY_DATASET_ID: build_directory_dataset(),
    }


def build_manifests(
    datasets: dict[str, EarthObservationDataset],
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, EarthObservationDatasetManifest]:
    filenames = {
        HISTORY_DATASET_ID: "uefa_czechia_history_events_v2.json",
        DIRECTORY_DATASET_ID: "uefa_czech_republic_2005_06_snapshot_v2.json",
    }
    manifests: dict[str, EarthObservationDatasetManifest] = {}
    for dataset_id, dataset in datasets.items():
        output = output_dir / filenames[dataset_id]
        relative = output.relative_to(Path("config/earth_research"))
        manifests[dataset_id] = EarthObservationDatasetManifest(
            dataset_id=dataset_id,
            source_id=dataset.source_id,
            relative_path=relative.as_posix(),
            sha256=observation_dataset_sha256(dataset),
            record_count=len(dataset.observations),
            source_document_sha256=dataset.source_document_sha256,
            input_artifact_sha256=dataset.input_artifact_sha256,
            generated_by=dataset.generated_by,
        )
    return manifests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-output", type=Path)
    args = parser.parse_args()

    datasets = build_datasets()
    manifests = build_manifests(datasets, output_dir=args.output_dir)
    filenames = {
        HISTORY_DATASET_ID: "uefa_czechia_history_events_v2.json",
        DIRECTORY_DATASET_ID: "uefa_czech_republic_2005_06_snapshot_v2.json",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for dataset_id, dataset in datasets.items():
        (args.output_dir / filenames[dataset_id]).write_text(
            json.dumps(dataset.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

    summary = {
        dataset_id: {
            "record_count": manifests[dataset_id].record_count,
            "sha256": manifests[dataset_id].sha256,
        }
        for dataset_id in datasets
    }
    print(json.dumps(summary, indent=2))

    if args.manifest_output:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_text(
            json.dumps(
                {
                    dataset_id: manifest.model_dump(mode="json")
                    for dataset_id, manifest in manifests.items()
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
