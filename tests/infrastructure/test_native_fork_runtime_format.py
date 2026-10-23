"""Pure v2 format guards. Actual authority/replay is exercised by public HTTP tests."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from beta_engine.application.native_fork_runtime_reducer import initial_runtime
from beta_engine.domain.native_fork_baseline import project_native_fork_baseline
from beta_engine.domain.players.calendar_health import CalendarHealthOrigin
from beta_engine.domain.rankings.calendar_official import (
    CalendarOfficialRankingSnapshot,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarTourPolicy,
    ranking_week,
)
from beta_engine.infrastructure.db.native_fork_runtime_state import (
    component,
    load_runtime,
)
from beta_engine.infrastructure.db.native_fork_saved_root import (
    load_native_fork_saved_root,
)
from tests.domain.test_native_fork_baseline import inputs

pytestmark = pytest.mark.pr_critical


def runtime_root():
    values = inputs(7)
    baseline = project_native_fork_baseline(**values)
    policy = OfficialRankingPolicy(policy_id="format-only", best_n=15)
    ranking = CalendarOfficialRankingSnapshot(
        run_id="r",
        branch_id="b",
        run_calendar=baseline.week.calendar.to_metadata(),
        week=ranking_week(baseline.week),
        policy=policy,
        previous_fingerprint=None,
        input_fingerprint="1" * 64,
        rows=(),
    )
    values["tour"].rankings = (ranking,)
    values["tour"].editions, values["tour"].transitions = (), ()
    values["tour"].policies = (
        CalendarTourPolicy(effective_week=baseline.week, ranking=policy),
    )
    values["health"].origin = CalendarHealthOrigin(
        baseline_fingerprint="2" * 64,
        command_id="format-health",
        request_fingerprint="3" * 64,
        initialization_policy="fresh_without_history.v1",
        audit_label="test",
        audit_reason="format test",
    )
    runtime = initial_runtime(
        baseline, "root", SimpleNamespace(health=values["health"], tour=values["tour"])
    )
    revision = SimpleNamespace(
        run_id="r",
        branch_id="target",
        revision_id="root",
        parent_revision_id="saved",
        kind="branch_fork_materialized",
        payload_schema_version="native_fork_saved_root.v2",
        payload={
            "run": {"run_calendar": baseline.week.calendar.to_metadata()},
            "branch": {
                "status": "active",
                "forked_from_branch_id": "b",
                "forked_from_saved_revision_id": "saved",
            },
            "content": {
                "native_fork_baseline": {
                    "state": baseline.model_dump(mode="json"),
                    "fingerprint": baseline.fingerprint,
                },
                "native_fork_runtime": component(runtime),
            },
        },
    )
    return runtime, revision


def test_complete_v2_runtime_roundtrip_and_compatible_envelope_extension():
    runtime, revision = runtime_root()
    assert load_runtime(revision.payload) == runtime
    assert load_native_fork_saved_root(revision) == runtime.baseline
    extended = deepcopy(revision.payload)
    extended["run"]["run_calendar"]["season_count"] += 1
    revision.payload = extended
    assert load_native_fork_saved_root(revision) == runtime.baseline
    assert load_runtime(revision.payload).week.calendar.season_count == 3


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "extra",
        "hash",
        "owner",
        "source",
        "clock",
        "shorten",
        "status",
        "parent",
        "kind",
        "schema",
        "detached_baseline",
        "runtime_owner",
    ],
)
def test_v2_format_fails_closed(case):
    _, revision = runtime_root()
    c = revision.payload["content"]
    if case == "missing":
        del c["native_fork_runtime"]
    elif case == "extra":
        c["unreviewed_state"] = {}
    elif case == "hash":
        c["native_fork_runtime"]["fingerprint"] = "0" * 64
    elif case == "owner":
        revision.branch_id = "foreign"
    elif case == "source":
        revision.payload["branch"]["forked_from_branch_id"] = "foreign"
    elif case == "clock":
        revision.payload["run"]["run_calendar"]["weeks_per_year"] += 1
    elif case == "shorten":
        revision.payload["run"]["run_calendar"]["season_count"] -= 1
    elif case == "status":
        revision.payload["branch"]["status"] = "preparing_native_fork"
    elif case == "parent":
        revision.parent_revision_id = "future"
    elif case == "kind":
        revision.kind = "manual_save"
    elif case == "schema":
        revision.payload_schema_version = "run_saved_revision_v1"
    elif case == "detached_baseline":
        c["native_fork_baseline"]["fingerprint"] = "0" * 64
    elif case == "runtime_owner":
        c["native_fork_runtime"]["state"]["tour"]["branch_id"] = "foreign"
    with pytest.raises(ValueError):
        load_native_fork_saved_root(revision)


def test_parsed_runtime_cache_is_bounded_and_never_accepts_a_declared_hash(monkeypatch):
    from beta_engine.infrastructure.db import native_fork_runtime_state as storage
    runtime, revision = runtime_root()
    with storage.native_read_proof_scope() as memo:
        for index in range(storage._MAX_PARSED_RUNTIMES + 3):
            from beta_engine.application.native_fork_runtime_reducer import cohere
            changed = cohere(runtime, root_saved_revision_id=f'root-{index}')
            assert load_runtime({'content': {'native_fork_runtime': component(changed)}}) == changed
        assert len(memo['parsed_native_runtimes']) == storage._MAX_PARSED_RUNTIMES
        payload = deepcopy(revision.payload)
        load_runtime(payload)
        payload['content']['native_fork_runtime']['state']['tour']['slot_cursor'] += 1
        with pytest.raises(ValueError, match='fingerprint differs'):
            load_runtime(payload)
    monkeypatch.setattr(storage, '_MAX_PARSED_RUNTIME_BYTES', 1)
    with storage.native_read_proof_scope() as memo:
        assert load_runtime(revision.payload) == runtime
        assert memo['parsed_native_runtimes'] == {}
