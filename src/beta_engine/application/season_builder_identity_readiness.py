"""Build read-only identity readiness metadata for Season Builder dry-run previews.

This helper only assembles checklist/readiness metadata from supplied dry-run
inputs. It does not mutate state, does not authorize apply/build execution, and
keeps dry-run behavior read-only. Candidate identity reference fields are
additive metadata for future audited flows only; they must not relax the main
future command gate.

`can_reference_future_command` remains derived from the primary identity
references plus validation/plan readiness (preflight fingerprint, reviewed diff
id, dry-run result references, validation summary, and read-only plan
availability).
"""

from __future__ import annotations


def _build_candidate_identity_readiness_overview(
    *,
    candidate_identity_fingerprint: str | None,
    candidate_identity_reference_id: str | None,
    candidate_identity_reference_type: str | None,
    can_reference_candidate_identity_set: bool,
    candidate_reference_status: str,
    main_future_command_reference_ready: bool,
) -> dict[str, object]:
    available = bool(candidate_identity_reference_id and candidate_identity_reference_id.strip())
    return {
        "available": available,
        "candidate_identity_fingerprint": candidate_identity_fingerprint,
        "candidate_identity_reference_id": candidate_identity_reference_id,
        "candidate_identity_reference_type": candidate_identity_reference_type,
        "can_reference_candidate_identity_set": can_reference_candidate_identity_set,
        "candidate_reference_status": candidate_reference_status,
        "main_future_command_reference_ready": main_future_command_reference_ready,
        "read_only": True,
        "mutation_permitted": False,
        "message": (
            "Candidate identity readiness is referenceable."
            if can_reference_candidate_identity_set
            else "Candidate identity readiness is not referenceable yet."
        ),
    }


def build_dry_run_identity_readiness(
    *,
    preflight_fingerprint: str | None,
    reviewed_diff_id: str | None,
    dry_run_result_fingerprint: str | None,
    dry_run_result_id: str | None,
    validation_summary: dict[str, object],
    plan_readiness: dict[str, object],
    candidate_identity_fingerprint: dict[str, object],
    candidate_identity_review_reference: dict[str, object],
) -> dict[str, object]:
    """Return dry-run identity readiness status, checklist items, and future references.

    The returned payload contains:
    - `status`: main identity readiness state for future command references.
    - `items`: checklist rows describing primary readiness, mutation lock state,
      and candidate identity review information.
    - `future_command_reference`: copied primary/candidate reference values plus
      the computed command-reference gate booleans.

    Candidate identity fields are copied into `future_command_reference` as
    additive, read-only metadata. In this phase, the
    `candidate_identity_review_reference` checklist item is informational and
    must not alter the main `can_reference_future_command` decision.
    """
    validation_summary_status = str(validation_summary.get("status") or "unknown").strip()
    has_preflight_fingerprint = bool(preflight_fingerprint and preflight_fingerprint.strip())
    has_reviewed_diff_id = bool(reviewed_diff_id and reviewed_diff_id.strip())
    has_dry_run_result_fingerprint = isinstance(dry_run_result_fingerprint, str) and dry_run_result_fingerprint.startswith("drf_")
    has_dry_run_result_id = isinstance(dry_run_result_id, str) and dry_run_result_id.startswith("drr_")
    plan_available = bool(plan_readiness.get("read_only_plan_available"))
    candidate_identity_fingerprint_value = (
        candidate_identity_fingerprint.get("fingerprint")
        if isinstance(candidate_identity_fingerprint.get("fingerprint"), str)
        and candidate_identity_fingerprint.get("fingerprint").strip()
        else None
    )
    candidate_identity_reference_id = (
        candidate_identity_review_reference.get("reference_id")
        if isinstance(candidate_identity_review_reference.get("reference_id"), str)
        and candidate_identity_review_reference.get("reference_id").strip()
        else None
    )
    can_reference_candidate_identity_set = (
        candidate_identity_review_reference.get("can_reference_future_apply")
        if isinstance(candidate_identity_review_reference.get("can_reference_future_apply"), bool)
        else False
    )
    candidate_identity_reference_type = (
        candidate_identity_review_reference.get("reference_type")
        if isinstance(candidate_identity_review_reference.get("reference_type"), str)
        and candidate_identity_review_reference.get("reference_type").strip()
        else None
    )

    identity_items: list[dict[str, str]] = [
        {
            "area": "preflight_fingerprint",
            "status": "OK" if has_preflight_fingerprint else "Missing",
            "message": "Preflight fingerprint is present." if has_preflight_fingerprint else "Preflight fingerprint is missing.",
        },
        {
            "area": "reviewed_diff_id",
            "status": "OK" if has_reviewed_diff_id else "Missing",
            "message": "Reviewed diff id is present." if has_reviewed_diff_id else "Reviewed diff id is missing.",
        },
        {
            "area": "dry_run_result_fingerprint",
            "status": "OK" if has_dry_run_result_fingerprint else "Missing",
            "message": "Dry-run result fingerprint is present." if has_dry_run_result_fingerprint else "Dry-run result fingerprint is missing or invalid.",
        },
        {
            "area": "dry_run_result_id",
            "status": "OK" if has_dry_run_result_id else "Missing",
            "message": "Dry-run result id is present." if has_dry_run_result_id else "Dry-run result id is missing or invalid.",
        },
        {
            "area": "validation_summary",
            "status": "Blocked" if validation_summary_status == "blocking" else ("Info" if validation_summary_status == "warnings" else "OK"),
            "message": f"Validation summary status is '{validation_summary_status}'.",
        },
        {
            "area": "plan_readiness",
            "status": "OK" if plan_available else "Blocked",
            "message": "Read-only plan is available." if plan_available else "Read-only plan is not available.",
        },
        {
            "area": "mutation_state",
            "status": "Blocked",
            "message": "Mutation remains disabled; this checklist is reference-only.",
        },
        {
            "area": "candidate_identity_review_reference",
            "status": "OK" if can_reference_candidate_identity_set else "BLOCKED",
            "message": (
                "Candidate identity set can be referenced by a future audited apply flow."
                if can_reference_candidate_identity_set
                else "Candidate identity set cannot be referenced by a future apply flow yet."
            ),
        },
    ]

    missing_identity = not all(
        [has_preflight_fingerprint, has_reviewed_diff_id, has_dry_run_result_fingerprint, has_dry_run_result_id]
    )
    blocked_reference = validation_summary_status == "blocking" or not plan_available
    identity_status = "missing_identity" if missing_identity else ("blocked_reference" if blocked_reference else "ready_reference")

    main_future_command_reference_ready = identity_status == "ready_reference"
    candidate_reference_status = next(
        item["status"] for item in identity_items if item["area"] == "candidate_identity_review_reference"
    )
    candidate_identity_readiness_overview = _build_candidate_identity_readiness_overview(
        candidate_identity_fingerprint=candidate_identity_fingerprint_value,
        candidate_identity_reference_id=candidate_identity_reference_id,
        candidate_identity_reference_type=candidate_identity_reference_type,
        can_reference_candidate_identity_set=can_reference_candidate_identity_set,
        candidate_reference_status=candidate_reference_status,
        main_future_command_reference_ready=main_future_command_reference_ready,
    )

    return {
        "status": identity_status,
        "items": identity_items,
        "future_command_reference": {
            "preflight_fingerprint": preflight_fingerprint,
            "reviewed_diff_id": reviewed_diff_id,
            "dry_run_result_fingerprint": dry_run_result_fingerprint,
            "dry_run_result_id": dry_run_result_id,
            "can_reference_future_command": main_future_command_reference_ready,
            "mutation_still_disabled": True,
            "candidate_identity_fingerprint": candidate_identity_fingerprint_value,
            "candidate_identity_reference_id": candidate_identity_reference_id,
            "can_reference_candidate_identity_set": can_reference_candidate_identity_set,
            "candidate_identity_reference_type": candidate_identity_reference_type,
        },
        "candidate_identity_readiness_overview": candidate_identity_readiness_overview,
    }
