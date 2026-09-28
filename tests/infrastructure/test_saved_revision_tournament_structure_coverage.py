"""Saved Revision coverage for canonical tournament-structure authorities."""

import pytest

from beta_engine.infrastructure.db.models import (
    TournamentFormatAuthorityModel,
    TournamentGroupMatchScheduleAuthorityModel,
    TournamentGroupRulesPolicyModel,
    TournamentTopologyAuthorityModel,
    WorldTourFinalsParticipantSelectionConfigurationModel,
    WorldTourFinalsParticipantSelectionSnapshotModel,
    WorldTourFinalsRaceConfigurationModel,
    WorldTourFinalsRaceSnapshotModel,
)
from beta_engine.infrastructure.db.saved_revision_restore_coverage import (
    COMPONENT_COVERAGE,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    COMPONENT_KEY as SIMULATION_SLOT_COMPONENT_KEY,
)


@pytest.mark.pr_critical
def test_simulation_slot_restore_preflight_covers_all_tournament_structure_authorities():
    simulation_coverage = next(
        coverage
        for coverage in COMPONENT_COVERAGE
        if coverage.component_key == SIMULATION_SLOT_COMPONENT_KEY
    )
    covered = set(simulation_coverage.models)

    assert {
        WorldTourFinalsRaceConfigurationModel,
        WorldTourFinalsRaceSnapshotModel,
        WorldTourFinalsParticipantSelectionConfigurationModel,
        WorldTourFinalsParticipantSelectionSnapshotModel,
        TournamentGroupRulesPolicyModel,
        TournamentFormatAuthorityModel,
        TournamentTopologyAuthorityModel,
        TournamentGroupMatchScheduleAuthorityModel,
    } <= covered
