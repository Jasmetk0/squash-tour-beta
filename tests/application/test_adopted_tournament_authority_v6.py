from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from beta_engine.application import authoritative_run_simulation_driver as driver_module
from beta_engine.application.authoritative_run_simulation_driver import (
    AuthoritativeRunSimulationDriver,
    _AdoptedTournamentEvidence,
)
from beta_engine.application.run_owned_match_package import build_run_owned_match_package
from beta_engine.application.season_point_awards_service import FrozenPointAwardAuthority
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.entry_field import TournamentEntryFieldCapacity
from beta_engine.domain.tournaments.models import CalendarEvent
from beta_engine.infrastructure.db.models import AdoptedTournamentAuthorityModel


pytestmark = pytest.mark.smoke


def _draw():
    draw_input = TournamentDrawInputAuthority(
        run_id="run",
        branch_id="branch",
        event_id="event",
        committed_by_command_id="input",
        draw_seed=9191,
        main_seed_count=1,
        qualification_seed_count=0,
        field_sequence=1,
        capacity=TournamentEntryFieldCapacity(
            main_draw_size=4,
            qualification_draw_size=0,
            qualifier_spots=0,
        ),
        tournament_ranking_authority_fingerprint="1" * 64,
        ranking_snapshot_fingerprint="2" * 64,
        entry_field_fingerprint="3" * 64,
        direct_main_player_ids=("A", "B", "C", "D"),
        qualification_player_ids=(),
        qualifier_placeholder_ids=(),
        withdrawn_player_ids=(),
        main_seed_player_ids=("A",),
        qualification_seed_player_ids=(),
    )
    return TournamentDrawAuthorityBuilder.build(
        draw_input=draw_input,
        command_id="draw",
    )


def _event():
    return CalendarEvent(
        event_id="event",
        season="2000/2001",
        season_week=1,
        calendar_year=2000,
        year_week=1,
        template_id="template",
        event_name="Canonical Open",
        category="TEST",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="Europe",
        main_draw_size=4,
        qualification_draw_size=0,
        seeds_count=2,
        qualifier_spots=0,
        ranking_points_table={
            "champion": 1000,
            "finalist": 650,
            "semifinal": 400,
        },
        ranking_configuration_legacy=False,
        calendar_fingerprint="c" * 64,
    )


def _points():
    return FrozenPointAwardAuthority(
        ranking_status="ranked",
        point_distribution={
            "champion": 1000,
            "finalist": 650,
            "semifinal": 400,
        },
        point_distribution_source="calendar_event.ranking_points_table",
    )


def _evidence(draw):
    return _AdoptedTournamentEvidence(
        event_id="event",
        calendar_event=_event(),
        point_award_authority=_points(),
        draw_authority_fingerprint=draw.fingerprint,
    )


class _FakeDrawStore:
    draw = None

    def __init__(self, session):
        self.session = session

    def get(self, **kwargs):
        return self.draw


class _FakeSession:
    def __init__(self, row=None):
        self.row = row

    def get(self, model, key):
        if model is AdoptedTournamentAuthorityModel:
            return self.row
        return None


def test_v6_adopted_authority_persists_no_matchpackage():
    draw = _draw()
    driver = AuthoritativeRunSimulationDriver(None, None, None)
    evidence = (_evidence(draw),)

    payload_json = driver._encode_adopted_authority(evidence)
    payload = json.loads(payload_json)

    assert payload["schema_version"] == "adopted_tournament_authority.v6"
    assert "package" not in payload["tournaments"][0]
    assert payload["tournaments"][0]["event_id"] == "event"
    assert payload["tournaments"][0]["calendar_event"]["event_id"] == "event"
    assert (
        payload["tournaments"][0]["draw_authority_fingerprint"]
        == draw.fingerprint
    )

    reopened = driver._decode_adopted_authority(payload_json)
    assert reopened == evidence


def test_v6_replay_rebuilds_exact_package_without_live_calendar_or_match_registry(
    monkeypatch,
):
    draw = _draw()
    _FakeDrawStore.draw = draw
    monkeypatch.setattr(
        driver_module,
        "TournamentDrawAuthorityStore",
        _FakeDrawStore,
    )
    driver = AuthoritativeRunSimulationDriver(None, None, None)
    week = RankingWeek(season_index=0, week=1)
    evidence = (_evidence(draw),)
    payload_json = driver._encode_adopted_authority(evidence)
    authority_fp = driver._tournament_authority_fingerprint(
        "run",
        "branch",
        week,
        evidence,
    )
    row = SimpleNamespace(
        package_json=payload_json,
        authority_fingerprint=authority_fp,
    )

    packages, replay_fp = driver._replay_adopted_authority(
        _FakeSession(row),
        run_id="run",
        branch_id="branch",
        week=week,
        row=row,
    )

    expected = driver._bind_owned_draw_evidence(
        package=build_run_owned_match_package(
            draw=draw,
            event=_event(),
            week=week,
        ),
        draw=draw,
        week=week,
    )
    assert packages == (expected,)
    assert replay_fp == authority_fp


def test_packages_after_v6_adoption_do_not_consult_legacy_services(monkeypatch):
    draw = _draw()
    _FakeDrawStore.draw = draw
    monkeypatch.setattr(
        driver_module,
        "TournamentDrawAuthorityStore",
        _FakeDrawStore,
    )
    week = RankingWeek(season_index=0, week=1)
    evidence = (_evidence(draw),)
    driver = AuthoritativeRunSimulationDriver(None, None, None)
    payload_json = driver._encode_adopted_authority(evidence)
    row = SimpleNamespace(
        package_json=payload_json,
        authority_fingerprint=driver._tournament_authority_fingerprint(
            "run",
            "branch",
            week,
            evidence,
        ),
    )

    class ForbiddenMatchService:
        def _load_registry(self):
            raise AssertionError("legacy match registry must not be read")

    class ForbiddenAwardService:
        @property
        def calendar_service(self):
            raise AssertionError("live Calendar service must not be read")

    replay_driver = AuthoritativeRunSimulationDriver(
        None,
        ForbiddenMatchService(),
        ForbiddenAwardService(),
    )
    packages = replay_driver._packages(
        week,
        session=_FakeSession(row),
        run_id="run",
        branch_id="branch",
    )
    assert len(packages) == 1
    assert packages[0].event_id == "event"


def test_v6_event_snapshot_corruption_fails_authority_replay(monkeypatch):
    draw = _draw()
    _FakeDrawStore.draw = draw
    monkeypatch.setattr(
        driver_module,
        "TournamentDrawAuthorityStore",
        _FakeDrawStore,
    )
    driver = AuthoritativeRunSimulationDriver(None, None, None)
    week = RankingWeek(season_index=0, week=1)
    evidence = (_evidence(draw),)
    payload_json = driver._encode_adopted_authority(evidence)
    authority_fp = driver._tournament_authority_fingerprint(
        "run",
        "branch",
        week,
        evidence,
    )
    payload = json.loads(payload_json)
    payload["tournaments"][0]["calendar_event"]["template_id"] = "tampered-template"
    row = SimpleNamespace(
        package_json=json.dumps(payload, sort_keys=True, separators=(",", ":")),
        authority_fingerprint=authority_fp,
    )

    with pytest.raises(ValueError, match="frozen tournament authority is corrupt"):
        driver._replay_adopted_authority(
            _FakeSession(row),
            run_id="run",
            branch_id="branch",
            week=week,
            row=row,
        )