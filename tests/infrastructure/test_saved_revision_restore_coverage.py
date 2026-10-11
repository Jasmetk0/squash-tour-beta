from __future__ import annotations

import pytest

pytestmark = pytest.mark.pr_critical

from beta_engine.infrastructure.db.models import (
    RunProspectModel,
    SeasonClosingRankingModel,
    StandaloneMatchWorkspaceModel,
    TournamentDrawProcessAuthorityModel,
    TournamentDrawRevisionModel,
    TournamentWildCardAuthorityModel,
)
from beta_engine.infrastructure.db.saved_revision_restore_coverage import (
    COMPONENT_COVERAGE,
    RUN_SCOPED_REFERENCE_COVERAGE,
    SUPPORTED_CONTENT_KEYS,
    TRANSIENT_RESTORE_BLOCKERS,
)
from beta_engine.infrastructure.db.saved_revision_season_closure import (
    SEASON_CLOSURE_COMPONENT_KEY,
)


def test_restore_component_registry_has_unique_keys_and_models() -> None:
    keys = [coverage.component_key for coverage in COMPONENT_COVERAGE]
    assert len(keys) == len(set(keys))

    registered_models = [
        model
        for coverage in COMPONENT_COVERAGE
        for model in coverage.models
    ]
    assert len(registered_models) == len(set(registered_models))


def test_restore_registry_covers_recent_recovery_sensitive_authorities() -> None:
    by_key = {
        coverage.component_key: set(coverage.models)
        for coverage in COMPONENT_COVERAGE
    }

    ranking_models = next(
        models
        for key, models in by_key.items()
        if SeasonClosingRankingModel in models
    )
    assert SeasonClosingRankingModel in ranking_models

    simulation_models = next(
        models
        for models in by_key.values()
        if TournamentDrawRevisionModel in models
    )
    assert {
        TournamentWildCardAuthorityModel,
        TournamentDrawProcessAuthorityModel,
        TournamentDrawRevisionModel,
    } <= simulation_models


def test_transient_workspace_is_not_misrepresented_as_saved_content() -> None:
    blocker_models = {
        model
        for blocker in TRANSIENT_RESTORE_BLOCKERS
        for model in blocker.models
    }
    component_models = {
        model
        for coverage in COMPONENT_COVERAGE
        for model in coverage.models
    }

    assert StandaloneMatchWorkspaceModel in blocker_models
    assert StandaloneMatchWorkspaceModel not in component_models


def test_run_prospect_source_is_run_scoped_reference_not_branch_owned() -> None:
    reference_models = {
        model
        for coverage in RUN_SCOPED_REFERENCE_COVERAGE
        for model in coverage.models
    }
    component_models = {
        model
        for coverage in COMPONENT_COVERAGE
        for model in coverage.models
    }

    assert RunProspectModel in reference_models
    assert RunProspectModel not in component_models
    assert all(
        coverage.component_key in SUPPORTED_CONTENT_KEYS
        for coverage in RUN_SCOPED_REFERENCE_COVERAGE
    )


def test_season_closure_is_allowed_saved_content_without_live_table_coverage() -> None:
    assert SEASON_CLOSURE_COMPONENT_KEY in SUPPORTED_CONTENT_KEYS
    assert SEASON_CLOSURE_COMPONENT_KEY not in {
        coverage.component_key for coverage in COMPONENT_COVERAGE
    }
