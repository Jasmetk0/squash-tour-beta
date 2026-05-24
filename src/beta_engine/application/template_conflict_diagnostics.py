from __future__ import annotations

import math

from beta_engine.domain.tournaments import (
    SeasonTemplateConflictDiagnosticsOverview,
    SeasonTemplateSlotConflictPreview,
)


def build_template_conflict_summary_preview(
    template_slot_conflict_preview: SeasonTemplateSlotConflictPreview | None,
) -> dict[str, object]:
    if template_slot_conflict_preview is None:
        return {
            "available": False,
            "read_only": True,
            "non_blocking": True,
            "status": None,
            "warning_count": 0,
            "info_count": 0,
            "conflict_count": 0,
            "conflict_codes": [],
            "busiest_week": None,
            "busiest_week_slot_count": None,
            "source": "template_slot_conflict_preview",
            "message": "Template slot conflict diagnostics are unavailable for this dry-run source.",
        }
    return {
        "available": True,
        "read_only": True,
        "non_blocking": True,
        "status": template_slot_conflict_preview.status,
        "warning_count": template_slot_conflict_preview.warning_count,
        "info_count": template_slot_conflict_preview.info_count,
        "conflict_count": template_slot_conflict_preview.conflict_count,
        "conflict_codes": list(template_slot_conflict_preview.conflict_codes),
        "busiest_week": template_slot_conflict_preview.busiest_week,
        "busiest_week_slot_count": template_slot_conflict_preview.busiest_week_slot_count,
        "source": "template_slot_conflict_preview",
        "message": "Template slot conflict diagnostics are available as read-only non-blocking preview.",
    }


def _normalize_conflict_status(value: object | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in {"clean", "warnings", "info"}:
        return normalized
    return None


def _normalize_non_negative_int(value: object | None) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value if value >= 0 else 0
    if isinstance(value, float):
        if math.isfinite(value) and value >= 0 and value.is_integer():
            return int(value)
        return 0
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return 0


def _is_valid_non_negative_int_value(value: object | None) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value >= 0
    if isinstance(value, float):
        return math.isfinite(value) and value >= 0 and value.is_integer()
    if isinstance(value, str):
        return value.strip().isdigit()
    return False


def build_template_conflict_diagnostics_overview(
    *,
    selected_report_available: bool = False,
    selected_status: str | None = None,
    selected_conflict_count: int = 0,
    preflight_preview: SeasonTemplateSlotConflictPreview | None = None,
    preflight_summary: dict[str, object] | None = None,
    dry_run_preview: SeasonTemplateSlotConflictPreview | None = None,
    dry_run_summary: dict[str, object] | None = None,
) -> SeasonTemplateConflictDiagnosticsOverview:
    preflight_summary_available = isinstance(preflight_summary, dict)
    dry_run_summary_available = isinstance(dry_run_summary, dict)
    preflight_preview_available = preflight_preview is not None
    dry_run_preview_available = dry_run_preview is not None

    preflight_summary_status = _normalize_conflict_status(
        preflight_summary.get("status") if preflight_summary_available else None
    )
    preflight_preview_status = preflight_preview.status if preflight_preview_available else None
    preflight_status = preflight_summary_status
    if preflight_status is None and preflight_preview_status is not None:
        preflight_status = preflight_preview_status

    preflight_summary_count_raw = preflight_summary.get("conflict_count") if preflight_summary_available else None
    preflight_summary_conflict_count = _normalize_non_negative_int(preflight_summary_count_raw)
    preflight_preview_conflict_count = preflight_preview.conflict_count if preflight_preview_available else 0
    preflight_conflict_count = preflight_summary_conflict_count
    if preflight_summary_available and not _is_valid_non_negative_int_value(preflight_summary_count_raw):
        preflight_conflict_count = preflight_preview_conflict_count if preflight_preview_available else 0
    elif not preflight_summary_available:
        preflight_conflict_count = preflight_preview_conflict_count

    dry_run_summary_status = _normalize_conflict_status(
        dry_run_summary.get("status") if dry_run_summary_available else None
    )
    dry_run_preview_status = dry_run_preview.status if dry_run_preview_available else None
    dry_run_status = dry_run_summary_status
    if dry_run_status is None and dry_run_preview_status is not None:
        dry_run_status = dry_run_preview_status

    dry_run_summary_count_raw = dry_run_summary.get("conflict_count") if dry_run_summary_available else None
    dry_run_summary_conflict_count = _normalize_non_negative_int(dry_run_summary_count_raw)
    dry_run_preview_conflict_count = dry_run_preview.conflict_count if dry_run_preview_available else 0
    dry_run_conflict_count = dry_run_summary_conflict_count
    if dry_run_summary_available and not _is_valid_non_negative_int_value(dry_run_summary_count_raw):
        dry_run_conflict_count = dry_run_preview_conflict_count if dry_run_preview_available else 0
    elif not dry_run_summary_available:
        dry_run_conflict_count = dry_run_preview_conflict_count

    return SeasonTemplateConflictDiagnosticsOverview(
        selected_report_available=selected_report_available,
        selected_status=selected_status,
        selected_conflict_count=selected_conflict_count,
        preflight_preview_available=preflight_preview_available,
        preflight_summary_available=preflight_summary_available,
        preflight_status=preflight_status,
        preflight_conflict_count=preflight_conflict_count,
        dry_run_preview_available=dry_run_preview_available,
        dry_run_summary_available=dry_run_summary_available,
        dry_run_status=dry_run_status,
        dry_run_conflict_count=dry_run_conflict_count,
        mutation_behavior="unavailable",
        blocking_behavior="non_blocking",
        read_only=True,
        non_blocking=True,
    )


def build_selected_template_conflict_diagnostics_overview(
    *,
    template_exists: bool,
    status: object | None,
    conflict_count: object | None,
) -> SeasonTemplateConflictDiagnosticsOverview:
    if not template_exists:
        return build_template_conflict_diagnostics_overview(
            selected_report_available=False,
            selected_status=None,
            selected_conflict_count=0,
        )
    selected_status = _normalize_conflict_status(status)
    selected_conflict_count = _normalize_non_negative_int(conflict_count)
    return build_template_conflict_diagnostics_overview(
        selected_report_available=True,
        selected_status=selected_status,
        selected_conflict_count=selected_conflict_count,
    )
