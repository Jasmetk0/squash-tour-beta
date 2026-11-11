import pytest
from tests.api.test_atp_saved_run_week_preview_api import _make_run
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark=pytest.mark.pr_critical


def test_saved_cross_week_schedule_preview_keeps_main_date_and_never_commits(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path/'schedule.db'}") as server:
        r,b=_make_run(server,name='ATP phase schedule',start=2025,count=2)
        root=server.base_url+f'/admin/runs/{r}/branches/{b}'
        source=root+'/packages/source-atp-reference-calendar'
        working=server.base_url+f'/run-containers/{r}/branches/{b}/working-draft'
        code,review=_request('POST',source+'/preview',{})
        assert code==200,review
        code,applied=_request('POST',source+'/confirm',{
            'command_id':'schedule-source','expected_head_revision_id':review['saved_head_revision_id'],
            'expected_draft_version':review['draft_version'],'expected_state_fingerprint':review['current_state_fingerprint'],
            'expected_preview_fingerprint':review['preview_fingerprint'],'conflict_resolutions':{},
        })
        assert code==200,applied
        code,saved=_request('POST',working+'/save',{'expected_draft_version':applied['draft_version']})
        assert code==201,saved
        code,catalog=_request('GET',root+'/calendar-tour/atp-source-editions')
        assert code==200,catalog
        profile=catalog['entries'][2]
        clock=profile['calendar_projection']['run_weeks'][0]
        # Source windows constrain weeks; exact round slots remain an Admin proposal.
        calendar={'schema_version':'run_calendar.v1','weeks_per_year':52,'season_start_year_week':1,'start_year':2025,'season_count':2}
        def position(week,slot):
            return {'week':{'calendar':calendar,'season_index':clock['season_index'],'week':week},'slot':slot}
        request={'expected_saved_head':catalog['saved_head_revision_id'],
                 'expected_profile_fingerprint':profile['profile_fingerprint'],
                 'schedule':{'calendar':calendar,'qualification':[position(5,1),position(5,2)],
                             'main':[position(6,n) for n in range(1,6)]}}
        url=root+'/calendar-tour/atp-source-editions/atp_2025_rotterdam/schedule-preview'
        before=_request('GET',working)
        code,plan=_request('POST',url,request)
        assert code==200,plan
        assert plan['actual_match_count']==43
        assert plan['schedule']['qualification'][0]['week']['week']==5
        assert plan['schedule']['main'][0]['week']['week']==6
        assert plan['qualification_dates_verified'] is True
        assert plan['sporting_execution_ready'] is plan['run_mutated'] is False
        assert plan['source_qualification_projection']['run_ordinals'] == [4]
        assert plan['source_qualification_projection']['source_start_date'] == '2025-02-01'
        assert _request('POST',url,request)==(code,plan)
        for patch in ({'expected_saved_head':'stale'},{'expected_profile_fingerprint':'a'*64}):
            assert _request('POST',url,{**request,**patch})[0]==409
        shifted={**request['schedule'],'main':[position(7,n) for n in range(1,6)]}
        assert _request('POST',url,{**request,'schedule':shifted})[0]==409
        wrong_q={**request['schedule'],'qualification':[position(4,1),position(4,2)]}
        code,rejected=_request('POST',url,{**request,'schedule':wrong_q})
        assert code==409 and 'Qualification source weeks' in rejected['detail']['message']
        missing_round={**request['schedule'],'qualification':[position(5,1)]}
        assert _request('POST',url,{**request,'schedule':missing_round})[0]==409
        invalid_slot={**request['schedule'],'qualification':[position(5,True),position(5,2)]}
        assert _request('POST',url,{**request,'schedule':invalid_slot})[0]==422
        group_url=root+'/calendar-tour/atp-source-editions/atp_2025_atp_finals/schedule-preview'
        assert _request('POST',group_url,request)[0]==409
        assert _request('GET',working)==before
