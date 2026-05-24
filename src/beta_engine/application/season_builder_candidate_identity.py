from __future__ import annotations

import re
from collections import Counter


def sanitize_candidate_identity_part(value: object | None) -> str:
    raw = str(value or "")
    normalized = raw.strip().lower()
    if not normalized:
        return "unknown"
    sanitized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return sanitized or "unknown"


def build_candidate_identity(
    *,
    source_template_id: str | None,
    source_slot_id: str,
    season_week_start: int | None,
    target_season_label: str,
    source_type: str,
    event_name: str | None,
    category: str | None,
    source_template_ref: str | None,
) -> tuple[str, str]:
    candidate_id = "_".join(
        [
            "cand",
            sanitize_candidate_identity_part(source_template_id),
            sanitize_candidate_identity_part(source_slot_id),
            sanitize_candidate_identity_part(season_week_start),
        ]
    )
    candidate_identity_key = "|".join(
        [
            f"target_season={sanitize_candidate_identity_part(target_season_label)}",
            f"source_type={sanitize_candidate_identity_part(source_type)}",
            f"source_template_id={sanitize_candidate_identity_part(source_template_id)}",
            f"source_slot_id={sanitize_candidate_identity_part(source_slot_id)}",
            f"season_week_start={sanitize_candidate_identity_part(season_week_start)}",
            f"event_name={sanitize_candidate_identity_part(event_name)}",
            f"category={sanitize_candidate_identity_part(category)}",
            f"source_template_ref={sanitize_candidate_identity_part(source_template_ref)}",
        ]
    )
    return candidate_id, candidate_identity_key


def build_candidate_identity_summary(candidate_events: list[dict[str, object]]) -> dict[str, object]:
    candidate_ids = [str(candidate.get("candidate_id") or "") for candidate in candidate_events]
    candidate_identity_keys = [str(candidate.get("candidate_identity_key") or "") for candidate in candidate_events]

    duplicate_candidate_ids = sorted(
        [value for value, count in Counter(candidate_ids).items() if value and count > 1]
    )
    duplicate_candidate_identity_keys = sorted(
        [value for value, count in Counter(candidate_identity_keys).items() if value and count > 1]
    )

    return {
        "candidate_count": len(candidate_events),
        "candidate_ids": candidate_ids,
        "candidate_identity_keys": candidate_identity_keys,
        "duplicate_candidate_ids": duplicate_candidate_ids,
        "duplicate_candidate_identity_keys": duplicate_candidate_identity_keys,
        "read_only": True,
        "mutation_permitted": False,
        "message": "Candidate event identities are deterministic and read-only in dry-run.",
    }
