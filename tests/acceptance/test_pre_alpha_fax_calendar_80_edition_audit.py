from pathlib import Path
from unittest.mock import patch

import pytest

from beta_engine.application.pre_alpha_fax_acceptance_calendar_source import (
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

pytestmark = pytest.mark.pr_critical

@pytest.fixture
def calendar_source(tmp_path: Path) -> PreAlphaFaxAcceptanceCalendarSource:
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

def test_audit_exact_80_planned_editions(calendar_source: PreAlphaFaxAcceptanceCalendarSource) -> None:
    calendar = calendar_source.build_calendar(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)

    # Verify counts
    assert len(calendar.events) == 80, "Calendar must produce exactly 80 editions"

    # Audit statuses (planned vs completed/played)
    for event in calendar.events:
        assert event.status == "planned", f"Event {event.event_id} is not 'planned' (created 80 vs actual played 80)"
        assert event.event_level_overrides.get("pre_alpha_release_fixture") is True, f"Event {event.event_id} missing fixture flag"

    # Verify identities and calendar affiliation
    event_ids = [e.event_id for e in calendar.events]
    assert len(set(event_ids)) == 80, "Edition identities must be unique"
    for event in calendar.events:
        assert event.season == PRE_ALPHA_FAX_ACCEPTANCE_SEASON, "Must be affiliated with the correct season"

    # Validate dates (season week placement)
    # The requirement says to distribute the 80 editions evenly so no season week has more than two.
    # We should verify that season_week is between 1 and 61 (which matches PRE_ALPHA_FAX_ACCEPTANCE_SEASON_WEEKS)
    season_weeks = [e.season_week for e in calendar.events]
    assert all(1 <= sw <= 61 for sw in season_weeks), "All events must be scheduled between SW1 and SW61"

    # Count frequency of each season week to ensure no more than 2 events per week
    from collections import Counter
    week_counts = Counter(season_weeks)
    assert all(count <= 2 for count in week_counts.values()), "No season week should have more than 2 reference events"

def test_audit_damaged_inputs(calendar_source: PreAlphaFaxAcceptanceCalendarSource) -> None:
    # Attempting to request a different season
    with pytest.raises(ValueError, match="only for 2000/2001"):
        calendar_source.build_calendar("2001/2002")

    # Verify rejection when underlying templates are missing or damaged
    with (
        patch("beta_engine.application.tournament_templates_service.TournamentTemplatesConfigService.list_templates", return_value=[]),
        pytest.raises(ValueError, match="requires at least one active WORLD_TOUR template"),
    ):
        calendar_source.build_calendar(PRE_ALPHA_FAX_ACCEPTANCE_SEASON)
