"""Curate canonical UEFA observations supporting the Faroe Islands 2006 anchor review.

Facts are transcribed from:
- UEFA "Developing football in the Faroe Islands" timeline/history page.
- UEFA "First division clubs in Europe 2005/06", Faroe Islands page 47,
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

HISTORY_SOURCE_ID = "uefa-faroe-history"
HISTORY_DATASET_ID = "uefa-faroe-history-events-v2"
HISTORY_URL = "https://www.uefa.com/nationalassociations/fro/"

DIRECTORY_SOURCE_ID = "uefa-first-division-clubs-2005-06"
DIRECTORY_DATASET_ID = "uefa-faroe-islands-2005-06-snapshot-v2"
DIRECTORY_URL = "https://www.uefa.com/newsfiles/332930.pdf"

DEFAULT_OUTPUT_DIR = Path("config/earth_research/observations/normalized")


def _event(
    *,
    local_id: str,
    year: int,
    text: str,
    locator: str,
    competition_scope: str,
    flags: list[str] | None = None,
) -> EarthObservation:
    return EarthObservation(
        observation_id=f"{HISTORY_DATASET_ID}#{local_id}",
        source_id=HISTORY_SOURCE_ID,
        source_entity="Faroe Islands Football Association history",
        earth_country_code="FRO",
        historical_entity="Faroe Islands",
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
        source_locator=locator,
        definition_notes=(
            "Official UEFA Faroe Islands association-history/timeline fact. "
            "This is factual context, not a direct 1-10 country rating."
        ),
        quality_flags=list(flags or []),
    )


def build_history_dataset() -> EarthObservationDataset:
    observations = [
        _event(
            local_id="1892-first-club",
            year=1892,
            text=(
                "UEFA timeline: the Faroe Islands' first club, "
                "Tvoroyrar Boltfelag TB, was established in 1892."
            ),
            locator="Timeline / Association history / 1892",
            competition_scope="institutional_history",
        ),
        _event(
            local_id="1942-first-official-championship",
            year=1942,
            text=(
                "UEFA timeline: the first official Faroese national championship "
                "took place in 1942."
            ),
            locator="Timeline / Association history / 1942",
            competition_scope="domestic_competition_history",
        ),
        _event(
            local_id="1955-first-cup",
            year=1955,
            text="UEFA timeline: the first Faroese Cup took place in 1955.",
            locator="Timeline / Association history / 1955",
            competition_scope="domestic_competition_history",
        ),
        _event(
            local_id="1979-fsf-formed-training-remit",
            year=1979,
            text=(
                "UEFA timeline: the Faroe Islands Football Association (FSF) was "
                "formed in 1979, taking charge of national tournaments and improved "
                "training conditions for coaches, officials and referees."
            ),
            locator="Timeline / Association history / 1979",
            competition_scope="association_governance_and_training",
        ),
        _event(
            local_id="1986-artificial-turf",
            year=1986,
            text=(
                "UEFA timeline: the FSF introduced artificial turf in 1986, a "
                "game-changing intervention that raised football's popularity as a "
                "participation sport."
            ),
            locator="Timeline / Association history / 1986",
            competition_scope="participation_infrastructure",
        ),
        _event(
            local_id="1990-uefa-membership",
            year=1990,
            text=(
                "UEFA timeline: after becoming a FIFA member in 1988, the FSF joined "
                "UEFA in 1990."
            ),
            locator="Timeline / Association history / 1990",
            competition_scope="international_affiliation",
        ),
        _event(
            local_id="1990-austria-qualifier-win",
            year=1990,
            text=(
                "UEFA timeline: the Faroe Islands beat Austria 1-0 in their first "
                "UEFA European Championship qualifier in 1990."
            ),
            locator="Timeline / National team history / 1990",
            competition_scope="senior_international_competition",
        ),
        _event(
            local_id="1999-torsvollur-opens",
            year=1999,
            text=(
                "UEFA timeline: the national stadium Torsvollur opened in Torshavn "
                "in 1999."
            ),
            locator="Timeline / Association history / 1999",
            competition_scope="elite_infrastructure",
        ),
    ]
    return EarthObservationDataset(
        dataset_id=HISTORY_DATASET_ID,
        source_id=HISTORY_SOURCE_ID,
        source_url=HISTORY_URL,
        source_document_sha256=None,
        input_artifact_sha256=None,
        generated_by="scripts/curate_fro_uefa_2006_observations.py",
        scope=(
            "Selected official UEFA Faroese football-history events needed for "
            "Faroe Islands 2006 rating provenance, from 1892 through 1999."
        ),
        limitations=(
            "Timeline events establish institutions, competition milestones and "
            "infrastructure but do not directly quantify coaching quality, league "
            "quality or elite-support services."
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
        source_entity="Faroe Islands",
        earth_country_code="FRO",
        historical_entity="Faroe Islands",
        observation_year=2005,
        measurement_type=measurement_type,
        sex_scope=sex_scope,
        age_scope=None,
        competition_scope="faroese_football_system_2005_06",
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
        source_page=47,
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
            local_id="amateur-adult-players",
            measurement_type="adult_amateur_players_reported",
            value=1785,
            unit="players",
            sex_scope="unknown",
            locator="Page 47 / Registered Players / Amateurs (over 18)",
            notes="UEFA directory reports 1,785 amateur registered players over age 18.",
        ),
        _directory_count(
            local_id="youth-players",
            measurement_type="youth_players_under_18_reported",
            value=2420,
            unit="players",
            sex_scope="unknown",
            locator="Page 47 / Registered Players / Youth (under 18)",
            notes="UEFA directory reports 2,420 registered youth players under age 18.",
        ),
        _directory_count(
            local_id="women-players",
            measurement_type="women_players_reported",
            value=258,
            unit="players",
            sex_scope="female",
            locator="Page 47 / Registered Players / Women",
            notes="UEFA directory reports 258 registered women players.",
        ),
        _directory_count(
            local_id="girls-players",
            measurement_type="girls_under_18_reported",
            value=1310,
            unit="players",
            sex_scope="female",
            locator="Page 47 / Registered Players / Girls (under 18)",
            notes="UEFA directory reports 1,310 registered girls under age 18.",
        ),
        _directory_count(
            local_id="clubs",
            measurement_type="clubs_reported",
            value=25,
            unit="clubs",
            sex_scope="not_applicable",
            locator="Page 47 / Clubs & Teams / Clubs",
            notes="UEFA directory reports 25 clubs in the Faroe Islands association.",
        ),
        _directory_count(
            local_id="teams",
            measurement_type="teams_reported",
            value=305,
            unit="teams",
            sex_scope="not_applicable",
            locator="Page 47 / Clubs & Teams / Teams",
            notes="UEFA directory reports 305 teams in the Faroe Islands association.",
        ),
        _directory_count(
            local_id="male-referees",
            measurement_type="male_referees_reported",
            value=136,
            unit="people",
            sex_scope="male",
            locator="Page 47 / Referees / Male",
            notes="UEFA directory reports 136 male referees.",
        ),
        _directory_count(
            local_id="female-referees",
            measurement_type="female_referees_reported",
            value=1,
            unit="people",
            sex_scope="female",
            locator="Page 47 / Referees / Female",
            notes="UEFA directory reports one female referee.",
        ),
        _directory_count(
            local_id="top-division-clubs",
            measurement_type="top_division_clubs_reported",
            value=10,
            unit="clubs",
            sex_scope="not_applicable",
            locator="Page 47 / Domestic Competitions 2004 / League Table positions 1-10",
            notes=(
                "The published 2004 Faroese league table contains ten positions/clubs. "
                "This is competition-structure evidence, not a direct league-quality score."
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
        generated_by="scripts/curate_fro_uefa_2006_observations.py",
        scope=(
            "Faroe Islands facts from UEFA First division clubs in Europe 2005/06, "
            "page 47: registered-player categories, clubs/teams, referees and "
            "2004 top-division size."
        ),
        limitations=(
            "UEFA prints '-' for non-amateur/professional players; no numeric "
            "professional-player observation is created and missing is not converted "
            "to zero. Counts describe system scale/structure rather than direct "
            "quality of coaching, competition or elite support."
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
        HISTORY_DATASET_ID: "uefa_faroe_history_events_v2.json",
        DIRECTORY_DATASET_ID: "uefa_faroe_islands_2005_06_snapshot_v2.json",
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
        HISTORY_DATASET_ID: "uefa_faroe_history_events_v2.json",
        DIRECTORY_DATASET_ID: "uefa_faroe_islands_2005_06_snapshot_v2.json",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for dataset_id, dataset in datasets.items():
        (args.output_dir / filenames[dataset_id]).write_text(
            json.dumps(dataset.model_dump(mode="json"), indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

    print(
        json.dumps(
            {
                dataset_id: {
                    "record_count": manifests[dataset_id].record_count,
                    "sha256": manifests[dataset_id].sha256,
                }
                for dataset_id in datasets
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
