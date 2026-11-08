"""Real source geometries through canonical field/WC/input/Draw and SQLite.

Named test players and explicitly eligible applications exercise mechanics; these
fixtures do not choose the unresolved production automatic eligibility policy.
"""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from beta_engine.application.calendar_package_run_adapter import (
    CalendarPackageRunAdapter,
)
from beta_engine.application.fax_reference_player_draw import (
    FaxReferencePlayerDrawService,
)
from beta_engine.application.pre_alpha_fax_acceptance_calendar_source import (
    PreAlphaFaxAcceptanceCalendarSource,
)
from beta_engine.application.season_calendar_service import SeasonCalendarService
from beta_engine.application.season_category_points_service import (
    SeasonCategoryPointsService,
)
from beta_engine.application.tournament_templates_service import (
    TournamentTemplatesConfigService,
)
from beta_engine.domain.run_packages import (
    AppliedPackageVersion,
    RunPackageEntity,
    RunPackageState,
    entity_content_fingerprint,
)
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
    TournamentDrawInputAuthorityBuilder,
    requires_padded_qualification_sections,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryFieldResolver,
)
from beta_engine.domain.tournaments.fax_reference_player_draw import (
    FaxReferencePlayerDraw,
    fax_reference_entry_capacity,
)
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthorityBuilder,
)
from beta_engine.infrastructure.db.engine import (
    DatabaseSettings,
    create_session_factory,
    create_sqlite_engine,
)
from beta_engine.infrastructure.db.models import (
    Base,
    PublishedOfficialRankingModel,
    RunBranchModel,
    RunContainerModel,
    TournamentDrawAuthorityModel,
)
from beta_engine.infrastructure.db.run_package_state import put_run_package_state
from beta_engine.infrastructure.db.simulation_slot_state import (
    capture_saved_simulation_slots,
    restore_saved_simulation_slots,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
)
from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_wild_card_authority import (
    TournamentWildCardAuthorityStore,
)
from tests.infrastructure.test_tournament_draw_authority import ranking_snapshot

pytestmark = [pytest.mark.smoke, pytest.mark.pr_critical]
PLAYERS = tuple(f"P{i:03d}" for i in range(1, 81))


@pytest.fixture
def database(tmp_path):
    engine = create_sqlite_engine(
        DatabaseSettings(url=f"sqlite:///{tmp_path / 'fax-draw.db'}")
    )
    Base.metadata.create_all(engine)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        session.add(
            RunContainerModel(
                run_id="run", timeline_start_season=2000, timeline_end_season=2049
            )
        )
        session.add(
            RunBranchModel(run_id="run", branch_id="branch", display_name="Timeline 1")
        )
    yield factory
    engine.dispose()


@pytest.fixture(scope="module")
def fax_source(tmp_path_factory):
    templates = TournamentTemplatesConfigService(
        config_path=Path("config/tournament_templates/mvp_templates.json")
    )
    points = SeasonCategoryPointsService(
        templates, registry_path=tmp_path_factory.mktemp("source") / "absent.json"
    )
    source = PreAlphaFaxAcceptanceCalendarSource(
        template_service=templates,
        calendar_validation_service=SeasonCalendarService(
            template_service=templates, category_points_service=points
        ),
    )
    calendar = source.build_calendar("2000/2001")
    document = source.build_document("2000/2001")
    assert not points.registry_path.exists()
    return calendar, document


@pytest.fixture(scope="module")
def snapshot():
    return ranking_snapshot(PLAYERS)


def applications(event):
    return tuple(
        TournamentEntryApplication(
            application_id=f"{event.event_id}:app:{player}",
            run_id="run",
            branch_id="branch",
            event_id=event.event_id,
            player_id=player,
            entry_window="main",
            decision_slot_ordinal=10,
            nr_tie_break_token=f"entry-{player}",
            eligible=True,
        )
        for player in PLAYERS[:-2]
    )


def in_memory_input(event, snapshot, *, seed=20261106):
    ranking = TournamentRankingSnapshotAuthority(
        run_id="run",
        branch_id="branch",
        event_id=event.event_id,
        ranking_week=snapshot.week,
        ranking_snapshot=snapshot,
        adopted_by_command_id="ranking",
    )
    field = TournamentEntryFieldResolver.build_initial(
        authority=ranking,
        applications=applications(event),
        capacity=fax_reference_entry_capacity(event),
    )
    wc = TournamentWildCardAuthorityBuilder.build(
        field=field,
        field_sequence=1,
        command_id="wc",
        original_wild_card_player_ids=PLAYERS[-2:],
    )
    return TournamentDrawInputAuthorityBuilder.build(
        authority=ranking,
        field=field,
        field_sequence=1,
        command_id="input",
        draw_seed=seed,
        main_seed_count=None,
        qualification_seed_count=None,
        schema_version=(
            "tournament_draw_input_authority.v12"
            if requires_padded_qualification_sections(field.capacity)
            else "tournament_draw_input_authority.v3"
        ),
        wild_card_authority=wc,
    )


def copied_state(document):
    return RunPackageState(
        run_id="run",
        branch_id="branch",
        package_versions=(
            AppliedPackageVersion(
                package_type=document.package_type,
                package_id=document.package_id,
                source_version=document.source_version,
                source_fingerprint=document.source_fingerprint,
                applied_entity_ids=tuple(e.source_entity_id for e in document.entities),
                provenance=document.provenance,
            ),
        ),
        entities=tuple(
            RunPackageEntity(
                run_local_id=i,
                source_package_id=document.package_id,
                source_package_version=document.source_version,
                source_package_fingerprint=document.source_fingerprint,
                source_entity_id=e.source_entity_id,
                entity_kind=e.entity_kind,
                entity_schema_version=e.entity_schema_version,
                scope=e.scope,
                payload=e.payload,
                source_baseline_fingerprint=entity_content_fingerprint(
                    entity_kind=e.entity_kind,
                    entity_schema_version=e.entity_schema_version,
                    scope=e.scope,
                    payload=e.payload,
                    references=e.references,
                ),
                references=e.references,
            )
            for i, e in enumerate(document.entities, 1)
        ),
    )


def package_draw(event, draw_input, draw, *, state=None):
    return FaxReferencePlayerDraw(
        run_package_state_fingerprint=state.fingerprint if state else "1" * 64,
        calendar_projection_fingerprint=(
            CalendarPackageRunAdapter.project_calendar(
                state, package_id="calendar-2000-2001"
            ).fingerprint
            if state
            else "2" * 64
        ),
        source_event=event,
        draw_input=draw_input,
        draw=draw,
    )


def assert_real_field(event, draw_input, draw):
    expected_q = event.qualification_draw_size // 4
    assert len(draw.main.slots) == 32
    assert len(draw.main.bye_slot_indexes) == event.byes
    assert {x for x, _ in draw.main.qualifier_placeholder_slots} == {
        "Q1",
        "Q2",
        "Q3",
        "Q4",
    }
    main_players = {s.player_id for s in draw.main.slots if s.entrant_kind == "player"}
    q_players = [
        s.player_id
        for b in draw.qualification_brackets
        for s in b.slots
        if s.entrant_kind == "player"
    ]
    assert main_players == set(draw_input.direct_main_player_ids) | set(
        draw_input.wild_card_player_ids
    )
    assert len(q_players) == len(set(q_players)) == event.qualification_draw_size
    assert set(q_players) == set(draw_input.qualification_player_ids)
    assert not main_players.intersection(q_players)
    assert {
        s.player_id for s in draw.main.slots if s.entry_status == "wild_card"
    } == set(PLAYERS[-2:])
    assert len([s for s in draw.main.slots if s.is_seed_protected]) == 8
    for bracket in draw.qualification_brackets:
        assert sum(s.entrant_kind == "player" for s in bracket.slots) == expected_q
        assert len(bracket.bye_slot_indexes) == bracket.bracket_size - expected_q
    for bracket in (draw.main, *draw.qualification_brackets):
        assert len(bracket.nodes) == bracket.bracket_size - 1
        for a, b in zip(bracket.slots[::2], bracket.slots[1::2], strict=True):
            assert (a.entrant_kind, b.entrant_kind) != ("bye", "bye")
            if a.entrant_kind == "bye" or b.entrant_kind == "bye":
                assert (b if a.entrant_kind == "bye" else a).is_seed_protected


def test_all_80_original_editions_have_source_bound_real_player_draws(
    fax_source, snapshot
):
    calendar, _ = fax_source
    assert len(calendar.events) == 80
    assert (
        calendar.metadata.build_fingerprint
        == "e2150e66eef92943b56b2d22f3de26b8fe6c161669bd5d24c770c516f560e197"
    )
    for event in calendar.events:
        before = event.model_dump_json()
        draw_input = in_memory_input(event, snapshot)
        draw = TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input, command_id="draw"
        )
        result = package_draw(event, draw_input, draw)
        assert_real_field(event, draw_input, draw)
        assert (
            FaxReferencePlayerDraw.model_validate_json(result.model_dump_json())
            == result
        )
        assert event.model_dump_json() == before
        assert (
            draw_input.capacity.qualification_draw_size == event.qualification_draw_size
        )
        assert draw_input.qualification_seed_count == (
            4 if event.main_draw_size == 24 else 8
        )
        assert draw == TournamentDrawAuthorityBuilder.build(
            draw_input=draw_input, command_id="draw"
        )


@pytest.mark.parametrize("main_size", [24, 32])
def test_seed_changes_shuffle_but_preserve_field_and_source(
    fax_source, snapshot, main_size
):
    event = next(e for e in fax_source[0].events if e.main_draw_size == main_size)
    first = in_memory_input(event, snapshot, seed=17)
    second = in_memory_input(event, snapshot, seed=18)
    draws = [
        TournamentDrawAuthorityBuilder.build(draw_input=x, command_id="draw")
        for x in (first, second)
    ]
    assert draws[0].main.slots != draws[1].main.slots
    for inputs, draw in zip((first, second), draws, strict=True):
        assert_real_field(event, inputs, draw)
        assert package_draw(event, inputs, draw).source_event == event


@pytest.mark.parametrize("main_size", [24, 32])
def test_sqlite_commit_retry_reopen_and_source_read_never_mutate(
    database, fax_source, snapshot, main_size
):
    calendar, document = fax_source
    event = next(e for e in calendar.events if e.main_draw_size == main_size)
    state = copied_state(document)
    scope = {"run_id": "run", "branch_id": "branch", "event_id": event.event_id}
    with database.begin() as session:
        put_run_package_state(session, state)
        session.add(
            PublishedOfficialRankingModel(
                run_id="run",
                branch_id="branch",
                week_ordinal=snapshot.week.ordinal,
                snapshot_fingerprint=snapshot.fingerprint,
                payload_json=snapshot.model_dump_json(),
            )
        )
        session.flush()
        TournamentRankingSnapshotAuthorityStore(session).adopt(
            **scope, ranking_week=snapshot.week, command_id="ranking"
        )
        field = TournamentEntryFieldStore(session).stage_initial(
            **scope,
            applications=applications(event),
            capacity=fax_reference_entry_capacity(event),
            command_id="field",
        )
        assert len(field.qualification_player_ids) == event.qualification_draw_size
        assert (
            len(field.below_qualification_cut_player_ids) > 0
        )  # padding does not admit the waiting list
        TournamentWildCardAuthorityStore(session).resolve(
            **scope,
            command_id="wc",
            original_wild_card_player_ids=PLAYERS[-2:],
        )
        before_draw = {"content": {}}
        capture_saved_simulation_slots(
            session, before_draw, run_id="run", branch_id="branch"
        )
        inputs = TournamentDrawInputAuthorityStore(session).commit(
            **scope, command_id="input", draw_seed=17
        )
        draw = TournamentDrawAuthorityStore(session).generate(
            **scope, command_id="draw"
        )
        assert (
            TournamentDrawInputAuthorityStore(session).commit(
                **scope, command_id="input", draw_seed=17
            )
            == inputs
        )
        assert (
            TournamentDrawAuthorityStore(session).generate(**scope, command_id="draw")
            == draw
        )
        after_draw = {"content": {}}
        capture_saved_simulation_slots(
            session, after_draw, run_id="run", branch_id="branch"
        )
        restore_saved_simulation_slots(
            session,
            current_payload=after_draw,
            target_payload=before_draw,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentDrawAuthorityStore(session).get_initial(**scope) is None
        restored_before = {"content": {}}
        capture_saved_simulation_slots(
            session, restored_before, run_id="run", branch_id="branch"
        )
        restore_saved_simulation_slots(
            session,
            current_payload=restored_before,
            target_payload=after_draw,
            run_id="run",
            branch_id="branch",
        )
        assert TournamentDrawAuthorityStore(session).get_initial(**scope) == draw
    with database() as session:
        before = session.connection().connection.driver_connection.total_changes
        assert TournamentDrawInputAuthorityStore(session).get(**scope) == inputs
        assert TournamentDrawAuthorityStore(session).get_initial(**scope) == draw
        assert session.connection().connection.driver_connection.total_changes == before
        stored = session.get(
            TournamentDrawAuthorityModel, ("run", "branch", event.event_id)
        ).payload_json
    database.kw[
        "bind"
    ].dispose()  # discard all pooled connections, then reopen the file
    report = FaxReferencePlayerDrawService(database).inspect(
        **scope, season="2000/2001"
    )
    assert report == package_draw(event, inputs, draw, state=state)
    assert_real_field(event, inputs, report.draw)
    with database() as session:
        assert (
            session.get(
                TournamentDrawAuthorityModel, ("run", "branch", event.event_id)
            ).payload_json
            == stored
        )
        assert session.execute(text("PRAGMA integrity_check")).scalar_one() == "ok"
    edited_entity = next(
        e for e in state.entities if e.source_entity_id == event.event_id
    )
    changed_entity = edited_entity.model_copy(
        update={"payload": dict(edited_entity.payload, event_name="Edited after Draw")}
    )
    edited_state = state.model_copy(
        update={
            "entities": tuple(
                changed_entity if e.source_entity_id == event.event_id else e
                for e in state.entities
            )
        }
    )
    with database.begin() as session:
        put_run_package_state(session, edited_state)
    with pytest.raises(ValueError, match="edited Calendar Edition"):
        FaxReferencePlayerDrawService(database).inspect(**scope, season="2000/2001")
    with database.begin() as session:
        put_run_package_state(session, state)


@pytest.mark.parametrize(
    "mutation", ["event", "capacity", "scope", "slots", "node", "q_link", "algorithm"]
)
def test_source_envelope_rejects_forged_draw_even_if_json_is_well_formed(
    fax_source, snapshot, mutation
):
    event = next(e for e in fax_source[0].events if e.main_draw_size == 32)
    inputs = in_memory_input(event, snapshot)
    draw = TournamentDrawAuthorityBuilder.build(draw_input=inputs, command_id="draw")
    data = package_draw(event, inputs, draw).model_dump(mode="json")
    if mutation == "event":
        data["source_event"]["event_id"] += "-other"
    elif mutation == "capacity":
        data["draw_input"]["capacity"]["qualification_draw_size"] = 32
    elif mutation == "scope":
        data["draw"]["branch_id"] = "other"
    elif mutation == "slots":
        slots = data["draw"]["main"]["slots"]
        a, b = [
            s
            for s in slots
            if s["entrant_kind"] == "player" and s["seed_number"] is None
        ][:2]
        a["player_id"], b["player_id"] = b["player_id"], a["player_id"]
    elif mutation == "node":
        data["draw"]["qualification_sections"][0]["nodes"][0]["source_top"] = "slot:99"
    elif mutation == "q_link":
        data["draw"]["qualification_sections"][0]["section_id"] = "Q2"
    else:
        data["draw"]["algorithm_version"] = "idealized_seed_tiers.v2"
    with pytest.raises(ValueError):
        FaxReferencePlayerDraw.model_validate_json(json.dumps(data))


def test_platinum_v12_cannot_be_silently_reinterpreted_as_old_schema(
    fax_source, snapshot
):
    event = next(e for e in fax_source[0].events if e.main_draw_size == 32)
    data = in_memory_input(event, snapshot).model_dump(mode="json")
    for old in (
        "tournament_draw_input_authority.v2",
        "tournament_draw_input_authority.v3",
    ):
        with pytest.raises(ValidationError, match="power-of-two"):
            TournamentDrawInputAuthority.model_validate_json(
                json.dumps(dict(data, schema_version=old))
            )
    for schema, size in (
        ("tournament_draw_input_authority.v12", 32),
        ("tournament_draw_input_authority.v12", 20),
    ):
        changed = dict(
            data,
            schema_version=schema,
            capacity=dict(data["capacity"], qualification_draw_size=size),
        )
        with pytest.raises(ValidationError):
            TournamentDrawInputAuthority.model_validate_json(json.dumps(changed))


@pytest.mark.parametrize("main_size", [24, 32])
def test_original_fax_draw_commit_generate_and_retry_over_real_http(
    tmp_path, fax_source, snapshot, main_size
):
    from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
    from tests.api.test_saved_revision_history_api import (
        ApiServer,
        _create_run,
        _request,
    )

    event = next(e for e in fax_source[0].events if e.main_draw_size == main_size)
    server = ApiServer(database_url=f"sqlite:///{tmp_path / 'fax-http.db'}")
    with server:
        run_id, branch_id, _ = _create_run(
            server, display_name=f"Original FAX Main {main_size}"
        )
        scope = {"run_id": run_id, "branch_id": branch_id, "event_id": event.event_id}
        ranking = snapshot.model_copy(update={"run_id": run_id, "branch_id": branch_id})
        with server.app.state.runtime.repository._session_factory.begin() as session:
            state = copied_state(fax_source[1]).model_copy(
                update={"run_id": run_id, "branch_id": branch_id}
            )
            put_run_package_state(session, state)
            session.add(
                PublishedOfficialRankingModel(
                    run_id=run_id,
                    branch_id=branch_id,
                    week_ordinal=ranking.week.ordinal,
                    snapshot_fingerprint=ranking.fingerprint,
                    payload_json=ranking.model_dump_json(),
                )
            )
            session.flush()
            TournamentRankingSnapshotAuthorityStore(session).adopt(
                **scope, ranking_week=ranking.week, command_id="ranking"
            )
            field = TournamentEntryFieldStore(session).stage_initial(
                **scope,
                applications=tuple(
                    a.model_copy(update={"run_id": run_id, "branch_id": branch_id})
                    for a in applications(event)
                ),
                capacity=fax_reference_entry_capacity(event),
                command_id="field",
            )
            TournamentWildCardAuthorityStore(session).resolve(
                **scope, command_id="wc", original_wild_card_player_ids=PLAYERS[-2:]
            )
        root = f"{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/tournaments/{event.event_id}/draw"
        commit = dict(
            scope,
            schema_version="canonical_tournament_draw_input_commit_command.v1",
            command_id="input",
            expected_field_fingerprint=field.fingerprint,
            draw_seed=17,
        )
        code, committed = _request("POST", root + "/commit-input", commit)
        assert code == 200, committed
        assert committed["qualification_seed_count"] == (4 if main_size == 24 else 8)
        assert _request("POST", root + "/commit-input", commit) == (200, committed)
        generate = dict(
            scope,
            schema_version="canonical_tournament_draw_generate_command.v1",
            command_id="draw",
            expected_draw_input_fingerprint=committed["draw_input_fingerprint"],
        )
        code, generated = _request("POST", root + "/generate", generate)
        assert code == 200, generated
        assert generated["qualification_section_sizes"] == (
            [4] * 4 if main_size == 24 else [8] * 4
        )
        assert _request("POST", root + "/generate", generate) == (200, generated)
        code, authority = _request("GET", root + "/authority")
        assert code == 200, authority
        parsed = TournamentDrawAuthority.model_validate_json(json.dumps(authority))
        assert parsed.main.bracket_size == 32
        assert len(parsed.main.bye_slot_indexes) == event.byes
        assert sum(len(s.bye_slot_indexes) for s in parsed.qualification_brackets) == (
            0 if main_size == 24 else 8
        )
        report = FaxReferencePlayerDrawService(
            server.app.state.runtime.repository._session_factory
        ).inspect(**scope, season="2000/2001")
        assert report.draw == parsed
        # A stale source request must not alter the already generated authority.
        code, _ = _request(
            "POST",
            root + "/generate",
            dict(generate, expected_draw_input_fingerprint="0" * 64),
        )
        assert code == 409
        assert _request("GET", root + "/authority") == (200, authority)


def test_first_gold_payload_keeps_exact_prechange_v2_bytes(fax_source, snapshot):
    # Independently computed using draw_authority.py from merged base 1800697b.
    # All 40 Gold payloads were also compared byte-for-byte with that baseline.
    event = fax_source[0].events[0]
    assert event.event_id == "FAX-ACCEPT-WT-001" and event.main_draw_size == 24
    draw = TournamentDrawAuthorityBuilder.build(
        draw_input=in_memory_input(event, snapshot), command_id="draw"
    )
    assert (
        draw.fingerprint
        == "02bcbbaf8a38234d1ffdfa470f86a9ffcf20aa537f660fb0c1ef0e27e4c9aa45"
    )


def test_v12_rejects_missing_wc_authority_and_source_admission_overflow(
    fax_source, snapshot
):
    event = next(e for e in fax_source[0].events if e.main_draw_size == 32)
    data = in_memory_input(event, snapshot).model_dump(mode="json")
    with pytest.raises(ValidationError, match="WC authority fingerprint"):
        TournamentDrawInputAuthority.model_validate_json(
            json.dumps(dict(data, wild_card_authority_fingerprint=None))
        )
    data["capacity"]["qualification_draw_size"] = 20
    with pytest.raises(ValidationError, match="source admission capacity"):
        TournamentDrawInputAuthority.model_validate_json(json.dumps(data))
