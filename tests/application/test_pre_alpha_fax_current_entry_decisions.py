from __future__ import annotations

from types import SimpleNamespace

import pytest

from beta_engine.application.pre_alpha_fax_current_entry_decisions import (
    PreAlphaFaxCurrentEntryDecisionApplyRequest,
    PreAlphaFaxCurrentEntryDecisionService,
)
from beta_engine.domain.rankings.official import RankingWeek


pytestmark = pytest.mark.pr_critical


class _SessionContext:
    def __enter__(self):
        return object()

    def __exit__(self, exc_type, exc, tb):
        return None


class _Driver:
    def __init__(self):
        self.factory = lambda: _SessionContext()
        self.preview_calls = []
        self.commit_calls = []
        self.persisted = False

    def position(self, *, run_id: str, branch_id: str):
        return SimpleNamespace(
            current_slot_kind="entry",
            slot_ordinal=7,
            current_week=RankingWeek(season_index=0, week=1),
            position_fingerprint="a" * 64,
        )

    def preview_entry_decision_slot(self, **kwargs):
        self.preview_calls.append(kwargs)
        return {
            "expected_revision_id": "revision-1",
            "entry_batch_fingerprint": "b" * 64,
            "application_decisions_fingerprint": "c" * 64,
            "slot_fingerprint": "d" * 64,
            "decision_count": 42,
            "persisted": self.persisted,
        }

    def commit_entry_decision_slot(self, command):
        self.commit_calls.append(command)
        self.persisted = True
        return {
            "decision_count": 42,
            "slot_fingerprint": "d" * 64,
            "adoption": "committed",
        }


def test_current_entry_bootstrap_uses_authoritative_position_slot_and_stops_at_validation(
    monkeypatch,
) -> None:
    import beta_engine.application.pre_alpha_fax_current_entry_decisions as module

    monkeypatch.setattr(module, "get_run_package_state", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        module.CalendarPackageRunAdapter,
        "project_calendar",
        staticmethod(
            lambda *args, **kwargs: SimpleNamespace(
                calendar=SimpleNamespace(
                    events=[
                        SimpleNamespace(
                            event_id="event-b",
                            season_week=1,
                            tour_level="WORLD_TOUR",
                        ),
                        SimpleNamespace(
                            event_id="event-a",
                            season_week=1,
                            tour_level="WORLD_TOUR",
                        ),
                        SimpleNamespace(
                            event_id="lower",
                            season_week=1,
                            tour_level="ELITE_TOUR",
                        ),
                    ]
                )
            )
        ),
    )
    driver = _Driver()
    service = PreAlphaFaxCurrentEntryDecisionService(driver)

    preview = service.preview(run_id="run", branch_id="branch", seed=9001)
    assert preview.decision_slot_ordinal == 7
    assert preview.event_ids == ("event-a", "event-b")
    assert preview.decision_count == 42
    assert driver.preview_calls[0]["decision_slot_ordinal"] == 7
    assert driver.preview_calls[0]["event_ids"] == ("event-a", "event-b")

    applied = service.apply(
        run_id="run",
        branch_id="branch",
        seed=9001,
        request=PreAlphaFaxCurrentEntryDecisionApplyRequest(
            command_id="fax-entry-slot-1",
            expected_preview_fingerprint=preview.preview_fingerprint,
        ),
    )
    assert applied.adoption == "committed"
    assert applied.validation_required is True
    assert applied.validation_policy_status == "automatic_policy_unresolved"
    assert driver.commit_calls[0].decision_slot_ordinal == 7
    assert driver.commit_calls[0].event_ids == ("event-a", "event-b")

    replay_preview = service.preview(run_id="run", branch_id="branch", seed=9001)
    assert replay_preview.persisted is True
    assert replay_preview.preview_fingerprint == preview.preview_fingerprint


def test_current_entry_bootstrap_refuses_non_entry_position() -> None:
    driver = _Driver()
    driver.position = lambda **kwargs: SimpleNamespace(
        current_slot_kind="match",
        slot_ordinal=3,
        current_week=RankingWeek(season_index=0, week=1),
        position_fingerprint="a" * 64,
    )
    service = PreAlphaFaxCurrentEntryDecisionService(driver)

    with pytest.raises(ValueError, match="current authoritative slot to be Entry"):
        service.preview(run_id="run", branch_id="branch")
