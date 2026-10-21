"""Pure staging-format contracts; actual source authority has SQLite coverage."""

from types import SimpleNamespace

import pytest

from beta_engine.domain.native_fork_baseline import project_native_fork_baseline
from beta_engine.domain.run_revisions import (
    BRANCH_FORK_MATERIALIZED_SAVED_REVISION_KIND,
)
from beta_engine.infrastructure.db.native_fork_saved_root import (
    COMPONENT_KEY,
    PAYLOAD_SCHEMA,
    PENDING_STATUS,
    load_native_fork_saved_root,
)
from tests.domain.test_native_fork_baseline import inputs

pytestmark = pytest.mark.pr_critical


def root():
    baseline = project_native_fork_baseline(**inputs())
    revision = SimpleNamespace(
        run_id="r",
        branch_id="target",
        parent_revision_id="saved",
        kind=BRANCH_FORK_MATERIALIZED_SAVED_REVISION_KIND,
        payload_schema_version=PAYLOAD_SCHEMA,
        payload={
            "run": {"run_calendar": baseline.week.calendar.to_metadata()},
            "branch": {
                "status": PENDING_STATUS,
                "forked_from_branch_id": "b",
                "forked_from_saved_revision_id": "saved",
            },
            "content": {
                COMPONENT_KEY: {
                    "state": baseline.model_dump(mode="json"),
                    "fingerprint": baseline.fingerprint,
                }
            },
        },
    )
    return baseline, revision


def test_staging_format_roundtrip_preserves_exact_current_facts():
    baseline, revision = root()
    assert load_native_fork_saved_root(revision) == baseline
    assert (
        load_native_fork_saved_root(
            SimpleNamespace(
                payload={"content": {}},
                payload_schema_version="run_saved_revision_v1",
            )
        )
        is None
    )


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "extra",
        "malformed",
        "fingerprint",
        "owner",
        "parent",
        "kind",
        "schema",
        "status",
        "source_branch",
        "calendar",
        "malformed_run",
        "downgrade",
    ],
)
def test_staging_format_rejects_incomplete_or_mixed_authorities(case):
    _, revision = root()
    payload = revision.payload
    if case == "missing":
        payload["content"].clear()
    elif case == "extra":
        payload["content"]["calendar_tour_authority"] = {}
    elif case == "malformed":
        payload["content"][COMPONENT_KEY] = []
    elif case == "fingerprint":
        payload["content"][COMPONENT_KEY]["fingerprint"] = "0" * 64
    elif case == "owner":
        revision.branch_id = "foreign"
    elif case == "parent":
        revision.parent_revision_id = "other"
    elif case == "kind":
        revision.kind = "manual_save"
    elif case == "schema":
        revision.payload_schema_version = "run_saved_revision_v1"
    elif case == "status":
        payload["branch"]["status"] = "active"
    elif case == "source_branch":
        payload["branch"]["forked_from_branch_id"] = "foreign"
    elif case == "calendar":
        payload["run"]["run_calendar"]["weeks_per_year"] = 61
    elif case == "malformed_run":
        payload["run"] = []
    elif case == "downgrade":
        revision.payload_schema_version = "run_saved_revision_v1"
        payload["content"].clear()
    with pytest.raises(ValueError, match="Native fork root"):
        load_native_fork_saved_root(revision)
