"""Point-distribution config loader for ranking/race engines."""

from __future__ import annotations

import json
from pathlib import Path


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
        normalized[distribution_ref] = {str(k): max(0, int(v)) for k, v in values.items()}

    return normalized
