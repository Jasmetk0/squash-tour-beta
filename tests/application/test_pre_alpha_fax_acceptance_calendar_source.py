from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from beta_engine.application.pre_alpha_fax_acceptance_calendar_source import (
    PRE_ALPHA_FAX_ACCEPTANCE_EDITION_COUNT,
    PRE_ALPHA_FAX_ACCEPTANCE_SEASON,
    PreAlphaFaxAcceptanceCalendarSource,
)
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_category_points_service import (
    SeasonCategoryPointsService,
)
from beta_engine.application.tournament_templates_service import (
    TournamentTemplatesConfigService,
)


def _source(tmp_path: Path) -> PreAlphaFaxAcceptanceCalendarSource:
    templates = TournamentTemplatesConfigService(
        config_path=Path("config/tournament_templates/mvp_templates.json")
    )
    return PreAlphaFaxAcceptanceCalendarSource(
        template_service=templates,
        calendar_validation_service=SeasonCalendarService(
            template_service=templates,
            category_points_service=SeasonCategoryPointsService(
                templates, registry_path=tmp_path / "category-points.json"
            ),
        ),
    )


@pytest.mark.pr_critical
def test_pre_alpha_fax_acceptance_calendar_builds_exact_deterministic_80_world_tour_editions(tmp_path) -> None:
    source = _source(tmp_path)
    first = source.build_calendar(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)
    second = source.build_calendar(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)

    assert len(first.events) == PRE_ALPHA_FAX_ACCEPTANCE_EDITION_COUNT == 80
    assert all(event.tour_level == "WORLD_TOUR" for event in first.events)
    assert all(event.is_world_tour is True for event in first.events)
    assert all(event.is_elite_tour is False for event in first.events)
    assert len({event.event_id for event in first.events}) == 80
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.metadata is not None
    assert first.metadata.event_count == 80
    assert len(first.metadata.build_fingerprint or "") == 64
    assert first.validation_errors == []

    counts = Counter(event.season_week for event in first.events)
    assert min(counts) == 1
    assert max(counts) == 61
    assert set(counts.values()) <= {1, 2}
    assert sum(counts.values()) == 80


@pytest.mark.pr_critical
def test_pre_alpha_fax_acceptance_calendar_preserves_existing_world_tour_template_geometry(tmp_path) -> None:
    source = _source(tmp_path)
    templates = {
        template.template_id: template
        for template in source.template_service.list_templates()
        if template.active and template.tour_level == "WORLD_TOUR"
    }
    calendar = source.build_calendar(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)

    assert {event.template_id for event in calendar.events} == set(templates)
    for event in calendar.events:
        template = templates[event.template_id]
        assert event.category == template.category
        assert event.host_country == template.host_country
        assert event.region == template.region
        assert event.main_draw_size == template.main_draw_size
        assert event.qualification_draw_size == template.qualification_draw_size
        assert event.seeds_count == template.seeds_count
        assert event.qualifier_spots == template.qualifier_spots
        assert event.wild_cards == template.wild_cards
        assert event.byes == template.byes
        assert event.point_distribution_ref == template.point_distribution_ref
        assert event.duration_in_season_weeks == template.duration_in_season_weeks
        assert event.template_snapshot == template.model_dump(mode="json")
        assert event.event_level_overrides["pre_alpha_release_fixture"] is True


@pytest.mark.pr_critical
def test_pre_alpha_fax_acceptance_calendar_package_is_replay_stable_and_explicitly_non_canonical(tmp_path) -> None:
    source = _source(tmp_path)
    first = source.build_document(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)
    second = source.build_document(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)

    assert first.package_id == "calendar-2000-2001"
    assert first.source_fingerprint == second.source_fingerprint
    assert first.provenance["adapter"] == "pre_alpha_fax_acceptance_calendar.v1"
    assert first.provenance["non_canonical_release_fixture"] is True
    event_entities = [
        entity
        for entity in first.entities
        if entity.entity_kind == "calendar.event.v1"
    ]
    assert len(event_entities) == 80


def test_pre_alpha_fax_acceptance_calendar_rejects_other_seasons(tmp_path) -> None:
    with pytest.raises(ValueError, match="only for 2000/2001"):
        _source(tmp_path).build_document("2001/2002")


def test_reference_snapshots_authored_points_without_writing_or_inventing_awards(tmp_path):
    source = _source(tmp_path)
    points = source.calendar_validation_service.category_points_service
    candidate = points.preview_initialization(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)
    tables = {row.category: row.ranking_points_table for row in candidate.categories}
    first = source.build_calendar()
    for event in first.events:
        assert event.ranking_points_table == tables[event.category]
        assert not event.points_table_complete
        assert "qualification_winner" not in event.ranking_points_table
    assert not points.registry_path.exists()

    points.initialize(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)
    # Explicit disposable test configuration, not newly decided FAX canon.
    for category, table in tables.items():
        required = {
            stage for event in first.events if event.category == category
            for stage in event.required_ranking_point_stages
        }
        points.update(PRE_ALPHA_FAX_ACCEPTANCE_SEASON, category, {
            **table, **{stage: 0 for stage in required if stage not in table},
        })
    before = points.registry_path.read_bytes()
    complete = source.build_calendar()
    assert all(event.points_table_complete for event in complete.events)
    assert all(event.ranking_points_table["qualification_winner"] == 0 for event in complete.events)
    assert points.registry_path.read_bytes() == before
    assert complete.metadata.build_fingerprint != first.metadata.build_fingerprint
    document = source.build_document(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)
    original_table = dict(complete.events[0].ranking_points_table)
    points.update(PRE_ALPHA_FAX_ACCEPTANCE_SEASON, complete.events[0].category, {"champion": 1})
    assert complete.events[0].ranking_points_table == original_table
    assert source.build_document(PRE_ALPHA_FAX_ACCEPTANCE_SEASON).source_fingerprint != document.source_fingerprint


def test_reference_calendar_requires_points_authority(tmp_path):
    source = _source(tmp_path)
    source.calendar_validation_service.category_points_service = None
    with pytest.raises(ValueError, match="Points authority is unavailable"):
        source.build_calendar()
