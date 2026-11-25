"""Real Package copy/Save and cold SQLite reopen for v1/v2 date knowledge."""
import json
from pathlib import Path

import pytest

from beta_engine.application.atp_historical_calendar_adapter import ATPHistoricalCalendarAdapter
from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package
from tests.api.test_atp_saved_run_week_preview_api import _make_run
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize('version',[2,4,5,6],ids=['historical-v1','dallas-source-v4','munich-vienna-v5','finals-source-v6'])
def test_saved_date_knowledge_survives_current_default_changes_and_cold_restart(tmp_path,monkeypatch,version):
    verified = version >= 4
    database=f"sqlite:///{tmp_path/'qualification.db'}"
    document=ATPHistoricalCalendarAdapter().build_document()
    if version < 6:
        legacy=Path(__file__).parents[1]/f'fixtures/atp/squash_sporting_profiles_source_v{version}.json'
        (tmp_path/'squash_sporting_profiles_v1.json').write_bytes(legacy.read_bytes())
        old=build_atp_sporting_package(tmp_path)
        document=document.model_copy(update={'source_version':version+1,'children':(*document.children[:-1],old)})
    with ApiServer(database_url=database) as server:
        r,b=_make_run(server,name='Saved phase chronology',start=2025,count=2)
        root=server.base_url+f'/admin/runs/{r}/branches/{b}'
        working=server.base_url+f'/run-containers/{r}/branches/{b}/working-draft'
        source=root+'/packages/source-atp-reference-calendar'
        with monkeypatch.context() as copying:
            copying.setattr(ATPHistoricalCalendarAdapter,'build_document',lambda self:document)
            code,review=_request('POST',source+'/preview',{});assert code==200,review
            code,applied=_request('POST',source+'/confirm',{
                'command_id':'copy-phases','expected_head_revision_id':review['saved_head_revision_id'],
                'expected_draft_version':review['draft_version'],'expected_state_fingerprint':review['current_state_fingerprint'],
                'expected_preview_fingerprint':review['preview_fingerprint'],'conflict_resolutions':{},
            });assert code==200,applied
            code,saved=_request('POST',working+'/save',{'expected_draft_version':applied['draft_version']});assert code==201,saved
        repo=server.app.state.runtime.repository
        revision=repo.get_branch_saved_revision(revision_id=repo.get_branch_revision_state(branch_id=b).saved_head_revision_id)
        saved_body=json.dumps(revision.payload,sort_keys=True)
        saved_hash=revision.content_hash
        code,catalog=_request('GET',root+'/calendar-tour/atp-source-editions');assert code==200,catalog
        entries = {entry["profile"]["occurrence_id"]: entry for entry in catalog["entries"]}
        assert ("atp_2025_dallas" in entries) is verified
        assert ("atp_2025_munich" in entries) is (version >= 5)
        assert ("atp_2025_vienna" in entries) is (version >= 5)
        assert ("atp_2024_atp_finals" in entries) is (version == 6)
        assert ("atp_2024_next_gen_atp_finals" in entries) is (version == 6)
        for occurrence_id in ("atp_2025_doha", "atp_2025_dubai", "atp_2025_halle", "atp_2024_dubai", "atp_2024_halle", "atp_2024_stuttgart", "atp_2025_stuttgart", "atp_2025_queens_club", "atp_2024_delray_beach", "atp_2025_delray_beach", "atp_2025_houston", "atp_2025_santiago",):
            assert (occurrence_id in entries) is (version == 6)
        if verified:
            dallas = entries["atp_2025_dallas"]
            assert dallas["qualification_calendar_projection"]["run_ordinals"] == [4]
            assert dallas["calendar_projection"]["run_weeks"][0]["season_week"] == 6
        p=entries['atp_2025_rotterdam']
        assert p['profile']['qualification_date_status']==('verified' if verified else 'not_verified')
        assert ('qualification_dates_not_verified' in p['execution_blockers']) is not verified
        assert not p['execution_supported']
        if verified:
            assert p['qualification_calendar_projection']['run_ordinals']==[4]
        calendar={'schema_version':'run_calendar.v1','weeks_per_year':52,'season_start_year_week':1,'start_year':2025,'season_count':2}
        def pos(w,s):return {'week':{'calendar':calendar,'season_index':0,'week':w},'slot':s}
        request={'expected_saved_head':catalog['saved_head_revision_id'],'expected_profile_fingerprint':p['profile_fingerprint'],
            'schedule':{'calendar':calendar,'qualification':[pos(5,1),pos(5,2)],'main':[pos(6,n) for n in range(1,6)]}}
        schedule_path=f'/admin/runs/{r}/branches/{b}/calendar-tour/atp-source-editions/atp_2025_rotterdam/schedule-preview'
        code,preview=_request('POST',server.base_url+schedule_path,request);assert code==200,preview
        assert preview['qualification_dates_verified'] is verified
        assert not preview['sporting_execution_ready']
        # Legacy proposals retain their old permissive source-knowledge boundary.
        # Verified v2 rejects moving Q to a week that contradicts its copied facts.
        wrong={**request,'schedule':{**request['schedule'],'qualification':[pos(4,1),pos(4,2)]}}
        assert _request('POST',server.base_url+schedule_path,wrong)[0]==(409 if verified else 200)
        before=_request('GET',working)

    def unavailable(*args,**kwargs):
        raise AssertionError('Saved source must not consult current defaults')
    monkeypatch.setattr(ATPHistoricalCalendarAdapter,'build_document',unavailable)
    with ApiServer(database_url=database) as reopened:
        url=reopened.base_url+f'/admin/runs/{r}/branches/{b}/calendar-tour/atp-source-editions'
        assert _request('GET',url)==(200,catalog)
        assert _request('POST',reopened.base_url+schedule_path,request)==(200,preview)
        assert _request('GET',reopened.base_url+f'/run-containers/{r}/branches/{b}/working-draft')==before
        revision=reopened.app.state.runtime.repository.get_branch_saved_revision(revision_id=revision.revision_id)
        assert revision.content_hash==saved_hash
        assert json.dumps(revision.payload,sort_keys=True)==saved_body
