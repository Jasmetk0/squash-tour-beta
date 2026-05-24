"""Deterministic candidate identity helpers for Season Builder dry-run previews.

This module builds read-only candidate identity metadata used for dry-run diagnostics.
It does not mutate state, create/apply events, or decide whether apply/build commands are
allowed. ``safe_for_future_reference`` only indicates candidate IDs/keys are non-empty and
free of duplicates; it is not mutation permission.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter


def sanitize_candidate_identity_part(value: object | None) -> str:
    """Normalize a value into a stable low-risk identity segment."""
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
    """Build deterministic candidate_id and candidate_identity_key values."""
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
    """Summarize candidate IDs/keys and duplicate diagnostics for dry-run output."""
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
    """Describe identity readiness for reference, never mutation permission."""
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


def build_candidate_identity_overview(
    candidate_identity_summary: dict[str, object],
    candidate_identity_contract: dict[str, object],
) -> dict[str, object]:
    """Build compact read-only overview derived from summary + contract."""
    raw_summary_count = candidate_identity_summary.get("candidate_count")
    raw_contract_count = candidate_identity_contract.get("candidate_count")
    candidate_count = 0
    if isinstance(raw_summary_count, int) and raw_summary_count >= 0:
        candidate_count = raw_summary_count
    elif isinstance(raw_contract_count, int) and raw_contract_count >= 0:
        candidate_count = raw_contract_count

    available = candidate_count > 0
    safe_for_future_reference = (
        candidate_identity_contract.get("safe_for_future_reference")
        if isinstance(candidate_identity_contract.get("safe_for_future_reference"), bool)
        else False
    )
    has_duplicate_candidate_ids = (
        candidate_identity_contract.get("has_duplicate_candidate_ids")
        if isinstance(candidate_identity_contract.get("has_duplicate_candidate_ids"), bool)
        else False
    )
    has_duplicate_candidate_identity_keys = (
        candidate_identity_contract.get("has_duplicate_candidate_identity_keys")
        if isinstance(candidate_identity_contract.get("has_duplicate_candidate_identity_keys"), bool)
        else False
    )

    identity_source = candidate_identity_contract.get("identity_source")
    id_strategy = candidate_identity_contract.get("id_strategy")
    key_strategy = candidate_identity_contract.get("key_strategy")
    normalized_identity_source = identity_source.strip() if isinstance(identity_source, str) and identity_source.strip() else "n/a"
    normalized_id_strategy = id_strategy.strip() if isinstance(id_strategy, str) and id_strategy.strip() else "n/a"
    normalized_key_strategy = key_strategy.strip() if isinstance(key_strategy, str) and key_strategy.strip() else "n/a"

    has_duplicates = has_duplicate_candidate_ids or has_duplicate_candidate_identity_keys
    if safe_for_future_reference:
        message = "Candidate identity overview: safe for future reference."
    elif available and has_duplicates:
        message = "Candidate identity overview: candidates generated but duplicate identities require review."
    elif available:
        message = "Candidate identity overview: candidates generated but not safe for future reference."
    else:
        message = "Candidate identity overview: no candidates generated."

    return {
        "available": available,
        "candidate_count": candidate_count,
        "safe_for_future_reference": safe_for_future_reference,
        "has_duplicate_candidate_ids": has_duplicate_candidate_ids,
        "has_duplicate_candidate_identity_keys": has_duplicate_candidate_identity_keys,
        "identity_source": normalized_identity_source,
        "id_strategy": normalized_id_strategy,
        "key_strategy": normalized_key_strategy,
        "read_only": True,
        "mutation_permitted": False,
        "message": message,
    }


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    if not all(isinstance(item, str) for item in value):
        return []
    return list(value)


def build_candidate_identity_fingerprint(
    *,
    target_season_label: str | None,
    source_type: str | None,
    source_template_id: str | None,
    candidate_identity_summary: dict[str, object],
    candidate_identity_contract: dict[str, object],
) -> dict[str, object]:
    """Build deterministic read-only fingerprint metadata for candidate identity sets."""
    candidate_ids = _as_string_list(candidate_identity_summary.get("candidate_ids"))
    candidate_identity_keys = _as_string_list(candidate_identity_summary.get("candidate_identity_keys"))

    raw_candidate_count = candidate_identity_summary.get("candidate_count")
    candidate_count = raw_candidate_count if isinstance(raw_candidate_count, int) and raw_candidate_count >= 0 else len(candidate_ids)

    raw_safe = candidate_identity_contract.get("safe_for_future_reference")
    safe_for_future_reference = raw_safe if isinstance(raw_safe, bool) else False

    payload_version = 1
    payload = {
        "candidate_count": candidate_count,
        "candidate_ids": candidate_ids,
        "candidate_identity_keys": candidate_identity_keys,
        "safe_for_future_reference": safe_for_future_reference,
        "source_template_id": source_template_id,
        "source_type": source_type,
        "target_season_label": target_season_label,
        "version": payload_version,
    }
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    return {
        "fingerprint": fingerprint,
        "fingerprint_algorithm": "sha256",
        "fingerprint_payload_version": payload_version,
        "candidate_count": candidate_count,
        "candidate_ids": candidate_ids,
        "candidate_identity_keys": candidate_identity_keys,
        "safe_for_future_reference": safe_for_future_reference,
        "target_season_label": target_season_label,
        "source_type": source_type,
        "source_template_id": source_template_id,
        "read_only": True,
        "mutation_permitted": False,
        "message": "Candidate identity fingerprint is deterministic and read-only.",
    }


def build_candidate_identity_review_reference(
    candidate_identity_fingerprint: dict[str, object],
) -> dict[str, object]:
    """Build read-only review reference metadata from a fingerprint payload."""
    raw_reference_id = candidate_identity_fingerprint.get("fingerprint")
    reference_id = raw_reference_id if isinstance(raw_reference_id, str) and raw_reference_id else ""

    raw_count = candidate_identity_fingerprint.get("candidate_count")
    candidate_count = raw_count if isinstance(raw_count, int) and raw_count >= 0 else 0

    raw_safe = candidate_identity_fingerprint.get("safe_for_future_reference")
    safe_for_future_reference = raw_safe if isinstance(raw_safe, bool) else False

    can_reference_future_apply = bool(reference_id) and safe_for_future_reference and candidate_count > 0

    message = (
        "Candidate identity set can be referenced by a future audited apply flow."
        if can_reference_future_apply
        else "Candidate identity set cannot be referenced by a future apply flow yet."
    )

    return {
        "reference_type": "candidate_identity_set",
        "reference_id": reference_id,
        "fingerprint_algorithm": "sha256",
        "fingerprint_payload_version": 1,
        "candidate_count": candidate_count,
        "safe_for_future_reference": safe_for_future_reference,
        "can_reference_future_apply": can_reference_future_apply,
        "read_only": True,
        "mutation_permitted": False,
        "message": message,
    }


def build_future_apply_reference_contract(
    *,
    candidate_identity_fingerprint: dict,
    candidate_identity_review_reference: dict,
    identity_readiness: dict,
) -> dict:
    """Build a preview/readiness contract for future-apply identity references.

    Safety invariant:
    - This helper is documentation/preview metadata only.
    - It never executes an apply command.
    - It never grants mutation permission.
    - ``available=True`` only means the identity reference values are present and
      structurally referenceable for a *future* command pathway.
    - ``apply_execution_enabled`` must remain ``False`` in this phase.
    """
    raw_reference_id = candidate_identity_review_reference.get("reference_id")
    reference_id = raw_reference_id if isinstance(raw_reference_id, str) and raw_reference_id else ""

    raw_reference_type = candidate_identity_review_reference.get("reference_type")
    reference_type = raw_reference_type if isinstance(raw_reference_type, str) and raw_reference_type else "candidate_identity_set"

    raw_can_reference_apply = candidate_identity_review_reference.get("can_reference_future_apply")
    can_reference_apply = raw_can_reference_apply if isinstance(raw_can_reference_apply, bool) else False

    raw_fingerprint = candidate_identity_fingerprint.get("fingerprint")
    fingerprint = raw_fingerprint if isinstance(raw_fingerprint, str) and raw_fingerprint else ""

    future_command_reference = identity_readiness.get("future_command_reference")
    if not isinstance(future_command_reference, dict):
        future_command_reference = {}
    raw_main_ready = future_command_reference.get("can_reference_future_command")
    main_future_command_reference_ready = raw_main_ready if isinstance(raw_main_ready, bool) else False

    available = bool(reference_id) and can_reference_apply and bool(fingerprint)

    message = (
        "Future apply reference contract is preview-only and disabled; it is read-only and does not execute apply."
        if available
        else "Future apply reference contract is preview-only and disabled; reference requirements are incomplete and apply execution remains unavailable."
    )

    return {
        "available": available,
        "contract_type": "future_apply_reference_contract",
        "candidate_identity_reference_type": reference_type,
        "candidate_identity_reference_id": reference_id,
        "candidate_identity_fingerprint": fingerprint,
        "candidate_identity_set_referenceable": can_reference_apply,
        "main_future_command_reference_ready": main_future_command_reference_ready,
        "apply_execution_enabled": False,
        "create_only_apply_required": True,
        "read_only": True,
        "mutation_permitted": False,
        "message": message,
    }


def build_future_apply_request_validation_preview(
    *,
    requested_candidate_identity_reference_id: str | None,
    requested_candidate_identity_fingerprint: str | None,
    requested_candidate_identity_reference_type: str | None,
    future_apply_reference_contract: dict,
) -> dict:
    """Build a read-only identity-match preview for a hypothetical future apply request.

    Safety invariant:
    - This is validation/readiness preview only.
    - It never executes apply and never mutates state.
    - It never grants mutation permission.
    - ``available=True`` only means the requested identity values match the expected
      reference contract and are structurally valid/referenceable.
    - ``available=True`` does not imply apply is enabled; ``apply_execution_enabled``
      must remain ``False``.
    """
    requested_reference_id = (
        requested_candidate_identity_reference_id
        if isinstance(requested_candidate_identity_reference_id, str)
        else ""
    )
    requested_fingerprint = (
        requested_candidate_identity_fingerprint
        if isinstance(requested_candidate_identity_fingerprint, str)
        else ""
    )
    requested_reference_type = (
        requested_candidate_identity_reference_type
        if isinstance(requested_candidate_identity_reference_type, str)
        else ""
    )

    raw_expected_reference_id = future_apply_reference_contract.get("candidate_identity_reference_id")
    expected_reference_id = raw_expected_reference_id if isinstance(raw_expected_reference_id, str) else ""
    raw_expected_fingerprint = future_apply_reference_contract.get("candidate_identity_fingerprint")
    expected_fingerprint = raw_expected_fingerprint if isinstance(raw_expected_fingerprint, str) else ""
    raw_expected_reference_type = future_apply_reference_contract.get("candidate_identity_reference_type")
    expected_reference_type = raw_expected_reference_type if isinstance(raw_expected_reference_type, str) else ""

    reference_id_matches = bool(requested_reference_id) and requested_reference_id == expected_reference_id
    fingerprint_matches = bool(requested_fingerprint) and requested_fingerprint == expected_fingerprint
    reference_type_matches = bool(requested_reference_type) and requested_reference_type == expected_reference_type

    raw_referenceable = future_apply_reference_contract.get("candidate_identity_set_referenceable")
    contract_referenceable = raw_referenceable if isinstance(raw_referenceable, bool) else False
    raw_available = future_apply_reference_contract.get("available")
    contract_available = raw_available is True

    available = (
        contract_available
        and reference_id_matches
        and fingerprint_matches
        and reference_type_matches
        and contract_referenceable
    )

    return {
        "available": available,
        "validation_type": "future_apply_request_validation_preview",
        "requested_candidate_identity_reference_id": requested_reference_id,
        "requested_candidate_identity_fingerprint": requested_fingerprint,
        "requested_candidate_identity_reference_type": requested_reference_type,
        "expected_candidate_identity_reference_id": expected_reference_id,
        "expected_candidate_identity_fingerprint": expected_fingerprint,
        "expected_candidate_identity_reference_type": expected_reference_type,
        "reference_id_matches": reference_id_matches,
        "fingerprint_matches": fingerprint_matches,
        "reference_type_matches": reference_type_matches,
        "contract_referenceable": contract_referenceable,
        "apply_execution_enabled": False,
        "read_only": True,
        "mutation_permitted": False,
        "message": "This is a validation-only preview and does not execute apply or mutate any state.",
    }


def build_create_only_apply_execution_preflight_preview(
    *,
    future_apply_reference_contract: dict,
    future_apply_request_validation_preview: dict,
    identity_readiness: dict,
    target_absent: bool,
    create_only_scope_confirmed: bool,
    audit_metadata_present: bool,
) -> dict:
    """Build a disabled, read-only create-only apply execution preflight preview.

    Safety invariant:
    - This helper is preflight/readiness metadata only.
    - It never executes apply and never mutates any state.
    - ``all_known_preconditions_met=True`` is not execution authorization.
    - ``available=True`` is not execution authorization.
    - ``execution_enabled`` and ``can_execute`` must remain ``False`` in this phase.
    - ``mutation_permitted`` must remain ``False`` in this phase.
    """

    normalized_target_absent = target_absent if isinstance(target_absent, bool) else False
    normalized_create_only_scope_confirmed = (
        create_only_scope_confirmed if isinstance(create_only_scope_confirmed, bool) else False
    )
    normalized_audit_metadata_present = audit_metadata_present if isinstance(audit_metadata_present, bool) else False

    raw_contract_available = future_apply_reference_contract.get("available")
    future_apply_reference_contract_available = raw_contract_available if isinstance(raw_contract_available, bool) else False

    raw_validation_available = future_apply_request_validation_preview.get("available")
    future_apply_request_validation_available = raw_validation_available if isinstance(raw_validation_available, bool) else False

    reference_id_matches = future_apply_request_validation_preview.get("reference_id_matches") is True
    fingerprint_matches = future_apply_request_validation_preview.get("fingerprint_matches") is True
    reference_type_matches = future_apply_request_validation_preview.get("reference_type_matches") is True
    candidate_identity_reference_matches = (
        reference_id_matches and fingerprint_matches and reference_type_matches
    )

    future_command_reference = identity_readiness.get("future_command_reference")
    if not isinstance(future_command_reference, dict):
        future_command_reference = {}
    raw_main_ready = future_command_reference.get("can_reference_future_command")
    main_future_command_reference_ready = raw_main_ready if isinstance(raw_main_ready, bool) else False

    all_known_preconditions_met = all(
        [
            normalized_target_absent,
            normalized_create_only_scope_confirmed,
            normalized_audit_metadata_present,
            future_apply_reference_contract_available,
            future_apply_request_validation_available,
            candidate_identity_reference_matches,
            main_future_command_reference_ready,
        ]
    )

    message = (
        "Create-only apply execution preflight preview is disabled and read-only; "
        "it does not execute apply or permit mutation, even when preconditions are met."
    )

    return {
        "available": all_known_preconditions_met,
        "preflight_type": "create_only_apply_execution_preflight_preview",
        "target_absent": normalized_target_absent,
        "create_only_scope_confirmed": normalized_create_only_scope_confirmed,
        "audit_metadata_present": normalized_audit_metadata_present,
        "future_apply_reference_contract_available": future_apply_reference_contract_available,
        "future_apply_request_validation_available": future_apply_request_validation_available,
        "candidate_identity_reference_matches": candidate_identity_reference_matches,
        "main_future_command_reference_ready": main_future_command_reference_ready,
        "all_known_preconditions_met": all_known_preconditions_met,
        "execution_enabled": False,
        "can_execute": False,
        "read_only": True,
        "mutation_permitted": False,
        "message": message,
    }


def build_create_only_apply_audit_metadata_preview(
    *,
    requested_by: str | None,
    audit_reason: str | None,
    explicit_confirmation: str | None,
    mutation_scope: str | None,
    required_confirmation_phrase: str,
    required_mutation_scope: str = "create_only",
) -> dict:
    """Build read-only preview metadata for future create-only apply audit requirements.

    Safety invariant:
    - This helper is preview/readiness metadata only.
    - It never executes apply and never mutates any state.
    - ``available=True`` only indicates required audit metadata is present/matching.
    - ``execution_enabled`` and ``can_execute`` must remain ``False``.
    """
    normalized_requested_by = requested_by.strip() if isinstance(requested_by, str) else ""
    normalized_audit_reason = audit_reason.strip() if isinstance(audit_reason, str) else ""
    normalized_explicit_confirmation = (
        explicit_confirmation.strip() if isinstance(explicit_confirmation, str) else ""
    )
    normalized_mutation_scope = mutation_scope.strip() if isinstance(mutation_scope, str) else ""

    requested_by_present = bool(normalized_requested_by)
    audit_reason_present = bool(normalized_audit_reason)
    explicit_confirmation_present = bool(normalized_explicit_confirmation)
    explicit_confirmation_matches = (
        explicit_confirmation_present
        and normalized_explicit_confirmation == required_confirmation_phrase
    )
    mutation_scope_present = bool(normalized_mutation_scope)
    mutation_scope_matches = (
        mutation_scope_present
        and normalized_mutation_scope == required_mutation_scope
    )

    all_required_audit_metadata_present = all(
        [
            requested_by_present,
            audit_reason_present,
            explicit_confirmation_present,
            explicit_confirmation_matches,
            mutation_scope_present,
            mutation_scope_matches,
        ]
    )

    return {
        "available": all_required_audit_metadata_present,
        "preview_type": "create_only_apply_audit_metadata_preview",
        "requested_by_present": requested_by_present,
        "audit_reason_present": audit_reason_present,
        "explicit_confirmation_present": explicit_confirmation_present,
        "explicit_confirmation_matches": explicit_confirmation_matches,
        "mutation_scope_present": mutation_scope_present,
        "mutation_scope_matches": mutation_scope_matches,
        "required_confirmation_phrase": required_confirmation_phrase,
        "required_mutation_scope": required_mutation_scope,
        "all_required_audit_metadata_present": all_required_audit_metadata_present,
        "execution_enabled": False,
        "can_execute": False,
        "read_only": True,
        "mutation_permitted": False,
        "message": (
            "Create-only apply audit metadata preview is read-only and disabled; "
            "it does not execute apply or mutate any state."
        ),
    }
