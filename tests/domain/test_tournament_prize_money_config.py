from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.domain.tournaments.models import CalendarEvent, TournamentTemplate


pytestmark = pytest.mark.pr_critical


def _template(**updates):
    payload = {
        "template_id": "wt_test",
        "tour_level": "WORLD_TOUR",
        "category": "TEST",
        "event_name": "Prize Test",
        "region": "Europe",
        "host_country": "CZE",
        "main_draw_size": 32,
        "qualification_draw_size": 16,
        "seeds_count": 8,
        "qualifier_spots": 4,
        "wild_cards": 2,
        "byes": 0,
        "lucky_loser_rules": {
            "enabled": True,
            "max_spots": 2,
            "replacement_window": "pre_main_draw_round_1",
        },
        "point_distribution_ref": "world",
        "event_duration_days": 6,
        "qualification_duration_days": 2,
    }
    payload.update(updates)
    return TournamentTemplate.model_validate(payload)


def test_partial_prize_money_table_preserves_unknown_stages_and_currency():
    template = _template(
        prize_money_currency="usd",
        prize_money_table={
            "qualification_final": 500,
            "round_of_32": None,
            "round_of_16": 1500,
            "finalist": 6000,
            "champion": 10000,
        },
    )

    assert template.prize_money_currency == "USD"
    assert template.prize_money_table["round_of_32"] is None
    assert template.prize_money_table["qualification_final"] == 500
    assert template.prize_money_table["champion"] == 10000


def test_known_prize_money_payout_requires_currency():
    with pytest.raises(
        ValidationError,
        match="Configured prize-money payouts require prize_money_currency",
    ):
        _template(
            prize_money_table={
                "finalist": 6000,
                "champion": 10000,
            }
        )


def test_known_prize_money_payouts_must_strictly_increase_by_stage():
    with pytest.raises(
        ValidationError,
        match="must strictly increase with finishing stage",
    ):
        _template(
            prize_money_currency="EUR",
            prize_money_table={
                "semifinal": 5000,
                "finalist": 5000,
                "champion": 10000,
            },
        )


def test_legacy_prize_money_total_does_not_invent_stage_payouts():
    template = _template(prize_money=100000)

    assert template.prize_money == 100000
    assert template.prize_money_currency is None
    assert template.prize_money_table == {}


def test_calendar_event_revalidates_canonical_prize_money_contract():
    event = CalendarEvent(
        event_id="evt-test",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=37,
        template_id="wt_test",
        event_name="Prize Test",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=32,
        qualification_draw_size=16,
        prize_money_currency="gbp",
        prize_money_table={
            "qualification_final": 250,
            "quarterfinal": 2000,
            "semifinal": 3500,
            "finalist": 6000,
            "champion": 10000,
        },
    )

    assert event.prize_money_currency == "GBP"

    payload = event.model_dump(mode="json", exclude_computed_fields=True)
    payload["prize_money_table"]["finalist"] = 3000
    with pytest.raises(
        ValidationError,
        match="must strictly increase with finishing stage",
    ):
        CalendarEvent.model_validate(payload)
