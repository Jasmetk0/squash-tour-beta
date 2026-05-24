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


def build_candidate_identity_contract(candidate_identity_summary: dict[str, object]) -> dict[str, object]:
    raw_candidate_count = candidate_identity_summary.get("candidate_count")
    candidate_count = raw_candidate_count if isinstance(raw_candidate_count, int) and raw_candidate_count >= 0 else 0

    duplicate_candidate_ids = candidate_identity_summary.get("duplicate_candidate_ids")
    duplicate_candidate_identity_keys = candidate_identity_summary.get("duplicate_candidate_identity_keys")

    has_duplicate_candidate_ids = isinstance(duplicate_candidate_ids, list) and bool(duplicate_candidate_ids)
    has_duplicate_candidate_identity_keys = isinstance(duplicate_candidate_identity_keys, list) and bool(duplicate_candidate_identity_keys)

    safe_for_future_reference = (
        candidate_count > 0
        and not has_duplicate_candidate_ids
        and not has_duplicate_candidate_identity_keys
    )

    if safe_for_future_reference:
        message = "Candidate identities are stable and safe for future reference."
    elif has_duplicate_candidate_ids or has_duplicate_candidate_identity_keys:
        message = "Candidate identities are deterministic but require review because duplicates were detected."
    else:
        message = "Candidate identities are unavailable for future reference because no candidates were generated."

    return {
        "identity_source": "season_template_slot",
        "id_strategy": "sanitized_template_slot_week",
        "key_strategy": "pipe_joined_sanitized_components",
        "key_components": [
            "target_season",
            "source_type",
            "source_template_id",
            "source_slot_id",
            "season_week_start",
            "event_name",
            "category",
            "source_template_ref",
        ],
        "candidate_count": candidate_count,
        "has_duplicate_candidate_ids": has_duplicate_candidate_ids,
        "has_duplicate_candidate_identity_keys": has_duplicate_candidate_identity_keys,
        "safe_for_future_reference": safe_for_future_reference,
        "read_only": True,
        "mutation_permitted": False,
        "message": message,
    }
