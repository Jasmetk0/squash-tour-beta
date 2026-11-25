import pytest
from tests.api.test_atp_saved_run_week_preview_api import _make_run
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark=pytest.mark.pr_critical


@pytest.mark.parametrize("series_id", ["rotterdam", "dallas"])
def test_saved_cross_week_schedule_preview_keeps_main_date_and_never_commits(tmp_path, series_id):
    occurrence_id = f"atp_2025_{series_id}"
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
        profile = next(entry for entry in catalog["entries"]
                       if entry["profile"]["occurrence_id"] == occurrence_id)
        clock=profile['calendar_projection']['run_weeks'][0]
        assert clock["season_week"] == 6
        assert profile["qualification_calendar_projection"]["run_weeks"] == [
            {"season_index": 0, "season_week": 5}
        ]
        # Source windows constrain weeks; exact round slots remain an Admin proposal.
        calendar={'schema_version':'run_calendar.v1','weeks_per_year':52,'season_start_year_week':1,'start_year':2025,'season_count':2}
        def position(week,slot):
            return {'week':{'calendar':calendar,'season_index':clock['season_index'],'week':week},'slot':slot}
        request={'expected_saved_head':catalog['saved_head_revision_id'],
                 'expected_profile_fingerprint':profile['profile_fingerprint'],
                 'schedule':{'calendar':calendar,'qualification':[position(5,1),position(5,2)],
                             'main':[position(6,n) for n in range(1,6)]}}
        url=root+f'/calendar-tour/atp-source-editions/{occurrence_id}/schedule-preview'
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


@pytest.mark.parametrize(
    ("offset", "start", "expected"),
    [
        (1, 2025, {"munich": (0, 15, 16), "vienna": (0, 42, 43),
                   "doha": (0, 7, 8), "dubai": (0, 8, 9), "halle": (0, 24, 25), "stuttgart": (0, 23, 24), "queens_club": (0, 24, 25)}),
        (37, 2024, {"munich": (0, 31, 32), "vienna": (1, 6, 7),
                     "doha": (0, 23, 24), "dubai": (0, 24, 25), "halle": (0, 40, 41), "stuttgart": (0, 39, 40), "queens_club": (0, 40, 41)}),
        (1, 2024, {"atp_2024_dubai": (0, 8, 9), "atp_2024_halle": (0, 24, 25), "atp_2024_stuttgart": (0, 23, 24)}),
        (37, 2023, {"atp_2024_dubai": (0, 24, 25), "atp_2024_halle": (0, 40, 41), "atp_2024_stuttgart": (0, 39, 40)}),
    ],
    ids=["2025-calendar-year", "2025-shifted-year", "2024-calendar-year", "2024-shifted-year"],
)
def test_new_atp_profiles_import_save_preview_and_cold_reopen(tmp_path, monkeypatch, offset, start, expected):
    import json
    from beta_engine.application.atp_historical_calendar_adapter import ATPHistoricalCalendarAdapter

    database = f"sqlite:///{tmp_path / 'new-atp.db'}"
    with ApiServer(database_url=database) as server:
        r, b = _make_run(server, name="New ATP phases", start=start, count=2, offset=offset)
        root_path = f"/admin/runs/{r}/branches/{b}"
        working_path = f"/run-containers/{r}/branches/{b}/working-draft"
        root = server.base_url + root_path
        working = server.base_url + working_path
        source = root + "/packages/source-atp-reference-calendar"
        catalog_path = "/calendar-tour/atp-source-editions"
        code, review = _request("POST", source + "/preview", {})
        assert code == 200, review
        code, applied = _request("POST", source + "/confirm", {
            "command_id": "import-new-atp",
            "expected_head_revision_id": review["saved_head_revision_id"],
            "expected_draft_version": review["draft_version"],
            "expected_state_fingerprint": review["current_state_fingerprint"],
            "expected_preview_fingerprint": review["preview_fingerprint"],
            "conflict_resolutions": {},
        })
        assert code == 200, applied
        assert _request("GET", root + catalog_path)[0] == 409
        code, saved = _request("POST", working + "/save", {
            "expected_draft_version": applied["draft_version"],
        })
        assert code == 201, saved
        code, catalog = _request("GET", root + catalog_path)
        assert code == 200, catalog
        entries = {entry["profile"]["occurrence_id"]: entry for entry in catalog["entries"]}
        repo = server.app.state.runtime.repository
        revision = repo.get_branch_saved_revision(
            revision_id=repo.get_branch_revision_state(branch_id=b).saved_head_revision_id,
        )
        revision_id, saved_hash = revision.revision_id, revision.content_hash
        saved_body = json.dumps(revision.payload, sort_keys=True)
        calendar = {"schema_version": "run_calendar.v1", "weeks_per_year": 52,
                    "season_start_year_week": offset, "start_year": start, "season_count": 2}
        before = _request("GET", working)
        previews = []
        for series_id, (season, qweek, mweek) in expected.items():
            occurrence_id = series_id if series_id.startswith("atp_") else f"atp_2025_{series_id}"
            entry = entries[occurrence_id]
            assert entry["qualification_calendar_projection"]["run_weeks"] == [
                {"season_index": season, "season_week": qweek}]
            assert entry["qualification_calendar_projection"]["run_ordinals"] == [season * 52 + qweek - 1]
            assert entry["calendar_projection"]["run_weeks"][0]["season_index"] == season
            assert entry["calendar_projection"]["run_weeks"][0]["season_week"] == mweek
            assert entry["execution_supported"] is False

            def position(week, slot):
                return {"week": {"calendar": calendar, "season_index": season, "week": week}, "slot": slot}

            request = {
                "expected_saved_head": catalog["saved_head_revision_id"],
                "expected_profile_fingerprint": entry["profile_fingerprint"],
                "schedule": {"calendar": calendar, "qualification": [position(qweek, n) for n in (1, 2)],
                             "main": [position(mweek, n) for n in range(1, 6)]},
            }
            path = catalog_path + f"/{occurrence_id}/schedule-preview"
            code, plan = _request("POST", root + path, request)
            assert code == 200, plan
            assert plan["actual_match_count"] == (39 if occurrence_id.endswith("_stuttgart") else 43)
            assert plan["qualification_dates_verified"] is True
            assert plan["sporting_execution_ready"] is plan["run_mutated"] is False
            assert plan["schedule"]["qualification"][0]["week"]["week"] == qweek
            assert plan["schedule"]["main"][0]["week"]["week"] == mweek
            wrong_q = {**request["schedule"], "qualification": [position(qweek - 1, n) for n in (1, 2)]}
            wrong_m = {**request["schedule"], "main": [position(mweek + 1, n) for n in range(1, 6)]}
            for wrong in (wrong_q, wrong_m):
                assert _request("POST", root + path, {**request, "schedule": wrong})[0] == 409
            previews.append((path, request, plan))
        assert _request("GET", working) == before

    def unavailable(*args, **kwargs):
        raise AssertionError("Saved profiles must not consult the live source")

    monkeypatch.setattr(ATPHistoricalCalendarAdapter, "build_document", unavailable)
    with ApiServer(database_url=database) as reopened:
        root = reopened.base_url + root_path
        assert _request("GET", root + catalog_path) == (200, catalog)
        for path, request, plan in previews:
            assert _request("POST", root + path, request) == (200, plan)
        assert _request("GET", reopened.base_url + working_path) == before
        revision = reopened.app.state.runtime.repository.get_branch_saved_revision(revision_id=revision_id)
        assert revision.content_hash == saved_hash
        assert json.dumps(revision.payload, sort_keys=True) == saved_body
