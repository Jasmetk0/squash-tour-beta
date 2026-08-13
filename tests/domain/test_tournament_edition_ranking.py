import json

import pytest
from pydantic import ValidationError

from beta_engine.domain.tournaments.models import CalendarEvent


def edition(**updates):
    data = dict(event_id="evt", season="2000/01", season_week=1, template_id="tpl", host_country="ENG", region="EUROPE", main_draw_size=8, qualification_draw_size=0)
    data.update(updates)
    return CalendarEvent(**data)


def test_explicit_ranking_status_enum_rejects_unknown_value():
    assert edition(ranking_status="ranked").ranking_status.value == "ranked"
    assert edition(ranking_status="unranked").ranking_status.value == "unranked"
    with pytest.raises(ValidationError):
        edition(ranking_status="exhibition")


def test_ranked_completeness_uses_actual_draw_structure():
    points = {"champion": 100, "finalist": 60, "semifinal": 30, "quarterfinal": 10}
    no_qualification = edition(ranking_points_table=points)
    assert no_qualification.points_table_complete
    assert not any(stage.startswith("qualification") for stage in no_qualification.required_ranking_point_stages)

    with_qualification = edition(qualification_draw_size=16, ranking_points_table=points)
    assert not with_qualification.points_table_complete
    assert with_qualification.missing_required_point_stages == ["qualification_winner", "qualification_final", "qualification_semifinal", "qualification_round"]


def test_malformed_points_are_missing_but_unranked_needs_no_table():
    ranked = edition(ranking_points_table={"champion": True, "finalist": -1, "semifinal": "3", "quarterfinal": 0})
    assert ranked.missing_required_point_stages == ["champion", "finalist", "semifinal"]
    unranked = edition(ranking_status="unranked")
    assert unranked.points_table_complete and unranked.missing_required_point_stages == []


def test_legacy_round_trip_defaults_ranked_and_snapshot_is_stable():
    legacy = edition().model_dump(mode="json", exclude={"ranking_status", "ranking_points_table"}, exclude_computed_fields=True)
    restored = CalendarEvent.model_validate(json.loads(json.dumps(legacy)))
    assert restored.ranking_status.value == "ranked"
    points = {"champion": 1, "finalist": 1, "semifinal": 1, "quarterfinal": 1}
    stored = edition(ranking_points_table=points)
    points["champion"] = 999
    assert stored.ranking_points_table["champion"] == 1
