"""Authenticate Saved ATP Package + initial Draw before scheduled consumption."""
import json
from dataclasses import dataclass

from sqlalchemy import text

from beta_engine.application.atp_saved_tour_source import read_saved_atp_source
from beta_engine.application.atp_knockout_schedule_preview import ATPKnockoutSchedulePreviewRequest, validate_saved_atp_knockout_schedule
from beta_engine.application.run_calendar_read_authority import resolve_revision_run_calendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.scheduled_knockout_feeders import ScheduledKnockoutFeederPlan, scheduled_knockout_progress
from beta_engine.infrastructure.db.run_package_state import load_saved_run_package_state
from beta_engine.infrastructure.db.simulation_slot_state import load_saved_simulation_slot_component
from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository


@dataclass(slots=True)
class SavedATPScheduledFeederService:
    repository: SimulationPersistenceRepository

    def prepare(self, *, run_id: str, branch_id: str, occurrence_id: str,
                request: ATPKnockoutSchedulePreviewRequest) -> ScheduledKnockoutFeederPlan:
        with self.repository._session_factory() as session:
            session.execute(text('BEGIN'))
            calendar, revision, state = read_saved_atp_source(session,run_id=run_id,branch_id=branch_id)
            if revision.revision_id != request.expected_saved_head:
                raise ValueError('Saved ATP source changed; refresh the Tour')
            if revision.branch_id != branch_id:
                raise ValueError('Scheduled ATP Draw requires a Branch-owned materialized Saved source')
            return self._build(run_id=run_id,branch_id=branch_id,occurrence_id=occurrence_id,request=request,
                calendar=calendar,state=state,payload=json.loads(revision.payload_json),
                revision_id=revision.revision_id,content_hash=revision.content_hash)

    def reload(self, plan: ScheduledKnockoutFeederPlan, *, run_id: str, branch_id: str,
               expected_plan_fingerprint: str) -> ScheduledKnockoutFeederPlan:
        # The schedule is an explicit proposal, not contained in the source
        # Package. Its reviewed fingerprint must come from the consuming owner.
        if plan.fingerprint != expected_plan_fingerprint:
            raise ValueError('Scheduled ATP plan differs from its reviewed binding')
        if (plan.draw.run_id,plan.draw.branch_id) != (run_id,branch_id):
            raise ValueError('Scheduled ATP plan belongs to a foreign Run/Branch')
        history=self.repository.get_branch_saved_revision_history(run_id=run_id,branch_id=branch_id)
        revision=next((r for r in history.saved_revisions if r.revision_id==plan.source_saved_revision_id),None)
        if revision is None or revision.branch_id!=branch_id or revision.content_hash!=plan.source_saved_content_hash:
            raise ValueError('Scheduled ATP source is unreachable or its Saved envelope differs')
        with self.repository._session_factory() as session:
            calendar=resolve_revision_run_calendar(session,run_id=run_id,revision_id=revision.revision_id,_repository=self.repository)
        state=load_saved_run_package_state(revision.payload,run_id=run_id,branch_id=branch_id)
        if state is None:
            raise ValueError('Saved ATP Package is missing')
        request=ATPKnockoutSchedulePreviewRequest(expected_saved_head=revision.revision_id,
            expected_profile_fingerprint=plan.source_profile_fingerprint,schedule=plan.schedule)
        rebuilt=self._build(run_id=run_id,branch_id=branch_id,occurrence_id=plan.draw.event_id,
            request=request,calendar=calendar,state=state,payload=revision.payload,
            revision_id=revision.revision_id,content_hash=revision.content_hash)
        if rebuilt!=plan:
            raise ValueError('Scheduled ATP plan differs from its original Saved source')
        return rebuilt

    def _build(self, *, run_id,branch_id,occurrence_id,request,calendar,state,payload,revision_id,content_hash):
        profile,fingerprint,_source,_geometry=validate_saved_atp_knockout_schedule(
            calendar=calendar,state=state,occurrence_id=occurrence_id,request=request)
        component=load_saved_simulation_slot_component(payload,run_id=run_id,branch_id=branch_id) or {}
        if any(r['event_id']==occurrence_id for r in component.get('draw_revisions',())):
            raise ValueError('Revised ATP Draw requires a versioned replacement consumer')
        inputs=[r for r in component.get('draw_inputs',()) if r['event_id']==occurrence_id]
        draws=[r for r in component.get('draw_authorities',()) if r['event_id']==occurrence_id]
        if len(inputs)!=1 or len(draws)!=1:
            raise ValueError('Manual Save of canonical ATP Draw Input and Draw is required')
        inp=TournamentDrawInputAuthority.model_validate_json(inputs[0]['payload_json'])
        draw=TournamentDrawAuthority.model_validate_json(draws[0]['payload_json'])
        if (inp.run_id,inp.branch_id,draw.run_id,draw.branch_id)!=(run_id,branch_id,run_id,branch_id):
            raise ValueError('Saved ATP Draw has a foreign owner')
        return ScheduledKnockoutFeederPlan(source_saved_revision_id=revision_id,source_saved_content_hash=content_hash,
            source_profile_fingerprint=fingerprint,profile=profile,
            profile_payload_fingerprint=canonical_hash(profile.model_dump(mode='json')),
            draw_input=inp,draw=draw,schedule=request.schedule)


def preview_saved_atp_feeders(repository, *, run_id,branch_id,occurrence_id,request):
    plan=SavedATPScheduledFeederService(repository).prepare(run_id=run_id,branch_id=branch_id,
        occurrence_id=occurrence_id,request=request)
    current=plan.schedule.qualification[0]
    progress,due=scheduled_knockout_progress(plan=plan,matches=(),positions={},current=current)
    return {'schema_version':'saved_atp_scheduled_feeder_preview.v1','run_id':run_id,'branch_id':branch_id,
        'saved_head_revision_id':plan.source_saved_revision_id,'source_content_hash':plan.source_saved_content_hash,
        'profile_fingerprint':plan.source_profile_fingerprint,'feeder_plan_fingerprint':plan.fingerprint,
        'draw_fingerprint':plan.draw.fingerprint,'schedule_fingerprint':plan.schedule.fingerprint,
        'executable_match_count':len(plan.topology.plans),'initial_round_matches':[m.model_dump(mode='json') for m in due],
        'qualification_blocking_main':progress.main_blocked_by_qualification,'run_mutated':False,
        'readiness_scope':'scheduled_feeder_only','sporting_execution_ready':False,
        'qualification_dates_verified':plan.profile.qualification_date_status == 'verified'}
