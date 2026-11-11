"""Validate an explicitly proposed round schedule against one Saved ATP profile."""
import json
from pydantic import Field, field_validator
from sqlalchemy import text

from beta_engine.application.atp_saved_tour_source import read_saved_atp_source
from beta_engine.application.atp_saved_snapshot_week_preview import build_saved_atp_reference_week_mapping
from beta_engine.application.atp_sourced_edition import saved_profiles, project_profile
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.atp_knockout_profile import ATPKnockoutProfile
from beta_engine.domain.tournaments.knockout_run_schedule import KnockoutRunSchedule


class ATPKnockoutSchedulePreviewRequest(FrozenInput):
    expected_saved_head: str = Field(min_length=1)
    expected_profile_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    schedule: KnockoutRunSchedule

    @field_validator('schedule', mode='before')
    @classmethod
    def decode_schedule(cls, value):
        # Strict dataclasses accept JSON objects at the HTTP boundary, while
        # direct Python construction still requires typed calendar instances.
        if isinstance(value, dict):
            return KnockoutRunSchedule.model_validate_json(json.dumps(value))
        return value


def preview_atp_knockout_schedule(repository, *, run_id, branch_id, occurrence_id, request):
    with repository._session_factory() as session:
        session.execute(text('BEGIN'))
        calendar, revision, state = read_saved_atp_source(session, run_id=run_id, branch_id=branch_id)
        if revision.revision_id != request.expected_saved_head:
            raise ValueError('Saved ATP source changed; refresh the Tour')
        profiles = saved_profiles(state, occurrence_id=occurrence_id)
        if occurrence_id not in profiles:
            raise ValueError('No Saved sporting configuration for this ATP occurrence')
        profile, fingerprint = profiles[occurrence_id]
        if not isinstance(profile, ATPKnockoutProfile):
            raise ValueError('Round schedule preview requires a knockout profile')
        if fingerprint != request.expected_profile_fingerprint:
            raise ValueError('Saved ATP sporting profile fingerprint changed')
        if request.schedule.calendar != calendar:
            raise ValueError('Knockout schedule differs from the exact Saved Run calendar')
        mapping = build_saved_atp_reference_week_mapping(state)
        source = project_profile(calendar, state, mapping, profile)
    if 'run_ordinals' not in source:
        raise ValueError('ATP Main source is outside the Run horizon')
    geometry = profile.geometry()
    request.schedule.validate_capacities(
        main_capacity=geometry['main']['bracket_capacity'],
        qualification_capacities=tuple(s['bracket_capacity'] for s in geometry['qualification_sections']),
    )
    if any(r.week.ordinal not in source['run_ordinals'] for r in request.schedule.main):
        raise ValueError('Proposed Main rounds leave the Saved ATP Main source weeks')
    result = {'schema_version':'atp_knockout_schedule_preview.v1',
              'run_id':run_id,'branch_id':branch_id,'saved_head_revision_id':revision.revision_id,
              'occurrence_id':occurrence_id,'profile_fingerprint':fingerprint,
              'schedule':request.schedule.model_dump(mode='json'),
              'schedule_fingerprint':request.schedule.fingerprint,
              'source_main_projection':source,'actual_match_count':geometry['actual_match_count'],
              'qualification_dates_verified':False,'sporting_execution_ready':False,
              'run_mutated':False,'requires_explicit_source_chronology_review':True}
    return {**result,'preview_fingerprint':canonical_hash(result)}
