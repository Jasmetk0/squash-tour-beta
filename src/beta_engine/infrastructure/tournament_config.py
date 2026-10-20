"""Loaders for tournament templates and season calendars."""

from __future__ import annotations

import json
from pathlib import Path

from beta_engine.domain.tournaments import SeasonCalendar, TournamentTemplatesConfig


def _load_json(path: str | Path) -> dict:
    """Load a configuration file chosen by trusted application wiring.

    This is not a file browser for user-supplied HTTP paths. Optional custom
    paths remain supported for offline configuration validation and tests.
    """
    source = Path(path)
    # These paths are configured by application wiring, not selected by an
    # HTTP client. Still reject traversal and redirection at every level.
    if source.suffix.lower() != ".json" or ".." in source.parts:
        raise ValueError("configuration must be a regular JSON file without traversal")
    if any(component.is_symlink() for component in (source, *source.parents)):
        raise ValueError("configuration must be a regular JSON file, not a symlink")
    if not source.is_file():
        raise FileNotFoundError(f"configuration file is unavailable: {source}")
    with source.open("r", encoding="utf-8") as fh:
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
    # A season is an integer selector, never a pathname component from a string.
    if requested_season is not None and (
        type(requested_season) is not int or not 1 <= requested_season <= 9999
    ):
        raise ValueError("season must be an integer between 1 and 9999")
    if requested_season is not None:
        season_path = Path("config/calendar") / f"season_{requested_season:d}.json"
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
