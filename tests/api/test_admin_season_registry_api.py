from fastapi.testclient import TestClient

from beta_engine.main import app


def test_admin_season_registry_response() -> None:
    client = TestClient(app)
    response = client.get('/admin/seasons/registry')
    assert response.status_code == 200
    payload = response.json()
    assert payload['start_season'] == '2000/01'
    assert payload['end_season'] == '2039/40'
    assert payload['season_count'] == 40
    assert payload['week_count'] == 61
    assert payload['season_week_1_year_week'] == 37
    assert len(payload['seasons']) == 40
