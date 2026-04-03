from __future__ import annotations

from statistics import mean

from beta_engine.core import DeterministicRng, SeedScope
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.entries import AcceptanceStatus, EntryEngine
from beta_engine.domain.players import HiddenCareerTraits, Player, PlayerGenerator
from beta_engine.infrastructure.entry_config import load_entry_tuning_config
from beta_engine.infrastructure.tournament_config import (
    load_season_calendar,
    load_tournament_templates_config,
)
from beta_engine.infrastructure.world_config import load_countries_config, load_player_identity_config


def _players(seed: int, per_country: int = 30) -> tuple[list[Player], dict[str, Country]]:
    countries = load_countries_config().countries
    generator = PlayerGenerator(
        rng=DeterministicRng(seed),
        identity_config=load_player_identity_config(),
        country_talent_model=CountryTalentModel(),
    )
    players: list[Player] = []
    for country in countries:
        players.extend(
            generator.generate(country=country, sequence=i + 1)
            for i in range(per_country)
        )
    return players, {country.code: country for country in countries}


def _event_and_template(event_id: str):
    calendar = load_season_calendar()
    templates = load_tournament_templates_config()
    event = next(e for e in calendar.events if e.event_id == event_id)
    template = next(t for t in templates.templates if t.template_id == event.template_id)
    return event, template


def test_same_seed_and_inputs_generate_same_acceptance_outcomes() -> None:
    players, countries = _players(seed=77)
    event, template = _event_and_template("ev_2027_w01_qatar_platinum")

    engine_a = EntryEngine(rng=DeterministicRng(701), tuning=load_entry_tuning_config())
    engine_b = EntryEngine(rng=DeterministicRng(701), tuning=load_entry_tuning_config())

    result_a = engine_a.build_acceptance_list(
        event=event,
        template=template,
        players=players,
        countries_by_code=countries,
    )
    result_b = engine_b.build_acceptance_list(
        event=event,
        template=template,
        players=players,
        countries_by_code=countries,
    )

    assert result_a.model_dump() == result_b.model_dump()


def test_strong_and_ambitious_players_enter_higher_level_more_often() -> None:
    event, template = _event_and_template("ev_2027_w01_qatar_platinum")
    country = Country(
        code="TST",
        name="Testland",
        region="EUROPE",
        population=1_000_000,
        flag_asset=None,
        squash_popularity=3,
        wealth_support=3,
        squash_tradition=3,
        system_quality=3,
    )

    base_hidden = {
        "potential_ceiling": 85,
        "growth_curve": "balanced",
        "injury_proneness": 0.2,
        "resilience": 0.7,
    }
    strong = Player(
        player_id="TST-STRONG",
        name="Strong Player",
        age=26,
        nationality="TST",
        technique=92,
        movement=91,
        physical=90,
        mental=88,
        consistency=87,
        clutch=88,
        recovery=86,
        play_style="attacking",
        archetype="all_court",
        hidden_career_traits=HiddenCareerTraits(
            **base_hidden,
            ambition=0.9,
            professionalism=0.9,
            travel_tolerance=0.7,
            schedule_aggression=0.6,
        ),
    )
    weak = Player(
        player_id="TST-WEAK",
        name="Weak Player",
        age=31,
        nationality="TST",
        technique=56,
        movement=54,
        physical=57,
        mental=53,
        consistency=52,
        clutch=51,
        recovery=55,
        play_style="counter",
        archetype="defensive",
        hidden_career_traits=HiddenCareerTraits(
            **base_hidden,
            ambition=0.2,
            professionalism=0.3,
            travel_tolerance=0.4,
            schedule_aggression=0.25,
        ),
    )

    strong_entries = 0
    weak_entries = 0
    for seed in range(140, 260):
        engine = EntryEngine(rng=DeterministicRng(seed), tuning=load_entry_tuning_config())
        event_rng = engine.rng.branch(SeedScope.WEEK, event.season, event.week, event.event_id)
        strong_decision = engine.decide_entry(
            player=strong,
            player_country=country,
            event=event,
            template=template,
            event_rng=event_rng,
        )
        weak_decision = engine.decide_entry(
            player=weak,
            player_country=country,
            event=event,
            template=template,
            event_rng=event_rng,
        )
        if strong_decision.target.value != "NONE":
            strong_entries += 1
        if weak_decision.target.value != "NONE":
            weak_entries += 1

    assert strong_entries > weak_entries


def test_travel_metadata_changes_entry_likelihood() -> None:
    event, template = _event_and_template("ev_2027_w01_qatar_platinum")
    player = Player(
        player_id="TRV-001",
        name="Traveler",
        age=27,
        nationality="TRV",
        technique=78,
        movement=78,
        physical=77,
        mental=76,
        consistency=76,
        clutch=75,
        recovery=77,
        play_style="balanced",
        archetype="all_court",
        hidden_career_traits=HiddenCareerTraits(
            potential_ceiling=90,
            growth_curve="late_bloom",
            professionalism=0.8,
            ambition=0.7,
            travel_tolerance=0.8,
            schedule_aggression=0.6,
            injury_proneness=0.2,
            resilience=0.75,
        ),
    )
    high_affinity_country = Country(
        code="TRV",
        name="Travelerland",
        region="MIDDLE_EAST",
        population=1_000_000,
        flag_asset=None,
        squash_popularity=3,
        wealth_support=3,
        squash_tradition=3,
        system_quality=3,
    )
    low_affinity_country = high_affinity_country.model_copy(
        update={"region": "AFRICA"}
    )

    high_probs = []
    low_probs = []
    for seed in range(100, 180):
        engine = EntryEngine(rng=DeterministicRng(seed), tuning=load_entry_tuning_config())
        event_rng = engine.rng.branch(SeedScope.WEEK, event.season, event.week, event.event_id)
        high_probs.append(
            engine.decide_entry(
                player=player,
                player_country=high_affinity_country,
                event=event,
                template=template,
                event_rng=event_rng,
            ).entry_probability
        )
        low_probs.append(
            engine.decide_entry(
                player=player,
                player_country=low_affinity_country,
                event=event,
                template=template,
                event_rng=event_rng,
            ).entry_probability
        )

    assert mean(high_probs) > mean(low_probs)


def test_acceptance_lists_include_required_structures_and_placeholders() -> None:
    players, countries = _players(seed=123, per_country=20)
    event, template = _event_and_template("ev_2027_w03_england_gold")
    engine = EntryEngine(rng=DeterministicRng(909), tuning=load_entry_tuning_config())

    acceptance = engine.build_acceptance_list(
        event=event,
        template=template,
        players=players,
        countries_by_code=countries,
    )

    assert acceptance.event_id == event.event_id
    assert acceptance.pending_week_conflict_resolution is True

    assert any(entry.status == AcceptanceStatus.DIRECT_ACCEPTANCE for entry in acceptance.main_draw_entries)
    assert any(entry.status == AcceptanceStatus.QUALIFICATION_ACCEPTANCE for entry in acceptance.qualification_entries)
    assert any(entry.status == AcceptanceStatus.WILD_CARD_PLACEHOLDER for entry in acceptance.main_draw_entries)
    assert any(entry.status == AcceptanceStatus.WITHDRAWAL_PLACEHOLDER for entry in acceptance.main_draw_entries)
    assert any(entry.status == AcceptanceStatus.LATE_REPLACEMENT_PLACEHOLDER for entry in acceptance.main_draw_entries)

    for entry in acceptance.main_draw_entries + acceptance.qualification_entries:
        payload = entry.model_dump()
        assert "event_id" in payload
        assert "status" in payload
        assert "slot" in payload
        assert "tour_level" in payload
