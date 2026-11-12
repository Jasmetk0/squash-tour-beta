"""Physical ATP Package/Draw Save, cold reopen and original-source isolation."""
import json
import pytest

from beta_engine.application.saved_atp_scheduled_feeders import SavedATPScheduledFeederService
from beta_engine.application.atp_knockout_schedule_preview import ATPKnockoutSchedulePreviewRequest
from beta_engine.infrastructure.db.models import PublishedOfficialRankingModel, TournamentDrawAuthorityModel, BranchSavedRevisionModel
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import TournamentRankingSnapshotAuthorityStore
from beta_engine.infrastructure.db.tournament_entry_field import TournamentEntryFieldStore
from beta_engine.infrastructure.db.tournament_wild_card_authority import TournamentWildCardAuthorityStore
from beta_engine.infrastructure.db.tournament_draw_input_authority import TournamentDrawInputAuthorityStore
from beta_engine.infrastructure.db.tournament_draw_authority import TournamentDrawAuthorityStore
from beta_engine.domain.tournaments.entry_field import TournamentEntryApplication, TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.scheduled_knockout_feeders import ScheduledKnockoutFeederPlan
from tests.api.test_atp_saved_run_week_preview_api import _make_run
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.api.viewer_saved_revision_helpers import save_simulation
from tests.infrastructure.test_tournament_draw_authority import ranking_snapshot
from tests.api.test_run_calendar_extension_commit_api import _review, _save
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.tournaments.knockout_run_schedule import KnockoutRoundPosition
from beta_engine.domain.tournaments.scheduled_knockout_feeders import scheduled_knockout_progress

pytestmark=pytest.mark.pr_critical


def test_saved_atp_draw_reopens_without_reading_live_draw_and_rejects_corruption(tmp_path):
    database=f"sqlite:///{tmp_path/'saved-atp.db'}"
    with ApiServer(database_url=database) as server:
        r,b=_make_run(server,name='Saved ATP Draw',start=2025,count=2)
        root=server.base_url+f'/admin/runs/{r}/branches/{b}'
        package=root+'/packages/source-atp-reference-calendar'
        working=server.base_url+f'/run-containers/{r}/branches/{b}/working-draft'
        code,review=_request('POST',package+'/preview',{});assert code==200,review
        code,applied=_request('POST',package+'/confirm',{
            'command_id':'source','expected_head_revision_id':review['saved_head_revision_id'],
            'expected_draft_version':review['draft_version'],'expected_state_fingerprint':review['current_state_fingerprint'],
            'expected_preview_fingerprint':review['preview_fingerprint'],'conflict_resolutions':{},
        });assert code==200,applied
        code,saved=_request('POST',working+'/save',{'expected_draft_version':applied['draft_version']});assert code==201,saved
        code,catalog=_request('GET',root+'/calendar-tour/atp-source-editions');assert code==200,catalog
        entry=catalog['entries'][2]
        clock={'schema_version':'run_calendar.v1','weeks_per_year':52,'season_start_year_week':1,'start_year':2025,'season_count':2}
        def position(w,s): return {'week':{'calendar':clock,'season_index':0,'week':w},'slot':s}
        body={'expected_saved_head':catalog['saved_head_revision_id'],'expected_profile_fingerprint':entry['profile_fingerprint'],
              'schedule':{'calendar':clock,'qualification':[position(5,1),position(5,2)],'main':[position(6,s) for s in range(1,6)]}}
        url=root+'/calendar-tour/atp-source-editions/atp_2025_rotterdam/feeder-preview'
        repo=server.app.state.runtime.repository
        service=SavedATPScheduledFeederService(repo)
        code,error=_request('POST',url,body);assert code==409,error
        assert 'Manual Save' in error['detail']['message']

        # Disposable subsystem authorities explicitly supply eligible players.
        # This is not native Turn Pro/Entry or a W52 publication acceptance proof.
        players=tuple(f'P{i:03d}' for i in range(44))
        snapshot=ranking_snapshot(players).model_copy(update={'run_id':r,'branch_id':b})
        scope={'run_id':r,'branch_id':b,'event_id':'atp_2025_rotterdam'}
        with repo._session_factory.begin() as session:
            session.add(PublishedOfficialRankingModel(run_id=r,branch_id=b,week_ordinal=snapshot.week.ordinal,
                snapshot_fingerprint=snapshot.fingerprint,payload_json=snapshot.model_dump_json()))
        def stage_draw(event, seed):
            target={'run_id':r,'branch_id':b,'event_id':event}
            with repo._session_factory.begin() as session:
                TournamentRankingSnapshotAuthorityStore(session).adopt(**target,ranking_week=snapshot.week,command_id=f'{event}-ranking')
                TournamentEntryFieldStore(session).stage_initial(**target,command_id=f'{event}-field',
                    capacity=TournamentEntryFieldCapacity.for_main_entrant_count(main_entrant_count=32,qualification_draw_size=16,qualifier_spots=4,wild_card_slots=4),
                    applications=tuple(TournamentEntryApplication(application_id=f'{event}-app-{p}',**target,player_id=p,entry_window='main',
                        decision_slot_ordinal=10,nr_tie_break_token=p,eligible=True) for p in players[:-4]))
                TournamentWildCardAuthorityStore(session).resolve(**target,command_id=f'{event}-wc',original_wild_card_player_ids=players[-4:])
                TournamentDrawInputAuthorityStore(session).commit(**target,command_id=f'{event}-input',draw_seed=seed)
                return TournamentDrawAuthorityStore(session).generate(**target,command_id=f'{event}-draw')
        draw=stage_draw(scope['event_id'],555)
        # The live Draw is deliberately insufficient until ordinary manual Save.
        assert _request('POST',url,body)[0]==409
        save_simulation(server,r,b)
        body['expected_saved_head']=repo.get_branch_revision_state(branch_id=b).saved_head_revision_id
        request=ATPKnockoutSchedulePreviewRequest.model_validate_json(json.dumps(body))
        before=_request('GET',working)
        plan=service.prepare(run_id=r,branch_id=b,occurrence_id=scope['event_id'],request=request)
        assert len(plan.topology.plans)==43
        assert plan.draw.fingerprint==draw.fingerprint
        assert plan.source_saved_revision_id==body['expected_saved_head']
        code,report=_request('POST',url,body);assert code==200,report
        assert report['feeder_plan_fingerprint']==plan.fingerprint
        assert report['executable_match_count']==43 and len(report['initial_round_matches'])==8
        assert report['qualification_blocking_main'] and not report['sporting_execution_ready']
        assert _request('GET',working)==before
        assert _request('POST',url,{**body,'expected_saved_head':'stale'})[0]==409
        encoded=plan.model_dump_json()
        reviewed_fingerprint=plan.fingerprint
        # Another legitimate Save changes HEAD, while the original root remains reachable.
        stage_draw('unrelated_tournament',556)
        save_simulation(server,r,b)
        assert repo.get_branch_revision_state(branch_id=b).saved_head_revision_id != plan.source_saved_revision_id
        assert service.reload(plan,run_id=r,branch_id=b,expected_plan_fingerprint=reviewed_fingerprint)==plan
        original_source=next(row for row in repo.get_branch_saved_revision_history(run_id=r,branch_id=b).saved_revisions
                             if row.revision_id==plan.source_saved_revision_id)
        source_bytes=json.dumps(original_source.payload,sort_keys=True)
        code,reviewed=_review(server,r,3);assert code==200,reviewed
        assert reviewed['can_save'],reviewed
        code,extended=_save(server,r,reviewed,'atp-schedule-horizon-extension');assert code==200,extended
        assert extended['saved'] and not extended['simulation_started']
        runtime=RunCalendar.from_metadata(reviewed['proposed_calendar'])
        restored=service.reload(plan,run_id=r,branch_id=b,expected_plan_fingerprint=reviewed_fingerprint)
        current=KnockoutRoundPosition(week=RunWeekPosition(calendar=runtime,season_index=0,week=5),slot=1)
        _,due=scheduled_knockout_progress(plan=restored,matches=(),positions={},current=current)
        assert len(due)==8
        assert restored.model_dump_json()==encoded
        unchanged=next(row for row in repo.get_branch_saved_revision_history(run_id=r,branch_id=b).saved_revisions
                       if row.revision_id==plan.source_saved_revision_id)
        assert unchanged.content_hash==original_source.content_hash
        assert json.dumps(unchanged.payload,sort_keys=True)==source_bytes
        # Tamper ONLY live Draw data. An immutable source read must ignore it.
        with repo._session_factory.begin() as session:
            row=session.query(TournamentDrawAuthorityModel).filter_by(run_id=r,branch_id=b,event_id=scope['event_id']).one()
            row.payload_json='{}'
        assert service.reload(plan,run_id=r,branch_id=b,expected_plan_fingerprint=reviewed_fingerprint)==plan

    with ApiServer(database_url=database) as reopened:
        repo=reopened.app.state.runtime.repository
        service=SavedATPScheduledFeederService(repo)
        plan=ScheduledKnockoutFeederPlan.model_validate_json(encoded)
        assert service.reload(plan,run_id=r,branch_id=b,expected_plan_fingerprint=reviewed_fingerprint)==plan
        code,reviewed=_review(reopened,r,4);assert code==200,reviewed
        assert reviewed['original_calendar']['season_count']==3
        runtime=RunCalendar.from_metadata(reviewed['original_calendar'])
        current=KnockoutRoundPosition(week=RunWeekPosition(calendar=runtime,season_index=0,week=5),slot=1)
        _,due=scheduled_knockout_progress(plan=plan,matches=(),positions={},current=current)
        assert len(due)==8
        with pytest.raises(ValueError): service.reload(plan,run_id=r,branch_id='foreign',expected_plan_fingerprint=reviewed_fingerprint)
        with pytest.raises(ValueError,match='reviewed binding'):
            service.reload(plan,run_id=r,branch_id=b,expected_plan_fingerprint='f'*64)
        for patch in ({'source_saved_content_hash':'f'*64},{'source_saved_revision_id':'unreachable'}):
            altered=plan.model_copy(update=patch)
            with pytest.raises(ValueError,match='unreachable or its Saved envelope'):
                service.reload(altered,run_id=r,branch_id=b,expected_plan_fingerprint=altered.fingerprint)
        with repo._session_factory.begin() as session:
            row=session.get(BranchSavedRevisionModel,plan.source_saved_revision_id)
            payload=json.loads(row.payload_json);payload['injected_corruption']=True
            row.payload_json=json.dumps(payload)
        with pytest.raises(ValueError): service.reload(plan,run_id=r,branch_id=b,expected_plan_fingerprint=reviewed_fingerprint)
