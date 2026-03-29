from __future__ import annotations

from beta_engine.core import DeterministicRng
from beta_engine.domain.draws import DrawEngine, DrawEntrantType
from beta_engine.domain.entries import EntryEngine
from beta_engine.domain.players import Player, PlayerGenerator
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.infrastructure.entry_config import load_entry_tuning_config
from beta_engine.infrastructure.tournament_config import load_season_calendar, load_tournament_templates_config
from beta_engine.infrastructure.world_config import load_countries_config, load_player_identity_config


def _players(seed: int, per_country: int = 24) -> tuple[list[Player], dict[str, Country]]:
    countries = load_countries_config().countries
    generator = PlayerGenerator(
        rng=DeterministicRng(seed),
        identity_config=load_player_identity_config(),
        country_talent_model=CountryTalentModel(),
    )
    players: list[Player] = []
    for country in countries:
        players.extend(generator.generate(country=country, sequence=i + 1) for i in range(per_country))
    return players, {country.code: country for country in countries}


def _event_and_template(event_id: str):
    calendar = load_season_calendar()
    templates = load_tournament_templates_config()
    event = next(e for e in calendar.events if e.event_id == event_id)
    template = next(t for t in templates.templates if t.template_id == event.template_id)
    return event, template


def _acceptance_for_event(event_id: str, *, seed: int = 440) -> tuple:
    players, countries = _players(seed=95)
    event, template = _event_and_template(event_id)
    entries = EntryEngine(rng=DeterministicRng(seed), tuning=load_entry_tuning_config())
    acceptance = entries.build_acceptance_list(
        event=event,
        template=template,
        players=players,
        countries_by_code=countries,
    )
    return acceptance, template


def test_draw_generation_is_reproducible_for_same_inputs() -> None:
    acceptance, template = _acceptance_for_event("ev_2027_w01_qatar_platinum")
    engine_a = DrawEngine(rng=DeterministicRng(7001))
    engine_b = DrawEngine(rng=DeterministicRng(7001))

    qual_a = engine_a.generate_qualification_draw(acceptance_list=acceptance, template=template)
    qual_b = engine_b.generate_qualification_draw(acceptance_list=acceptance, template=template)
    main_a = engine_a.generate_main_draw(acceptance_list=acceptance, template=template)
    main_b = engine_b.generate_main_draw(acceptance_list=acceptance, template=template)

    assert qual_a.model_dump() == qual_b.model_dump()
    assert main_a.model_dump() == main_b.model_dump()


def test_seeds_are_placed_in_configured_seed_positions() -> None:
    acceptance, template = _acceptance_for_event("ev_2027_w01_qatar_platinum")
    draw = DrawEngine(rng=DeterministicRng(33)).generate_main_draw(
        acceptance_list=acceptance,
        template=template,
    )

    assert len(draw.seed_positions) == template.seeds_count
    for seed_number, slot_index in draw.seed_positions.items():
        slot = draw.slots[slot_index - 1]
        assert slot.seed_number == seed_number
        assert slot.is_seed_protected is True
        assert slot.entrant_type == DrawEntrantType.PLAYER


def test_byes_are_inserted_correctly_for_24_player_main_draw() -> None:
    acceptance, template = _acceptance_for_event("ev_2027_w03_england_gold")
    draw = DrawEngine(rng=DeterministicRng(104)).generate_main_draw(
        acceptance_list=acceptance,
        template=template,
    )

    bye_slots = [slot for slot in draw.slots if slot.entrant_type == DrawEntrantType.BYE]
    assert draw.bracket_size == template.main_draw_size + template.byes
    assert len(bye_slots) == template.byes


def test_main_draw_contains_qualifier_and_wild_card_placeholders() -> None:
    acceptance, template = _acceptance_for_event("ev_2027_w01_malaysia_major")
    draw = DrawEngine(rng=DeterministicRng(22)).generate_main_draw(
        acceptance_list=acceptance,
        template=template,
    )

    qualifier_slots = [slot for slot in draw.slots if slot.entrant_type == DrawEntrantType.QUALIFIER_PLACEHOLDER]
    wild_card_slots = [slot for slot in draw.slots if slot.entrant_type == DrawEntrantType.WILD_CARD_PLACEHOLDER]

    assert len(qualifier_slots) == template.qualifier_spots
    assert len(wild_card_slots) == template.wild_cards
    assert draw.qualifier_slot_indexes == [slot.slot_index for slot in qualifier_slots]
    assert draw.wild_card_slot_indexes == [slot.slot_index for slot in wild_card_slots]


def test_parallel_event_draws_are_independent_but_deterministic() -> None:
    acceptance_a, template_a = _acceptance_for_event("ev_2027_w01_qatar_platinum", seed=501)
    acceptance_b, template_b = _acceptance_for_event("ev_2027_w01_malaysia_major", seed=501)

    engine = DrawEngine(rng=DeterministicRng(8181))
    draw_a_first = engine.generate_main_draw(acceptance_list=acceptance_a, template=template_a)
    draw_b_first = engine.generate_main_draw(acceptance_list=acceptance_b, template=template_b)

    engine_replay = DrawEngine(rng=DeterministicRng(8181))
    draw_a_second = engine_replay.generate_main_draw(acceptance_list=acceptance_a, template=template_a)
    draw_b_second = engine_replay.generate_main_draw(acceptance_list=acceptance_b, template=template_b)

    assert draw_a_first.model_dump() == draw_a_second.model_dump()
    assert draw_b_first.model_dump() == draw_b_second.model_dump()
    assert draw_a_first.model_dump() != draw_b_first.model_dump()
