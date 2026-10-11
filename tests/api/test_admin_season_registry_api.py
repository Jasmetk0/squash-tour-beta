from __future__ import annotations

from test_admin_lifecycle_api import Server, call


def test_admin_season_registry_response(tmp_path) -> None:
    with Server(tmp_path) as server:
        status, payload = call('GET', f'{server.base_url}/admin/seasons/registry')

    assert status == 200
    assert payload['start_season'] == '2000/01'
    assert payload['end_season'] == '2049/50'
    assert payload['season_count'] == 50
    assert payload['week_count'] == 61
    assert payload['season_week_1_year_week'] == 37
    assert len(payload['seasons']) == 50
    assert payload['seasons'][0]['label'] == '2000/01'
    assert payload['seasons'][-1]['label'] == '2049/50'
