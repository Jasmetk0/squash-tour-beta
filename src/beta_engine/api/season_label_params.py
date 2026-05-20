from __future__ import annotations

from fastapi import HTTPException, status

from beta_engine.domain.calendar.season_labels import normalize_season_label, to_long_season_label


def normalize_season_for_legacy_services(season: str) -> str:
    """Accept compact and legacy long season labels at API boundary.

    Existing legacy services/storage are still keyed by long YYYY/YYYY labels,
    so compact labels are converted to long format before service calls.
    """
    try:
        return to_long_season_label(normalize_season_label(season))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
