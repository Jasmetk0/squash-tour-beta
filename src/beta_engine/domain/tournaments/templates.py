"""Utilities for validating template/calendar compatibility."""

from __future__ import annotations

from beta_engine.domain.tournaments.models import SeasonCalendar, TournamentTemplatesConfig


def validate_calendar_template_references(
    templates_config: TournamentTemplatesConfig,
    calendar: SeasonCalendar,
) -> None:
    """Ensure every calendar event references an existing template id."""

    template_ids = {template.template_id for template in templates_config.templates}
    missing = sorted({event.template_id for event in calendar.events if event.template_id not in template_ids})
    if missing:
        missing_csv = ", ".join(missing)
        raise ValueError(f"Calendar references unknown template ids: {missing_csv}")
