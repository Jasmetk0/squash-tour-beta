"""Loaders for tournament templates and season calendars."""

from __future__ import annotations

import json
from pathlib import Path

from beta_engine.domain.tournaments import SeasonCalendar, TournamentTemplatesConfig


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_tournament_templates_config(
    path: str | Path = "config/tournament_templates/mvp_templates.json",
) -> TournamentTemplatesConfig:
    return TournamentTemplatesConfig.model_validate(_load_json(path))


def load_season_calendar(
    path: str | Path = "config/calendar/season_2027.json",
    season: int | None = None,
) -> SeasonCalendar:
    requested_season = season
    if requested_season is not None:
        season_path = Path(f"config/calendar/season_{requested_season}.json")
        if season_path.exists():
            return SeasonCalendar.model_validate(_load_json(season_path))

    calendar = SeasonCalendar.model_validate(_load_json(path))
    if requested_season is None or calendar.season == requested_season:
        return calendar

    events = []
    for event in calendar.events:
        event_payload = event.model_dump()
        event_payload["season"] = requested_season
        event_payload["event_id"] = event.event_id.replace(str(calendar.season), str(requested_season), 1)
        events.append(event_payload)
    return SeasonCalendar.model_validate({"season": requested_season, "events": events})
