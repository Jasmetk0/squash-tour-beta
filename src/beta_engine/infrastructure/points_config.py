"""Point-distribution config loader for ranking/race engines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LEGACY_POINT_STAGE_KEYS = {
    "winner": "champion",
    "semifinalist": "semifinal",
    "quarterfinalist": "quarterfinal",
}


def normalize_ranking_points_table(values: dict[str, Any]) -> dict[str, int]:
    """Validate authored points and normalize legacy names at an input boundary."""
    normalized: dict[str, int] = {}
    for raw_key, value in values.items():
        key = LEGACY_POINT_STAGE_KEYS.get(str(raw_key), str(raw_key))
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"ranking point '{key}' must be an integer greater than or equal to zero")
        normalized[key] = value
    return normalized


def load_points_config(path: str | Path = "config/points/mvp_points.json") -> dict[str, dict[str, int]]:
    with Path(path).open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    distributions = payload.get("point_distributions", {})
    if not isinstance(distributions, dict) or not distributions:
        raise ValueError("points config must contain non-empty point_distributions mapping")

    normalized: dict[str, dict[str, int]] = {}
    for distribution_ref, values in distributions.items():
        if not isinstance(values, dict):
            raise ValueError(f"point distribution {distribution_ref} must be an object")
        normalized[distribution_ref] = normalize_ranking_points_table(values)

    return normalized
