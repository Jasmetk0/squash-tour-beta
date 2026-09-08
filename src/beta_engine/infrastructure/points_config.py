"""Point-distribution config loader for ranking/race engines."""

from __future__ import annotations

import json
from pathlib import Path

from beta_engine.domain.rankings.points import (
    CANONICAL_RANKING_POINT_STAGES,
    LEGACY_POINT_STAGE_KEYS,
    normalize_ranking_points_table,
)

__all__ = [
    "CANONICAL_RANKING_POINT_STAGES", "LEGACY_POINT_STAGE_KEYS",
    "load_points_config", "normalize_ranking_points_table",
]


def load_points_config(path: str | Path = "config/points/mvp_points.json") -> dict[str, dict[str, int]]:
    with Path(path).open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    distributions = payload.get("point_distributions", {})
    if not isinstance(distributions, dict) or not distributions:
        raise ValueError("points config must contain non-empty point_distributions mapping")

    normalized: dict[str, dict[str, int]] = {}
    for distribution_ref, values in distributions.items():
        if not isinstance(values, dict):
            raise ValueError(f"point distribution {distribution_ref} must be an object")  # noqa: TRY004 - preserve loader error contract
        normalized[distribution_ref] = normalize_ranking_points_table(values)

    return normalized
