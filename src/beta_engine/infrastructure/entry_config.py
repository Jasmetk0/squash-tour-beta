"""Loaders for entry/acceptance tuning config."""

from __future__ import annotations

import json
from pathlib import Path

from beta_engine.domain.entries import EntryTuningConfig


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_entry_tuning_config(path: str | Path = "config/balance/entry_tuning.json") -> EntryTuningConfig:
    return EntryTuningConfig.model_validate(_load_json(path))
