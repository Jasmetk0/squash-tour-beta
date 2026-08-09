from __future__ import annotations
from tests.support.world_packages import load_fax_reference_countries

from beta_engine.core import DeterministicRng
from beta_engine.domain.draws import DrawEngine, DrawEntrantType
from beta_engine.domain.entries import EntryEngine
from beta_engine.domain.players import Player, PlayerGenerator
from beta_engine.domain.countries import Country, CountryTalentModel
from beta_engine.domain.tournaments.progression import (
    MatchDisposition,
    PlaceholderResolutionStatus,
    TournamentProgressionEngine,
)
from beta_engine.infrastructure.entry_config import load_entry_tuning_config
from beta_engine.infrastructure.tournament_config import load_season_calendar, load_tournament_templates_config
from beta_engine.infrastructure.world_config import load_player_identity_config


def _players(seed: int, per_country: int = 24) -> tuple[list[Player], dict[str, Country]]:
    countries = load_fax_reference_countries().countries
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


def _event_inputs(event_id: str, *, seed: int = 44):
    players, countries = _players(seed=95)
    event, template = _event_and_template(event_id)

    entry_engine = EntryEngine(rng=DeterministicRng(seed), tuning=load_entry_tuning_config())
    acceptance = entry_engine.build_acceptance_list(
        event=event,
        template=template,
        players=players,
        countries_by_code=countries,
    )

    draw_engine = DrawEngine(rng=DeterministicRng(seed + 200))
    qual_draw = draw_engine.generate_qualification_draw(acceptance_list=acceptance, template=template)
    main_draw = draw_engine.generate_main_draw(acceptance_list=acceptance, template=template)

    player_map = {player.player_id: player for player in players}
    return event, template, qual_draw, main_draw, player_map


def test_tournament_progression_replay_same_seed_same_inputs_same_result() -> None:
    event, template, qual_draw, main_draw, players = _event_inputs("ev_2027_w01_qatar_platinum", seed=151)

    engine_a = TournamentProgressionEngine(rng=DeterministicRng(8080))
    engine_b = TournamentProgressionEngine(rng=DeterministicRng(8080))

    result_a = engine_a.run_tournament(
        event_id=event.event_id,
        season=event.season,
        week=event.week,
        template=template,
        qualification_draw=qual_draw,
        main_draw=main_draw,
        players_by_id=players,
    )
    result_b = engine_b.run_tournament(
        event_id=event.event_id,
        season=event.season,
        week=event.week,
        template=template,
        qualification_draw=qual_draw,
        main_draw=main_draw,
        players_by_id=players,
    )

    assert result_a.model_dump() == result_b.model_dump()


def test_qualification_winners_feed_main_draw_qualifier_slots_in_slot_order() -> None:
    event, template, qual_draw, main_draw, players = _event_inputs("ev_2027_w01_qatar_platinum", seed=173)
    result = TournamentProgressionEngine(rng=DeterministicRng(2222)).run_tournament(
        event_id=event.event_id,
        season=event.season,
        week=event.week,
        template=template,
        qualification_draw=qual_draw,
        main_draw=main_draw,
        players_by_id=players,
    )

    resolved = [
        res for res in result.qualifier_slot_resolutions if res.status == PlaceholderResolutionStatus.RESOLVED
    ]
    assert [res.slot_index for res in resolved] == sorted(main_draw.qualifier_slot_indexes)[: len(resolved)]
    assert [res.resolved_player_id for res in resolved] == result.qualification.qualifiers_in_order[: len(resolved)]
    assert len(result.qualifier_slot_resolutions) == len(main_draw.qualifier_slot_indexes)


def test_bye_advancement_exists_in_24_8_main_draw_path() -> None:
    event, template, qual_draw, main_draw, players = _event_inputs("ev_2027_w03_england_gold", seed=211)
    result = TournamentProgressionEngine(rng=DeterministicRng(5151)).run_tournament(
        event_id=event.event_id,
        season=event.season,
        week=event.week,
        template=template,
        qualification_draw=qual_draw,
        main_draw=main_draw,
        players_by_id=players,
    )

    first_round = next(round_result for round_result in result.main_draw.rounds if round_result.round_number == 1)
    assert any(match.disposition == MatchDisposition.BYE_ADVANCE for match in first_round.matches)
    assert any(slot.entrant_type == DrawEntrantType.BYE for slot in main_draw.slots)


def test_main_draw_produces_champion_and_finalist_placements() -> None:
    event, template, qual_draw, main_draw, players = _event_inputs("ev_2027_w01_malaysia_major", seed=301)
    result = TournamentProgressionEngine(rng=DeterministicRng(9991)).run_tournament(
        event_id=event.event_id,
        season=event.season,
        week=event.week,
        template=template,
        qualification_draw=qual_draw,
        main_draw=main_draw,
        players_by_id=players,
    )

    assert result.main_draw.champion_player_id is not None
    assert result.main_draw.finalist_player_id is not None

    placement_map = {placement.player_id: placement.finish for placement in result.main_draw.placements}
    assert placement_map[result.main_draw.champion_player_id] == "CHAMPION"
    assert placement_map[result.main_draw.finalist_player_id] == "FINALIST"
    assert any(placement.finish == "SEMIFINALIST" for placement in result.main_draw.placements)
