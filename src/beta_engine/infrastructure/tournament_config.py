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
) -> SeasonCalendar:
    return SeasonCalendar.model_validate(_load_json(path))
