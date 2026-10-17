"""Read-only preview -> real 57-backed MatchEngine -> immutable Save/cold replay."""
import pytest
from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_standalone_match_flow import prepare_saved_world
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_saved_revision_history_api import ApiServer,_request
from tests.api.test_player_generation_calendar_gate import _dump

pytestmark=pytest.mark.pr_critical


@pytest.mark.parametrize('clock',[RunCalendar(52,35,2030,3),RunCalendar(80,80,2100,3)])
def test_preview_is_read_only_and_exact_canonical_source_is_played_saved_restarted(tmp_path,clock):
    path=tmp_path/'canonical.db';db=f'sqlite:///{path}'
    with ApiServer(database_url=db) as server:
        repo,head=prepare_saved_world(server,clock)
        _,view=_request('GET',base(server))
        request=dict(expected_saved_head=head,expected_initial_world_fingerprint=view['initial_world_fingerprint'],entrant_ids=view['player_ids'])
        before=_dump(path)
        code,preview=_request('POST',base(server)+'/canonical-preview',request)
        assert code==200,preview
        assert _dump(path)==before
        assert _request('POST',base(server)+'/canonical-preview',request)==(200,preview)
        assert all(len(p['attributes'])==57 for p in preview['source']['records'])
        assert _request('POST',base(server)+'/canonical-preview',{**request,'expected_saved_head':'stale'})[0]==409
        assert _request('POST',base(server)+'/canonical-preview',{**request,'entrant_ids':[view['player_ids'][0]]*4})[0]==409
        cmd=dict(**request,command_id='canonical-play',match_id='canonical-play',seed=672,
            operator_label='Admin',audit_reason='Frozen 57-attribute projection')
        code,played=_request('POST',base(server)+'/simulate',cmd)
        assert code==201,played
        ko=played['knockout'];assert ko['schema_version']=='calendar_opening_knockout.v4'
        assert ko['canonical_source']==preview['source']
        assert all(len(p['canonical_attributes'])==57 for m in ko['matches'] for p in m['canonical_projections'])
        assert _request('POST',base(server)+'/simulate',cmd)==(201,played)
        _,proof=_request('GET',base(server)+'/save/preview')
        code,saved=_request('POST',base(server)+'/save',dict(expected_draft_version=proof['draft_version'],expected_calendar_match_fingerprint=played['fingerprint']))
        assert code==201,saved
        saved_id=saved['saved_revision']['revision_id']
        assert repo.verify_branch_saved_revision_hash(revision_id=head)
        assert repo.verify_branch_saved_revision_hash(revision_id=saved_id)
        assert _request('GET',base(server)+'/canonical-play/replay')[1]['exact_replay']
    with ApiServer(database_url=db) as restarted:
        code,view=_request('GET',base(restarted))
        assert code==200 and view['saved'],view
        assert view['knockout']==ko
        assert _request('GET',base(restarted)+'/canonical-play/replay')[1]['exact_replay']
