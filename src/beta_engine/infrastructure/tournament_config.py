"""Loaders for tournament templates and season calendars."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from beta_engine.domain.tournaments import SeasonCalendar, TournamentTemplatesConfig


def _load_json(path: str | Path, *, trusted_root: Path | None = None) -> dict:
    """Load a configuration file chosen by trusted application wiring.

    This is not a file browser for user-supplied HTTP paths. Optional custom
    paths remain supported for offline configuration validation and tests.
    """
    # Strings are accepted only for the shipping, application-owned configs.
    # Explicit Path overrides are reserved for trusted application wiring
    # (such as offline validation and isolated tests), not HTTP path inputs.
    if isinstance(path, str) and path not in {
        "config/tournament_templates/mvp_templates.json",
        "config/calendar/season_2027.json",
    }:
        raise ValueError("unrecognized configuration path")
    source = Path(path)
    if source.suffix.lower() != ".json" or ".." in source.parts:
        raise ValueError("configuration must be a regular JSON file without traversal")
    if any(component.is_symlink() for component in (source, *source.parents)):
        raise ValueError("configuration must be a regular JSON file, not a symlink")

    # Off-tree paths require a root supplied by trusted application wiring.
    # Check lexical containment BEFORE touching the requested file. Resolving
    # user-provided paths before containment checks itself performs filesystem
    # lookups and does not remove the dangerous input-to-open dependency.
    root = Path("config") if trusted_root is None else Path(trusted_root)
    if ".." in root.parts or any(component.is_symlink() for component in (root, *root.parents)):
        raise ValueError("configuration trusted root must not be a symlink or contain traversal")
    base = root.absolute()
    try:
        components = source.absolute().relative_to(base).parts
    except ValueError as exc:
        raise ValueError("configuration path must be within its trusted root") from exc
    if not components:
        raise ValueError("configuration must be a regular JSON file")

    # Select the actual filesystem entries from the trusted directory. Input
    # components are only used for equality checks, not passed to the opener.
    directory = base
    for component in components[:-1]:
        child = next((entry for entry in directory.iterdir() if entry.name == component), None)
        if child is None:
            raise FileNotFoundError(f"configuration file is unavailable: {source}")
        if child.is_symlink() or not child.is_dir():
            raise ValueError("configuration directory must not be a symlink")
        directory = child
    selected = next((entry for entry in directory.iterdir() if entry.name == components[-1]), None)
    if selected is None:
        raise FileNotFoundError(f"configuration file is unavailable: {source}")
    if selected.is_symlink():
        raise ValueError("configuration must be a regular JSON file, not a symlink")

    # O_NOFOLLOW guards the final entry against a link swap at open time.
    try:
        handle = os.open(selected, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"configuration file is unavailable: {source}") from exc
    try:
        if not stat.S_ISREG(os.fstat(handle).st_mode):
            raise ValueError("configuration must be a regular JSON file")
        with os.fdopen(handle, "r", encoding="utf-8") as fh:
            handle = -1
            return json.load(fh)
    finally:
        if handle != -1:
            os.close(handle)


def load_tournament_templates_config(
    path: str | Path = "config/tournament_templates/mvp_templates.json",
    *,
    trusted_root: Path | None = None,
) -> TournamentTemplatesConfig:
    return TournamentTemplatesConfig.model_validate(_load_json(path, trusted_root=trusted_root))


def load_season_calendar(
    path: str | Path = "config/calendar/season_2027.json",
    season: int | None = None,
    *,
    trusted_root: Path | None = None,
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

    calendar = SeasonCalendar.model_validate(_load_json(path, trusted_root=trusted_root))
    if requested_season is None or calendar.season == requested_season:
        return calendar

    events = []
    for event in calendar.events:
        event_payload = event.model_dump()
        event_payload["season"] = requested_season
        event_payload["event_id"] = event.event_id.replace(str(calendar.season), str(requested_season), 1)
        events.append(event_payload)
    return SeasonCalendar.model_validate({"season": requested_season, "events": events})
