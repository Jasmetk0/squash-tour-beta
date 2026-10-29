"""Production HTTP/SQLite overlapping native Editions; no fabricated match results."""

import json
import sqlite3
import time
from copy import deepcopy

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
    tour_url,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def ready(server, width=52, *, seasons=2):
    offset = 37 if width == 61 else 80 if width == 80 else 1
    repo, _ = setup(server, RunCalendar(width, offset, 2030, seasons), 8)
    for eid in ("parallel-a", "parallel-b"):
        view = inspect(server)
        week = view["state"]["week"]
        execute(
            server,
            command(
                view,
                "create-edition",
                name=eid + ":create",
                data={
                    "schema_version": "calendar_tournament_edition.v2",
                    "simulation_seed": 891,
                    "edition_id": eid,
                    "name": eid,
                    "week": {**week, "week": 4},
                    "announcement_week": {**week, "week": 3},
                    "start_slot": 1,
                    "main_entrant_count": 4,
                    "ranked": True,
                    "validity_weeks": width,
                    "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
                },
            ),
        )
        save_tour(server)
    for target in (3, 4):
        execute(server, command(inspect(server), "transition", name=f"week-{target}"))
        save_tour(server)
    players = [p["player_id"] for p in inspect(server)["players"]]
    for i, eid in enumerate(("parallel-a", "parallel-b")):
        execute(
            server,
            command(
                inspect(server),
                "submit",
                name=eid + ":submit",
                edition_id=eid,
                data={"player_ids": players[i * 4 : i * 4 + 4]},
            ),
        )
        for action in ("approve", "draw"):
            execute(
                server,
                command(
                    inspect(server), action, name=eid + ":" + action, edition_id=eid
                ),
            )
        save_tour(server)
    return repo


def copy_database(source, target):
    with sqlite3.connect(source) as source_db, sqlite3.connect(target) as target_db:
        source_db.backup(target_db)


def test_global_save_verifies_actual_append_before_install_and_rejects_changed_ancestor(
    tmp_path, prepared_slots, monkeypatch
):
    from sqlalchemy import update, select
    from sqlalchemy.orm import object_session
    from beta_engine.domain.run_revisions import saved_revision_content_hash
    from beta_engine.infrastructure.db import calendar_global_slot_origins
    from beta_engine.infrastructure.db import repositories as repository_module
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunBranchModel, TournamentApplicationSubmissionAuthorityModel
    from beta_engine.domain.tournaments.application_submission_authority import TournamentApplicationSubmissionAuthority

    path = tmp_path / 'verified-append.db'
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        repo = server.app.state.runtime.repository
        execute(server, command(inspect(server), 'next-match', name='append-first'))
        old = inspect(server)['saved_head_revision_id']
        original_gate = calendar_global_slot_origins.verify_saved_global_origins
        checked = []
        save_origin_maps = []

        def actual_gate(repository, session, revision, **kwargs):
            checked.append((revision.revision_id, session.get(RunBranchModel, 'branch').saved_head_revision_id))
            values = kwargs['sporting_component_proofs']
            assert set(values) == {'_global_origin_inputs'}
            assert values['_global_origin_inputs'] is not repository._origin_projection_values
            before = dict(repository._origin_projection_values)
            result = original_gate(repository, session, revision, **kwargs)
            assert repository._origin_projection_values == before, 'staged values must remain private until commit'
            assert any(key[2] == revision.revision_id for key in values['_global_origin_inputs'])
            save_origin_maps.append(values['_global_origin_inputs'])
            return result

        monkeypatch.setattr(calendar_global_slot_origins, 'verify_saved_global_origins', actual_gate)
        replay = repository_module.load_saved_calendar_sources
        replayed = []

        def independent_math(payload, **kwargs):
            replayed.append(payload)
            return replay(payload, **kwargs)

        monkeypatch.setattr(repository_module, 'load_saved_calendar_sources', independent_math)
        saved = save_tour(server)
        assert checked == [(saved['revision_id'], old)]
        assert save_origin_maps
        assert any(key[2] == saved['revision_id'] for key in repo._origin_projection_values)
        assert not replayed, 'identical complete actual payload already passed independent live replay'
        assert inspect(server)['saved_head_revision_id'] == saved['revision_id']
        from beta_engine.infrastructure.db.calendar_standalone_match_state import decode_prevalidated_calendar_sources
        from beta_engine.infrastructure.db.native_fork_source_projection import decoded_global_tour_source

        record = repo.get_branch_saved_revision(revision_id=saved['revision_id'])

        def no_second_decode(_source):
            pytest.fail('the committed exact captured DTO should already be retained')

        assert decoded_global_tour_source(repo, record, no_second_decode) == decode_prevalidated_calendar_sources(
            record.payload, run_id='run', branch_id='branch',
        )

        execute(server, command(inspect(server), 'next-match', name='append-second'))
        view = inspect(server)
        # A validly rehashed production row cannot diverge from the confirmed
        # Tour's Entry authorities, even after its complete math proof is warm.
        with repo._session_factory.begin() as session:
            entry = session.scalar(select(TournamentApplicationSubmissionAuthorityModel).where(
                TournamentApplicationSubmissionAuthorityModel.run_id == 'run',
                TournamentApplicationSubmissionAuthorityModel.branch_id == 'branch',
            ).limit(1))
            entry_id = entry.application_id
            original_entry = entry.payload_json, entry.fingerprint
            changed = TournamentApplicationSubmissionAuthority.model_validate_json(entry.payload_json).model_copy(
                update={'provenance': 'Rehashed changed production Entry provenance'},
            )
            entry.payload_json, entry.fingerprint = changed.model_dump_json(), changed.fingerprint
        code, rejected = _request('POST', tour_url(server) + '/save', {
            'expected_draft_version': view['draft_version'],
            'expected_calendar_tour_fingerprint': view['tour_fingerprint'],
        })
        assert code == 409 and 'Entry authority' in str(rejected), rejected
        with repo._session_factory.begin() as session:
            entry = session.scalar(select(TournamentApplicationSubmissionAuthorityModel).where(
                TournamentApplicationSubmissionAuthorityModel.application_id == entry_id,
                TournamentApplicationSubmissionAuthorityModel.run_id == 'run',
                TournamentApplicationSubmissionAuthorityModel.branch_id == 'branch',
            ))
            entry.payload_json, entry.fingerprint = original_entry
        assert inspect(server)['tour_fingerprint'] == view['tour_fingerprint']
        # Reusing the private checkpoint captured earlier in THIS Save still
        # rehashes the actual row. A changed/rehashed row must decode afresh.
        from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel
        from beta_engine.domain.run_packages import canonical_hash

        capture = repository_module.capture_saved_calendar_match
        capture_checked = []

        def changed_live_checkpoint(session, payload, **kwargs):
            assert kwargs['_captured_checkpoint'] is not None
            row = session.get(CalendarPlayerSportingCheckpointModel, ('run', 'branch'))
            body = json.loads(row.payload_json)
            body['unexpected_capture_field'] = True
            row.payload_json, row.fingerprint = json.dumps(body), canonical_hash(body)
            session.flush()
            capture_checked.append(True)
            return capture(session, payload, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(repository_module, 'capture_saved_calendar_match', changed_live_checkpoint)
            assert _request('POST', tour_url(server) + '/save', {
                'expected_draft_version': view['draft_version'],
                'expected_calendar_tour_fingerprint': view['tour_fingerprint'],
            })[0] == 409
        assert capture_checked and inspect(server)['tour_fingerprint'] == view['tour_fingerprint']
        original_decode = repo._to_branch_saved_revision
        injected = []
        before_failed_save_origins = dict(repo._origin_projection_values)

        def change_actual_ancestor(model, **kwargs):
            result = original_decode(model, **kwargs)
            if model.parent_revision_id == saved['revision_id'] and not injected:
                session = object_session(model)
                source = session.get(BranchSavedRevisionModel, saved['revision_id'])
                body = json.loads(source.payload_json)
                body['run']['display_name'] = 'Rehashed during the Save transaction'
                digest = saved_revision_content_hash(
                    revision_id=source.revision_id, run_id=source.run_id, branch_id=source.branch_id,
                    sequence=source.sequence, parent_revision_id=source.parent_revision_id,
                    kind=source.kind, payload_schema_version=source.payload_schema_version,
                    payload=body, change_summary=json.loads(source.change_summary_json),
                )
                session.execute(update(BranchSavedRevisionModel).where(
                    BranchSavedRevisionModel.revision_id == source.revision_id,
                ).values(payload_json=json.dumps(body), content_hash=digest)
                    .execution_options(synchronize_session=False))
                injected.append(True)
            return result

        monkeypatch.setattr(repo, '_to_branch_saved_revision', change_actual_ancestor)
        code, rejected = _request('POST', tour_url(server) + '/save', {
            'expected_draft_version': view['draft_version'],
            'expected_calendar_tour_fingerprint': view['tour_fingerprint'],
        })
        assert injected and code == 409, rejected
        assert repo._origin_projection_values == before_failed_save_origins
        assert 'dependenc' in str(rejected).lower()
        monkeypatch.setattr(repo, '_to_branch_saved_revision', original_decode)
        after = inspect(server)
        assert after['saved_head_revision_id'] == saved['revision_id']
        assert after['tour_fingerprint'] == view['tour_fingerprint'] and not after['saved']
        # A different captured body cannot reuse the old completed math proof,
        # even when its changed field does not itself alter sporting outcomes.
        base_payload = repository_module.viewer_branch_saved_revision_payload

        def changed_capture(**kwargs):
            payload = base_payload(**kwargs)
            payload['content']['test_actual_capture_change'] = {'value': 'new'}
            return payload

        monkeypatch.setattr(repository_module, 'viewer_branch_saved_revision_payload', changed_capture)
        replayed.clear()
        assert save_tour(server)['revision_id'] != saved['revision_id']
        assert len(replayed) == 1


@pytest.mark.parametrize('mode', ['canonical', 'private-mutation', 'noncanonical-encoding'])
def test_origin_projection_seeding_binds_complete_current_raw_payload(
    tmp_path, prepared_slots, monkeypatch, mode,
):
    from sqlalchemy import text

    from beta_engine.infrastructure.db import calendar_global_slot_origins as origins
    from beta_engine.infrastructure.db.calendar_tour import _origin_inputs
    from beta_engine.infrastructure.db.models import (
        BranchSavedRevisionModel,
        RunBranchModel,
    )
    from beta_engine.infrastructure.db.repositories import (
        _saved_revision_validation_signature,
    )

    path = tmp_path / ('origin-raw-' + mode + '.db')
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        repo = server.app.state.runtime.repository
        with repo._session_factory() as session:
            session.execute(text('BEGIN'))
            branch = session.get(RunBranchModel, 'branch')
            revision = repo._validated_saved_revision_in_session(
                session=session, model=session.get(BranchSavedRevisionModel, branch.saved_head_revision_id),
            )
            row = session.get(BranchSavedRevisionModel, revision.revision_id)
            actual_payload = json.loads(row.payload_json)
            if mode == 'private-mutation':
                revision.payload['run']['run_id'] = 'forged-private-owner'
                revision.payload['run']['display_name'] = 'Not the actual SQLite payload'
            elif mode == 'noncanonical-encoding':
                row.payload_json = json.dumps(actual_payload, indent=2)
                session.flush()
            signature = _saved_revision_validation_signature(row)
            proofs = {'_global_origin_inputs': {}}
            reads = []
            original_inputs = origins._origin_inputs

            def counted_inputs(current, cache, **kwargs):
                if current.revision_id == revision.revision_id:
                    reads.append(any(key[2] == current.revision_id for key in cache))
                return original_inputs(current, cache, **kwargs)

            with monkeypatch.context() as patch:
                patch.setattr(origins, '_origin_inputs', counted_inputs)
                origins.verify_saved_global_origins(repo, session, revision,
                    sporting_component_proofs=proofs, _validated_value_signature=signature,
                    _reuse_actual_payload=True)
            assert reads and reads[0] is (mode == 'canonical')
            projected, _ = _origin_inputs(row, proofs['_global_origin_inputs'])
            assert projected['run'] == actual_payload['run']
            assert projected['branch'] == actual_payload['branch']
            assert projected['content']['calendar_tour_authority'] == actual_payload['content']['calendar_tour_authority']
            session.rollback()


def test_verified_working_health_reuses_only_the_complete_unchanged_history(tmp_path, prepared_slots, monkeypatch):
    from sqlalchemy import select
    from beta_engine.application import calendar_native_tour_context
    from beta_engine.infrastructure.db.models import PlayerHealthWeekStateModel
    from beta_engine.infrastructure.db.player_health_state import _parse_health_json

    path = tmp_path / 'verified-working-health.db'
    copy_database(prepared_slots, path)
    database = f'sqlite:///{path}'
    with ApiServer(database_url=database) as server:
        repository = server.app.state.runtime.repository
        before = inspect(server)

        def unexpected_duplicate_fold(*_args, **_kwargs):
            raise AssertionError('The complete working payload already passed independent Health replay')

        with monkeypatch.context() as patch:
            patch.setattr(calendar_native_tour_context, 'load_saved_health', unexpected_duplicate_fold)
            # Exercise both the new full proof and an exact subsequent proof hit.
            result, request = execute(server, command(before, 'next-match', name='verified-health-match'))
            assert result['completed'] == 1
            expected = inspect(server)
            assert inspect(server) == expected
            assert _request('POST', tour_url(server) + '/execute', request) == (201, result)
        with repository._session_factory() as session:
            ordinals = list(session.scalars(select(PlayerHealthWeekStateModel.week_ordinal)
                .where(PlayerHealthWeekStateModel.run_id == 'run', PlayerHealthWeekStateModel.branch_id == 'branch')
                .order_by(PlayerHealthWeekStateModel.week_ordinal)))
        assert len(ordinals) > 1
        # A self-consistent change to either an older or the latest actual Health
        # state must invalidate the COMPLETE captured-payload proof and reject.
        for ordinal in (ordinals[0], ordinals[-1]):
            with repository._session_factory.begin() as session:
                row = session.get(PlayerHealthWeekStateModel, ('run', 'branch', ordinal))
                original = row.payload_json, row.fingerprint
                body = json.loads(row.payload_json)
                body['source_initial_world_fingerprint'] = '0' * 64
                row.payload_json = json.dumps(body)
                row.fingerprint = _parse_health_json(row.payload_json).fingerprint
            try:
                assert _request('GET', tour_url(server))[0] == 409
            finally:
                with repository._session_factory.begin() as session:
                    row = session.get(PlayerHealthWeekStateModel, ('run', 'branch', ordinal))
                    row.payload_json, row.fingerprint = original
            assert inspect(server) == expected
    with ApiServer(database_url=database) as reopened:
        assert inspect(reopened) == expected


def test_incremental_checkpoint_hash_is_the_original_full_canonical_hash(tmp_path, prepared_slots):
    import hashlib
    from pydantic_core import to_json
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.domain.tournaments.calendar_global_slots import (
        GlobalCompetitionCheckpoint, GlobalSlot, global_replay_projection_scope, _replay_projections,
    )
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import parse_checkpoint_json
    from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel

    path = tmp_path / 'canonical-prefix-hash.db'
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        execute(server, command(inspect(server), 'next-match', name='canonical-first-result'))
        with server.app.state.runtime.repository._session_factory() as session:
            raw = session.get(CalendarPlayerSportingCheckpointModel, ('run', 'branch')).payload_json
    actual = parse_checkpoint_json(raw)
    states = [actual.model_copy(update={'events': actual.events[:count]}) for count in range(len(actual.events) + 1)]
    slot = actual.events[-1]
    assert isinstance(slot, GlobalSlot) and len(slot.accepted) == 1
    states.extend([
        actual.model_copy(update={'events': actual.events[:-1] + (slot.model_copy(update={'accepted': ()}),)}),
        actual,
        actual.model_copy(update={'run_id': 'běh/漢', 'branch_id': 'větev "🟢"'}),
        actual.model_copy(update={'events': actual.events[:-1] + (slot.model_copy(update={'number': slot.number + 1}),)}),
    ])

    class FutureCheckpoint(GlobalCompetitionCheckpoint):
        future: str

    class FutureSlot(GlobalSlot):
        future: str

    states.append(FutureCheckpoint.model_construct(
        **{key: getattr(actual, key) for key in GlobalCompetitionCheckpoint.model_fields}, future='retained'))
    future_slot = FutureSlot.model_construct(**{key: getattr(slot, key) for key in GlobalSlot.model_fields}, future='retained')
    states.append(actual.model_copy(update={'events': actual.events[:-1] + (future_slot,)}))
    expected = [canonical_hash(value.model_dump(mode='json')) for value in states]
    with global_replay_projection_scope():
        projection = _replay_projections.get()
        projection['collect_checkpoint_value_hashes'] = True
        for index in list(range(len(states))) + list(reversed(range(len(states)))):
            assert states[index].fingerprint == expected[index]
            if type(states[index]) is GlobalCompetitionCheckpoint and all(type(event) is not FutureSlot for event in states[index].events):
                ordered = json.loads(json.dumps(states[index].model_dump(mode='json'), sort_keys=True, ensure_ascii=False))
                assert projection['checkpoint_value_hashes'][expected[index]] == hashlib.sha256(
                    to_json(ordered, inf_nan_mode='constants')).digest()
    for value, fingerprint in zip(states, expected, strict=True):
        assert value.fingerprint == fingerprint


def test_replayed_tour_value_is_private_and_bound_to_complete_actual_state(tmp_path, prepared_slots):
    from sqlalchemy import text
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.calendar_native_competition import replayed_global_tour_value
    from beta_engine.infrastructure.db.models import RunBranchModel

    path = tmp_path / 'private-replayed-tour.db'
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        repository = server.app.state.runtime.repository
        with repository._session_factory() as session:
            session.execute(text('BEGIN'))
            branch = session.get(RunBranchModel, 'branch')
            head = branch.saved_head_revision_id
            proofs = {}
            lineage = repository._validated_branch_revision_lineage_in_session(
                session=session, branch=branch, payload_revision_ids=frozenset({head}),
                sporting_component_proofs=proofs,
            )
            payload = next(row.payload for row in lineage if row.revision_id == head)
            # The routing peek can transfer only this exact raw JSON tree to
            # the structural decoder. Different actual bytes must decode anew.
            from types import SimpleNamespace
            from beta_engine.infrastructure.db.calendar_global_slot_origins import is_global_slot_row
            from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

            physical = session.get(BranchSavedRevisionModel, head)
            observed = {}
            assert is_global_slot_row(physical, _decoded_out=observed)
            decoded = repository._to_branch_saved_revision(physical,
                validate_components=False, validate_native_root=False, _decoded_payload=observed['value'])
            assert decoded.payload == payload
            detached = SimpleNamespace(**{
                column.key: getattr(physical, column.key) for column in BranchSavedRevisionModel.__table__.columns
            })
            changed_json = deepcopy(payload)
            changed_json['run']['display_name'] = 'Changed raw decoding input'
            detached.payload_json = json.dumps(changed_json)
            decoded = repository._to_branch_saved_revision(detached,
                validate_components=False, validate_native_root=False, _decoded_payload=observed['value'])
            assert decoded.payload == changed_json
        scope = dict(run_id='run', branch_id='branch')
        value = replayed_global_tour_value(payload, proofs, **scope)
        assert value is not None
        actual = payload['content']['calendar_tour_authority']
        assert value.model_dump(mode='json') == actual['state']
        original = deepcopy(payload)
        for part in ('run_id', 'branch_id'):
            assert replayed_global_tour_value(payload, proofs, **{**scope, part: 'foreign'}) is None
        changed = deepcopy(payload)
        component = changed['content']['calendar_tour_authority']
        component['state']['receipts'][-1]['request']['command']['audit_reason'] = 'Changed actual source'
        component['fingerprint'] = canonical_hash(component['state'])
        assert replayed_global_tour_value(changed, proofs, **scope) is None
        changed = deepcopy(payload)
        changed['content']['calendar_tour_authority']['fingerprint'] = '0' * 64
        assert replayed_global_tour_value(changed, proofs, **scope) is None
        from beta_engine.infrastructure.db.calendar_native_competition import replayed_global_checkpoint_value
        from beta_engine.infrastructure.db.calendar_standalone_match_state import decode_prevalidated_calendar_sources

        checkpoint = replayed_global_checkpoint_value(payload, proofs, **scope)
        assert checkpoint is not None
        actual_checkpoint = payload['content']['calendar_player_sporting_checkpoint']
        assert checkpoint.model_dump(mode='json') == actual_checkpoint['state']
        decoded = decode_prevalidated_calendar_sources(payload, **scope)
        reused = decode_prevalidated_calendar_sources(payload, **scope, _global_value_proofs=proofs)
        assert reused == decoded
        for part in ('run_id', 'branch_id'):
            assert replayed_global_checkpoint_value(payload, proofs, **{**scope, part: 'foreign'}) is None
        changed = deepcopy(payload)
        changed_cp = changed['content']['calendar_player_sporting_checkpoint']
        changed_cp['state']['unexpected_owner_field'] = True
        assert replayed_global_checkpoint_value(changed, proofs, **scope) is None
        changed_cp['fingerprint'] = canonical_hash(changed_cp['state'])
        assert replayed_global_checkpoint_value(changed, proofs, **scope) is None
        with pytest.raises(ValueError):
            decode_prevalidated_calendar_sources(changed, **scope, _global_value_proofs=proofs)
        changed = deepcopy(payload)
        changed['content']['calendar_player_sporting_checkpoint']['fingerprint'] = '0' * 64
        assert replayed_global_checkpoint_value(changed, proofs, **scope) is None
        retained = proofs['_prefixes']['_global_replayed_checkpoints']
        fingerprint = checkpoint.fingerprint
        retained[fingerprint] = checkpoint.model_copy(update={'branch_id': 'foreign'})
        assert replayed_global_checkpoint_value(payload, proofs, **scope) is None
        retained[fingerprint] = checkpoint

        value.receipts[-1].request['command']['audit_reason'] = 'Mutated private witness'
        assert replayed_global_tour_value(payload, proofs, **scope) is None
        assert payload == original


def test_version_directed_global_decode_preserves_strict_union_validation(tmp_path, prepared_slots):
    from beta_engine.domain.tournaments.calendar_global_slots import GlobalCompetitionCheckpoint
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import parse_checkpoint_json
    from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel

    path = tmp_path / 'strict-dispatch.db'
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        execute(server, command(inspect(server), 'next-match', name='strict-partial-source'))
        with server.app.state.runtime.repository._session_factory() as session:
            row = session.get(CalendarPlayerSportingCheckpointModel, ('run', 'branch'))
            raw = row.payload_json
            expected_hash = row.fingerprint
    original = GlobalCompetitionCheckpoint.model_validate_json(raw)
    directed = parse_checkpoint_json(raw)
    assert directed == original and directed.fingerprint == original.fingerprint == expected_hash
    assert directed.model_dump(mode='json') == original.model_dump(mode='json')
    assert directed.model_dump_json() == original.model_dump_json()
    assert parse_checkpoint_json(raw, _parsed_global_parts={}) == directed
    original_body = json.loads(raw)
    # Version defaults remain accepted exactly as by the original strict Union.
    for part in ('competition_root', 'event'):
        defaulted = deepcopy(original_body)
        value = defaulted['events'][-1] if part == 'event' else defaulted[part]
        value.pop('schema_version')
        defaulted_json = json.dumps(defaulted)
        try:
            expected = GlobalCompetitionCheckpoint.model_validate_json(defaulted_json)
        except ValueError:
            # A historical nondefault root version may require explicit schema.
            for options in ({}, {'_parsed_global_parts': {}}):
                with pytest.raises(ValueError):
                    parse_checkpoint_json(defaulted_json, **options)
        else:
            for options in ({}, {'_parsed_global_parts': {}}):
                assert parse_checkpoint_json(defaulted_json, **options) == expected
    bad = []
    body = deepcopy(original_body); body['unexpected_owner_field'] = True; bad.append(body)
    body = deepcopy(original_body); body['competition_root']['unexpected_root_field'] = True; bad.append(body)
    body = deepcopy(original_body); body['events'][-1]['unexpected_event_field'] = True; bad.append(body)
    body = deepcopy(original_body); body['events'][-1]['number'] = 0; bad.append(body)
    body = deepcopy(original_body); body['events'][-1]['schema_version'] = 'unknown'; bad.append(body)
    for body in bad:
        changed = json.dumps(body)
        with pytest.raises((ValueError, TypeError)):
            GlobalCompetitionCheckpoint.model_validate_json(changed)
        with pytest.raises((ValueError, TypeError)):
            parse_checkpoint_json(changed)


def test_global_draft_read_projects_only_verified_run_and_falls_back_on_changed_bytes(
    tmp_path, prepared_slots, monkeypatch,
):
    from sqlalchemy import text

    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel
    from beta_engine.infrastructure.db.repositories import (
        _saved_revision_validation_signature,
    )

    path = tmp_path / 'draft-run-projection.db'
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        repo = server.app.state.runtime.repository
        with repo._session_factory() as session:
            session.execute(text('BEGIN'))
            expected, full = repo._viewer_branch_working_draft_in_session(
                session=session, run_id='run', branch_id='branch', include_revision_state=True,
            )
            head = full.saved_head_revision_id
            assert full.saved_revision.payload['content']['calendar_tour_authority']
            signature = _saved_revision_validation_signature(session.get(BranchSavedRevisionModel, head))
        original_decode = repo._to_branch_saved_revision
        materialized = []

        def decoded(model, **kwargs):
            if model.revision_id == head:
                materialized.append(head)
            return original_decode(model, **kwargs)

        monkeypatch.setattr(repo, '_to_branch_saved_revision', decoded)
        assert repo.get_viewer_branch_working_draft(run_id='run', branch_id='branch') == expected
        assert not materialized, 'complete actual graph plus exact Run projection needs no full head DTO'
        with repo._revision_validation_lock:
            projected = repo._revision_run_projection_cache.pop(signature)
        assert repo.get_viewer_branch_working_draft(run_id='run', branch_id='branch') == expected
        assert materialized, 'evicted projection must take the full validated payload path'
        with repo._revision_validation_lock:
            repo._revision_run_projection_cache[signature] = projected
        materialized.clear()
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, head)
            original_raw = row.payload_json
            row.payload_json = json.dumps(json.loads(original_raw), indent=2)
        assert repo.get_viewer_branch_working_draft(run_id='run', branch_id='branch') == expected
        assert materialized, 'the same declared hash cannot certify different actual raw bytes'
        with repo._session_factory.begin() as session:
            session.get(BranchSavedRevisionModel, head).payload_json = original_raw
        materialized.clear()
        assert repo.get_viewer_branch_working_draft(run_id='run', branch_id='branch') == expected
        assert not materialized


def test_metadata_only_global_history_keeps_payload_until_physical_gates_finish(
    tmp_path, prepared_slots, monkeypatch
):
    from sqlalchemy import text

    from beta_engine.infrastructure.db import calendar_terminal_results
    from beta_engine.infrastructure.db.models import BranchSavedRevisionModel, RunBranchModel

    path = tmp_path / "metadata-source-gates.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo = server.app.state.runtime.repository
        verify = calendar_terminal_results.verify_saved_terminal_results
        checked = []

        def complete_payload(repository, session, revision, **kwargs):
            physical = session.get(BranchSavedRevisionModel, revision.revision_id)
            raw = json.loads(physical.payload_json)
            if raw.get("content", {}).get("calendar_tour_authority", {}).get("state", {}).get("schema_version") == "calendar_tour_authority.v5":
                assert revision.payload == raw
                checked.append(revision.revision_id)
            return verify(repository, session, revision, **kwargs)

        monkeypatch.setattr(calendar_terminal_results, "verify_saved_terminal_results", complete_payload)
        with repo._session_factory() as session:
            session.execute(text("BEGIN"))
            lineage = repo._validated_branch_revision_lineage_in_session(
                session=session, branch=session.get(RunBranchModel, "branch"),
                payload_revision_ids=frozenset(),
            )
        assert checked
        assert all(not revision.payload for revision in lineage)
        ancestor_id = checked[0]
        checked.clear()
        with repo._session_factory() as session:
            session.execute(text("BEGIN"))
            warm = repo._validated_branch_revision_lineage_in_session(
                session=session, branch=session.get(RunBranchModel, "branch"),
                payload_revision_ids=frozenset(),
            )
        assert warm == lineage
        assert not checked, "unchanged complete graph and absent closure need only metadata"
        expected_draft = repo.get_viewer_branch_working_draft(run_id='run', branch_id='branch')

        # A newly inserted, rehashed marker must invalidate that absence proof,
        # even though every sporting/Tour component remains byte-for-byte equal.
        from beta_engine.domain.run_revisions import saved_revision_content_hash

        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, ancestor_id)
            original_bytes = row.payload_json, row.content_hash
            body = json.loads(row.payload_json)
            body["run"]["native_branch_closures"] = "not a closure history"
            row.payload_json = json.dumps(body)
            row.content_hash = saved_revision_content_hash(
                revision_id=row.revision_id, run_id=row.run_id, branch_id=row.branch_id,
                sequence=row.sequence, parent_revision_id=row.parent_revision_id,
                kind=row.kind, payload_schema_version=row.payload_schema_version,
                payload=body, change_summary=json.loads(row.change_summary_json),
            )
        with repo._session_factory() as session, pytest.raises(ValueError, match="[Cc]losure"):
            session.execute(text("BEGIN"))
            repo._validated_branch_revision_lineage_in_session(
                session=session, branch=session.get(RunBranchModel, "branch"),
                payload_revision_ids=frozenset(),
            )
        with pytest.raises(ValueError, match='[Cc]losure'):
            repo.get_viewer_branch_working_draft(run_id='run', branch_id='branch')
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, ancestor_id)
            row.payload_json, row.content_hash = original_bytes
        with repo._session_factory() as session:
            session.execute(text("BEGIN"))
            assert repo._validated_branch_revision_lineage_in_session(
                session=session, branch=session.get(RunBranchModel, "branch"),
                payload_revision_ids=frozenset(),
            ) == lineage
        assert repo.get_viewer_branch_working_draft(run_id='run', branch_id='branch') == expected_draft


def test_first_global_edition_after_birth_keeps_the_actual_native_root(tmp_path):
    from tests.api.test_calendar_native_birth_week_execution import sign_prospects

    database = f"sqlite:///{tmp_path / 'birth-global-upgrade.db'}"
    with ApiServer(database_url=database) as server:
        clock = RunCalendar(52, 1, 2030, 3)
        repo, _ = setup(server, clock, 4)
        sign_prospects(server, repo, clock)
        execute(server, command(inspect(server), "transition", name="global-admit"))
        saved = save_tour(server)
        born = inspect(server)
        assert born["state"]["schema_version"] == "calendar_tour_authority.v3"
        week = born["state"]["week"]
        execute(server, command(born, "create-edition", name="first-global-after-birth", data={
            "schema_version": "calendar_tournament_edition.v2",
            "simulation_seed": 891, "edition_id": "born-global", "name": "Born global",
            "week": {**week, "week": 5}, "announcement_week": {**week, "week": 4},
            "start_slot": 1, "main_entrant_count": 4, "ranked": True,
            "validity_weeks": 52,
            "point_table": {"champion": 100, "finalist": 60, "semifinal": 30},
        }))
        upgraded = inspect(server)
        assert upgraded["state"]["competition_root_tour"] == born["state"]
        assert upgraded["state"]["competition_root_saved_head"] == saved["revision_id"]
        save_tour(server)
        expected = inspect(server)["state"]
    with ApiServer(database_url=database) as reopened:
        assert inspect(reopened)["state"] == expected


def test_real_overlapping_slots_save_restart_and_points(tmp_path, prepared_slots, monkeypatch):
    path = tmp_path / "slots.db"
    copy_database(prepared_slots, path)
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        view = inspect(server)
        assert view["next_slot"]["number"] == 4
        assert view["next_slot"]["remaining"] == 4
        result, request = execute(
            server, command(view, "next-match", name="first-match")
        )
        assert result["completed"] == 1 and result["remaining"] == 3
        assert _request("POST", tour_url(server) + "/execute", request) == (201, result)
        save_tour(server)
        snapshot = inspect(server)["next_slot"]["snapshot_fingerprint"]
    with ApiServer(database_url=db) as server:
        view = inspect(server)
        assert view["next_slot"]["snapshot_fingerprint"] == snapshot
        assert view["next_slot"]["remaining"] == 3
        execute(server, command(view, "next-slot", name="complete-first-slot"))
        save_tour(server)
        assert inspect(server)["next_slot"]["number"] == 5
        execute(server, command(inspect(server), "next-slot", name="finals-slot"))
        save_tour(server)
        view = inspect(server)
        assert view["next_slot"] is None
        for eid in ("parallel-a", "parallel-b"):
            assert len(view["edition_evidence"][eid]["matches"]) == 3
            execute(
                server,
                command(
                    inspect(server),
                    "confirm-result",
                    name=eid + ":confirm",
                    edition_id=eid,
                ),
            )
            save_tour(server)
        execute(server, command(inspect(server), "transition", name="publish-points"))
        save_tour(server)
        rows = inspect(server)["state"]["rankings"][-1]["rows"]
        assert sorted(r["points"] for r in rows) == [30, 30, 30, 30, 60, 60, 100, 100]
        from sqlalchemy import text
        from beta_engine.application.calendar_tour_service import CalendarTourService
        from beta_engine.domain.run_packages import canonical_hash
        from beta_engine.domain.tournaments.calendar_global_slots import _replay_projections

        service = CalendarTourService(server.app.state.runtime.repository)
        with service.repository._session_factory() as session:
            session.execute(text("BEGIN"))
            fingerprints = {}
            ctx, state, signed = service._context(session, 'run', 'branch', _fingerprints=fingerprints)
            # The uncached projection and the private scoped projection must
            # return the same actual complete histories and public JSON DTO.
            expected = service._inspection_from_context(session, 'run', 'branch', ctx, state, signed, fingerprints)
        # The public envelope also carries optional Save value continuity.
        # Derive it independently from the complete immutable Saved payload;
        # keep the full sporting DTO equality below, including after failure.
        record = service.repository.get_branch_saved_revision(
            revision_id=expected["saved_head_revision_id"],
        )
        expected["save_projection_fingerprint"] = canonical_hash(record.payload)
        assert service.inspect(run_id='run', branch_id='branch') == expected
        assert _replay_projections.get() is None

        def interrupted_projection(*_args):
            assert _replay_projections.get() is not None
            raise ValueError('Interrupted private inspection')

        with monkeypatch.context() as patch:
            patch.setattr(service, '_inspection_from_context', interrupted_projection)
            with pytest.raises(ValueError, match='Interrupted private inspection'):
                service.inspect(run_id='run', branch_id='branch')
        assert _replay_projections.get() is None
        assert service.inspect(run_id='run', branch_id='branch') == expected


def sporting(server):
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
        load_checkpoint,
    )

    with server.app.state.runtime.repository._session_factory() as session:
        return load_checkpoint(session, run_id="run", branch_id="branch")


def test_batch_matches_reverse_order_save_and_engine_free_reads(
    tmp_path, prepared_slots, monkeypatch
):
    from beta_engine.domain.matches.match_engine import MatchEngine

    outcomes = []
    elapsed = []
    for mode in ("batch", "reverse"):
        path = tmp_path / f"{mode}.db"
        copy_database(prepared_slots, path)
        started = time.monotonic()
        with ApiServer(database_url=f"sqlite:///{path}") as server:
            view = inspect(server)
            if mode == "batch":
                execute(server, command(view, "next-slot", name="whole-slot"))
            else:
                for i, mid in enumerate(
                    reversed([m["match_id"] for m in view["next_slot"]["matches"]])
                ):
                    execute(
                        server,
                        command(
                            inspect(server),
                            "next-match",
                            name=f"match-{i}",
                            data={"match_id": mid},
                        ),
                    )
                    if i == 1:
                        save_tour(server)
            # Repeated identical reads use byte-bound completed proofs.
            inspect(server)
            with monkeypatch.context() as patch:
                patch.setattr(
                    MatchEngine,
                    "simulate",
                    lambda *args, **kwargs: pytest.fail("GET recalculated a match"),
                )
                for _ in range(3):
                    assert inspect(server)["next_slot"]["number"] == 5
            save_tour(server)
            execute(server, command(inspect(server), "next-slot", name="final-slot"))
            save_tour(server)
            outcomes.append(sporting(server))
        elapsed.append(time.monotonic() - started)
    assert outcomes[0] == outcomes[1]
    assert len(outcomes[0].tournaments[-2:]) == 2
    print({"actual_batch_and_reverse_seconds": elapsed}, flush=True)


def test_partial_source_public_fork_is_independent(tmp_path, prepared_slots):
    from tests.api.test_native_fork_public_continuation import Tour, fork

    path = tmp_path / "partial-fork.db"
    copy_database(prepared_slots, path)
    db = f"sqlite:///{path}"
    with ApiServer(database_url=db) as server:
        execute(server, command(inspect(server), "next-match", name="source-partial"))
        saved = save_tour(server)
        source = sporting(server)
        created = fork(server, saved["revision_id"], name="Independent partial slot")
        target = Tour(server, created["branch_id"])
        assert target.view()["next_slot"]["remaining"] == 3
        target_result, target_request = target.execute("next-match", "target-second-match")
        status, projected = _request(
            "POST", target.url + "/execute?include_inspection=true", target_request,
        )
        assert status == 201, projected
        assert projected["schema_version"] == "calendar_tour_execution_inspection.v1"
        assert projected["result"] == target_result
        assert projected["inspection"] == target.view()
        target_partial = target.save()
        nested_created = fork(
            server,
            target_partial["revision_id"],
            branch=created["branch_id"],
            name="Nested independent partial slot",
        )
        nested = Tour(server, nested_created["branch_id"])
        assert nested.view()["next_slot"]["remaining"] == 2
        assert nested.view()["next_slot"]["completed"] == 2
        nested.execute("next-slot", "nested-rest-of-slot")
        nested.save()
        assert nested.view()["next_slot"]["number"] == 5
        nested.execute("next-slot", "nested-finals")
        nested.save()
        for eid in ("parallel-a", "parallel-b"):
            nested.execute("confirm-result", eid + ":nested-confirm", edition_id=eid)
            nested.save()
        nested.advance("nested-points")
        assert sorted(
            r["points"] for r in nested.view()["state"]["rankings"][-1]["rows"]
        ) == [30, 30, 30, 30, 60, 60, 100, 100]
        assert target.view()["next_slot"]["remaining"] == 2
        target.execute("next-slot", "target-rest-of-slot")
        target.save()
        assert target.view()["next_slot"]["number"] == 5
        target.execute("next-slot", "target-finals")
        target.save()
        assert sporting(server) == source
        for eid in ("parallel-a", "parallel-b"):
            target.execute("confirm-result", eid + ":target-confirm", edition_id=eid)
            target.save()
        target.advance("target-points")
        assert sorted(
            r["points"] for r in target.view()["state"]["rankings"][-1]["rows"]
        ) == [30, 30, 30, 30, 60, 60, 100, 100]
        assert inspect(server)["next_slot"]["remaining"] == 3


def test_full_simulation_uses_slot_children_and_frozen_target(tmp_path, prepared_slots):
    from tests.api.test_native_full_simulation_tasks import resume, reviewed, start

    path = tmp_path / "slot-worker.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        original = reviewed(
            server, {"season_index": 0, "week": 5}, name="global-slot-worker"
        )
        task = start(server, original)
        assert task["checkpoint"] == "native_manual_save_required", task
        assert inspect(server)["next_slot"]["number"] == 5
        save_tour(server)
        task = resume(server, task, "saved-first-slot")
        assert task["checkpoint"] == "native_manual_save_required", task
        assert inspect(server)["next_slot"] is None
        save_tour(server)
        task = resume(server, task, "saved-finals-slot")
        assert task["checkpoint"] == "native_result_review_required", task
        for eid in ("parallel-a", "parallel-b"):
            execute(
                server,
                command(
                    inspect(server),
                    "confirm-result",
                    name=eid + ":worker-confirm",
                    edition_id=eid,
                ),
            )
            save_tour(server)
        task = resume(server, task, "confirmed-both-results")
        assert task["checkpoint"] == "native_manual_save_required", task
        save_tour(server)
        task = resume(server, task, "saved-next-week")
        assert task["state"] == "target_reached", task
        state = inspect(server)["state"]
        child_actions = [
            r["request"]["command"]["action"]
            for r in state["receipts"]
            if r["command_id"].startswith("nfs-")
        ]
        assert child_actions == ["next-slot", "next-slot", "transition"]
        assert state["week"]["week"] == 5


def test_retry_concurrent_stale_rollback_and_rehashed_slot(
    tmp_path, prepared_slots, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor

    from beta_engine.application import calendar_tour_service
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.models import (
        CalendarPlayerSportingCheckpointModel,
        CalendarTourAuthorityModel,
    )
    from tests.api.test_player_generation_calendar_gate import _dump

    path = tmp_path / "negative.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo = server.app.state.runtime.repository
        view = inspect(server)
        viewer_url = server.base_url + "/viewer/runs/run/calendar-tour"
        code, public = _request("GET", viewer_url)
        assert code == 200, public
        # Warm publication reauthenticates actual Saved bytes and sources, but
        # cannot run the MatchEngine again just to project that same history.
        from beta_engine.domain.matches.match_engine import MatchEngine

        def unexpected_replay(*_args, **_kwargs):
            raise AssertionError("Authenticated publication replayed accepted matches")

        with monkeypatch.context() as patch:
            patch.setattr(MatchEngine, "simulate", unexpected_replay)
            assert _request("GET", viewer_url) == (200, public)
        first = command(view, "next-match", name="concurrent-exact")
        stale = command(view, "next-match", name="concurrent-other")
        requests = []
        for cmd in (first, stale):
            code, preview = _request("POST", tour_url(server) + "/preview", cmd)
            assert code == 200, preview
            requests.append(
                {
                    "command": cmd,
                    "expected_preview_fingerprint": preview["preview_fingerprint"],
                    "explicit_confirmation": True,
                }
            )
        before = _dump(path)

        def fail(point):
            if point == "after_global_slot_matches_write":
                raise ValueError("Injected late global-slot rollback")

        with monkeypatch.context() as patch:
            patch.setattr(calendar_tour_service, "_fault_injection_point", fail)
            assert (
                _request("POST", tour_url(server) + "/execute", requests[0])[0] == 409
            )
        assert _dump(path) == before
        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = list(
                pool.map(
                    lambda _: _request(
                        "POST", tour_url(server) + "/execute", requests[0]
                    ),
                    range(2),
                )
            )
        assert attempts[0] == attempts[1] and attempts[0][0] == 201
        assert _request("POST", tour_url(server) + "/execute", requests[1])[0] == 409
        forged_request = deepcopy(requests[0])
        forged_request["command"]["seed"] += 1
        assert _request("POST", tour_url(server) + "/execute", forged_request)[0] == 409
        assert inspect(server)["next_slot"]["completed"] == 1
        # A self-consistent rehash of unused frozen inputs is not source proof.
        with repo._session_factory.begin() as session:
            row = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch"))
            tour = session.get(CalendarTourAuthorityModel, ("run", "branch"))
            originals = (
                row.payload_json,
                row.fingerprint,
                tour.payload_json,
                tour.fingerprint,
            )
            body = json.loads(row.payload_json)
            body["events"][-1]["scheduled"][-1]["seed"] += 1
            row.payload_json, row.fingerprint = json.dumps(body), canonical_hash(body)
            state = json.loads(tour.payload_json)
            state["checkpoint_fingerprint"] = row.fingerprint
            tour.payload_json, tour.fingerprint = (
                json.dumps(state),
                canonical_hash(state),
            )
        assert _request("GET", tour_url(server))[0] == 409
        with repo._session_factory.begin() as session:
            row = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch"))
            tour = session.get(CalendarTourAuthorityModel, ("run", "branch"))
            row.payload_json, row.fingerprint, tour.payload_json, tour.fingerprint = (
                originals
            )
        assert inspect(server)["next_slot"]["completed"] == 1

        from beta_engine.domain.run_revisions import saved_revision_content_hash
        from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

        source_id = next(
            a["played_saved_head"]
            for a in inspect(server)["state"]["editions"]
            if a["played_saved_head"]
        )
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, source_id)
            original_source = row.payload_json, row.content_hash
            body = json.loads(row.payload_json)
            component = body["content"]["calendar_tour_authority"]
            component["state"]["editions"][0]["edition"]["point_table"]["champion"] += 1
            component["fingerprint"] = canonical_hash(component["state"])
            row.payload_json = json.dumps(body)
            row.content_hash = saved_revision_content_hash(
                revision_id=row.revision_id,
                run_id=row.run_id,
                branch_id=row.branch_id,
                sequence=row.sequence,
                parent_revision_id=row.parent_revision_id,
                kind=row.kind,
                payload_schema_version=row.payload_schema_version,
                payload=body,
                change_summary=json.loads(row.change_summary_json),
            )
        assert _request("GET", tour_url(server))[0] == 409
        assert _request("GET", viewer_url)[0] == 409
        with repo._session_factory.begin() as session:
            row = session.get(BranchSavedRevisionModel, source_id)
            row.payload_json, row.content_hash = original_source
        assert inspect(server)["next_slot"]["completed"] == 1
        assert _request("GET", viewer_url) == (200, public)


def test_restore_partial_slot_retains_accepted_result_and_exact_retry(
    tmp_path, prepared_slots
):
    from tests.api.test_calendar_population_sporting_checkpoint import restore

    path = tmp_path / "restore-partial.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        first, request = execute(
            server, command(inspect(server), "next-match", name="restore-first")
        )
        saved = save_tour(server)
        accepted = sporting(server)
        execute(server, command(inspect(server), "next-match", name="restore-second"))
        save_tour(server)
        restore(server, saved["revision_id"])
        assert sporting(server) == accepted
        assert inspect(server)["next_slot"]["remaining"] == 3
        assert _request("POST", tour_url(server) + "/execute", request) == (201, first)
        execute(server, command(inspect(server), "next-slot", name="restore-rest"))
        save_tour(server)
        assert inspect(server)["next_slot"]["number"] == 5


def test_same_player_collision_blocks_only_affected_matches(tmp_path, prepared_slots):
    from tests.api.test_calendar_population_sporting_checkpoint import restore

    path = tmp_path / "conflict.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo = server.app.state.runtime.repository
        # Select an actual Saved revision before B's applications; no positive
        # authority or MatchEngine evidence is inserted or fabricated.
        with repo._session_factory() as session:
            from sqlalchemy import select

            from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

            source = None
            for row in session.scalars(
                select(BranchSavedRevisionModel).order_by(
                    BranchSavedRevisionModel.sequence.desc()
                )
            ):
                raw = (
                    json.loads(row.payload_json)
                    .get("content", {})
                    .get("calendar_tour_authority", {})
                    .get("state", {})
                )
                editions = {
                    a["edition"]["edition_id"]: a for a in raw.get("editions", [])
                }
                if (
                    set(editions) == {"parallel-a", "parallel-b"}
                    and editions["parallel-a"]["draw"]
                    and not editions["parallel-b"]["submissions"]
                ):
                    source = row.revision_id
                    break
        assert source
        restore(server, source)
        view = inspect(server)
        a = next(
            a
            for a in view["state"]["editions"]
            if a["edition"]["edition_id"] == "parallel-a"
        )
        shared = a["field"]["direct_main_player_ids"][0]
        selected = [shared] + [
            p["player_id"]
            for p in view["players"]
            if p["player_id"] not in a["field"]["direct_main_player_ids"]
        ][:3]
        execute(
            server,
            command(
                view,
                "submit",
                name="conflict-applications",
                edition_id="parallel-b",
                data={"player_ids": selected},
            ),
        )
        for action in ("approve", "draw"):
            execute(
                server,
                command(
                    inspect(server),
                    action,
                    name="conflict-" + action,
                    edition_id="parallel-b",
                ),
            )
        save_tour(server)
        view = inspect(server)
        assert view["next_slot"]["conflicts"][0]["player_id"] == shared
        code, blocked = _request(
            "POST",
            tour_url(server) + "/preview",
            command(view, "next-slot", name="blocked-conflict-slot"),
        )
        assert code == 409 and shared in blocked["detail"]["message"], blocked
        independent = next(
            m
            for m in view["next_slot"]["matches"]
            if shared not in (m["player_a_id"], m["player_b_id"])
        )
        before = next(p for p in sporting(server).players if p.player_id == shared)
        execute(
            server,
            command(
                view,
                "next-match",
                name="independent-with-conflict",
                data={"match_id": independent["match_id"]},
            ),
        )
        assert (
            next(p for p in sporting(server).players if p.player_id == shared) == before
        )
        assert len(sporting(server).players) == 8
        save_tour(server)
        assert (
            _request(
                "POST",
                tour_url(server) + "/preview",
                command(inspect(server), "transition", name="cannot-skip-conflict"),
            )[0]
            == 409
        )


@pytest.mark.parametrize("failure", ["projection", "coupled-write"])
def test_execution_inspection_uses_independent_postwrite_context_and_atomic_retry(
    tmp_path, prepared_slots, monkeypatch, failure,
):
    from beta_engine.application.calendar_tour_service import CalendarTourService
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.models import (
        CalendarPlayerSportingCheckpointModel,
    )
    from tests.api.test_player_generation_calendar_gate import _dump

    path = tmp_path / "execution-inspection.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        view = inspect(server)
        cmd = command(view, "next-match", name="inspection-next-match")
        code, preview = _request("POST", tour_url(server) + "/preview", cmd)
        assert code == 200, preview
        request = {"command": cmd, "expected_preview_fingerprint": preview["preview_fingerprint"],
            "explicit_confirmation": True}
        endpoint = tour_url(server) + "/execute?include_inspection=true"
        before = _dump(path)
        original = CalendarTourService._context
        calls = []

        def context(self, session, *args, **kwargs):
            calls.append(1)
            if failure == "coupled-write" and len(calls) == 2:
                row = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch"))
                body = json.loads(row.payload_json)
                body["branch_id"] = "foreign-owner"
                row.payload_json = json.dumps(body)
                row.fingerprint = canonical_hash(body)
                session.flush()
            return original(self, session, *args, **kwargs)

        def failed_projection(*args, **kwargs):
            raise ValueError("Injected post-verification inspection projection failure")

        with monkeypatch.context() as patch:
            patch.setattr(CalendarTourService, "_context", context)
            if failure == "projection":
                patch.setattr(CalendarTourService, "_inspection_from_context", failed_projection)
            code, refused = _request("POST", endpoint, request)
            assert code == 409, refused
        assert len(calls) == 2, "Both independent before/after physical gates must execute"
        assert _dump(path) == before

        calls.clear()
        def counted(self, *args, **kwargs):
            calls.append(1)
            return original(self, *args, **kwargs)
        with monkeypatch.context() as patch:
            patch.setattr(CalendarTourService, "_context", counted)
            code, response = _request("POST", endpoint, request)
        assert code == 201, response
        assert len(calls) == 2, "Project the verified post-write context without a third full read"
        assert response["schema_version"] == "calendar_tour_execution_inspection.v1"
        assert response["result"]["command_id"] == cmd["command_id"]
        assert response["result"]["action"] == "next-match"
        current = response["inspection"]
        assert current == inspect(server)
        assert current["saved_head_revision_id"] == view["saved_head_revision_id"]
        assert current["checkpoint_fingerprint"] != view["checkpoint_fingerprint"]
        assert not current["saved"] and current["next_slot"]["completed"] == 1
        committed = _dump(path)
        # The stored command receipt and default HTTP contract are unchanged.
        assert _request("POST", tour_url(server) + "/execute", request) == (201, response["result"])
        assert _request("POST", endpoint, request) == (201, response)
        assert _dump(path) == committed


@pytest.mark.parametrize("changed_metadata", [False, True])
def test_confirmed_save_projection_binds_the_entire_actual_payload(
    tmp_path, prepared_slots, changed_metadata,
):
    from beta_engine.infrastructure.db.models import RunContainerModel

    path = tmp_path / "save-projection.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        view = inspect(server)
        cmd = command(view, "next-match", name="save-projection-next")
        status, preview = _request("POST", tour_url(server) + "/preview", cmd)
        assert status == 200, preview
        status, result = _request("POST", tour_url(server) + "/execute?include_inspection=true", {
            "command": cmd, "expected_preview_fingerprint": preview["preview_fingerprint"],
            "explicit_confirmation": True,
        })
        assert status == 201, result
        current = result["inspection"]
        assert len(current["save_projection_fingerprint"]) == 64
        if changed_metadata:
            # A real isolated DB metadata mutation, never a sporting repair.
            # The full Save must capture it; unchanged declared Tour/CP hashes
            # alone cannot authorize reuse of the earlier inspection.
            with server.app.state.runtime.repository._session_factory.begin() as session:
                session.get(RunContainerModel, "run").display_name += " changed"
        status, saved = _request("POST", tour_url(server) + "/save", {
            "expected_draft_version": current["draft_version"],
            "expected_calendar_tour_fingerprint": current["tour_fingerprint"],
        })
        assert status == 201, saved
        binding = saved["saved_projection"]
        assert binding["run_id"] == "run" and binding["branch_id"] == "branch"
        assert binding["previous_saved_head_revision_id"] == current["saved_head_revision_id"]
        assert binding["saved_head_revision_id"] == saved["saved_revision"]["revision_id"]
        assert binding["checkpoint_fingerprint"] == current["checkpoint_fingerprint"]
        assert binding["tour_fingerprint"] == current["tour_fingerprint"]
        if changed_metadata:
            assert binding["payload_fingerprint"] != current["save_projection_fingerprint"]
        else:
            assert binding["payload_fingerprint"] == current["save_projection_fingerprint"]
            expected = {**current, "saved_head_revision_id": binding["saved_head_revision_id"],
                "draft_version": binding["draft_version"], "saved": True,
                "sporting_saved": True, "can_initialize": False}
            assert inspect(server) == expected


def test_save_projection_declines_external_sources_calendar_and_completed_seasons(
    tmp_path, prepared_slots,
):
    from beta_engine.application.calendar_tour_save_projection import (
        saved_inspection_value_fingerprint,
    )
    from beta_engine.infrastructure.db.models import (
        StagedCalendarRankingResultVersionModel,
        StagedCalendarRankingZeroVersionModel,
    )
    path = tmp_path / "save-projection-eligibility.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        repo = server.app.state.runtime.repository
        view = inspect(server)
        assert view["save_projection_fingerprint"]
        record = repo.get_branch_saved_revision(revision_id=view["saved_head_revision_id"])
        with repo._session_factory() as session:
            kwargs = {"expected_head": record.revision_id}
            assert saved_inspection_value_fingerprint(session, record.payload, **kwargs)
            assert saved_inspection_value_fingerprint(session, record.payload, expected_head="foreign") is None
            for unsupported in ("clock", "prospects", "season", "closure", "fork"):
                payload = deepcopy(record.payload)
                if unsupported == "clock":
                    payload["run"]["run_calendar"]["season_count"] += 1
                elif unsupported == "prospects":
                    payload["content"]["run_prospect_source"] = {}
                elif unsupported == "season":
                    payload["content"]["calendar_tour_authority"]["state"]["transitions"].append(
                        {"public_event": {"kind": "season_transition_completed"}})
                elif unsupported == "closure":
                    payload["run"]["native_branch_closures"] = {"branch": {}}
                else:
                    payload["branch"]["forked_from_branch_id"] = "source"
                assert saved_inspection_value_fingerprint(session, payload, **kwargs) is None
        # Adversarial future staging rows are not sporting facts. Their mere
        # presence disables this optimization, even beyond the current week.
        for model in (StagedCalendarRankingZeroVersionModel, StagedCalendarRankingResultVersionModel):
            with repo._session_factory.begin() as session:
                identity = {"zero_id": "untrusted"} if model is StagedCalendarRankingZeroVersionModel else {
                    "edition_id": "untrusted", "player_id": "untrusted"}
                row = model(run_id="run", branch_id="branch", effective_ordinal=1000000,
                    saved_head_revision_id=record.revision_id, fingerprint="0" * 64,
                    payload_json="{}", **identity)
                session.add(row);session.flush()
                assert saved_inspection_value_fingerprint(session, record.payload, expected_head=record.revision_id) is None
                session.delete(row)


def test_cached_native_final_replay_keeps_actual_sources_engine_and_read_only_boundary(
    tmp_path, prepared_slots, monkeypatch,
):
    from beta_engine.domain.matches.match_engine import MatchEngine
    from tests.api.test_calendar_continuation_flow import root as replay_root
    from tests.api.test_player_generation_calendar_gate import _dump

    path = tmp_path / 'cached-final-replay.db'
    copy_database(prepared_slots, path)
    database = f'sqlite:///{path}'
    with ApiServer(database_url=database) as server:
        for number in (1, 2):
            execute(server, command(inspect(server), 'next-slot', name=f'replay-slot-{number}'))
            if number == 1:
                save_tour(server)
        url = replay_root(server) + '/parallel-a:final/replay'
        before = _dump(path)
        assert _request('GET', url)[0] == 409, 'An unsaved final is not historical replay authority'
        assert _dump(path) == before
        save_tour(server)
        code, expected = _request('GET', url)
        assert code == 200 and expected['exact_replay'], expected
        assert expected['historical_owner_scope'] == 'native_competition_checkpoint'
        original_engine = MatchEngine.simulate
        replayed = []

        def actual_engine(self, context, *args, **kwargs):
            replayed.append(context.match_id)
            return original_engine(self, context, *args, **kwargs)

        monkeypatch.setattr(MatchEngine, 'simulate', actual_engine)
        before = _dump(path)
        for _ in range(2):
            assert _request('GET', url) == (200, expected)
        assert replayed.count('parallel-a:final') >= 2, 'Decode reuse must not replace actual replay'
        assert _dump(path) == before
        # Equivalent noncanonical bytes still receive ordinary strict decoding.
        with sqlite3.connect(path) as db:
            raw, fingerprint = db.execute(
                'SELECT payload_json,fingerprint FROM calendar_player_sporting_checkpoints'
            ).fetchone()
            db.execute('UPDATE calendar_player_sporting_checkpoints SET payload_json=?', (raw + ' ',))
        before = _dump(path)
        assert _request('GET', url) == (200, expected)
        assert _dump(path) == before
        with sqlite3.connect(path) as db:
            db.execute('UPDATE calendar_player_sporting_checkpoints SET payload_json=?', (raw,))
        # Warming both DTO caches never authorizes changed live physical data.
        changed = json.loads(raw)
        changed['branch_id'] = 'foreign'
        for actual_raw, actual_fingerprint in ((json.dumps(changed), fingerprint), (raw, '0' * 64)):
            with sqlite3.connect(path) as db:
                db.execute('UPDATE calendar_player_sporting_checkpoints SET payload_json=?,fingerprint=?',
                    (actual_raw, actual_fingerprint))
            before = _dump(path)
            assert _request('GET', url)[0] == 409
            assert _dump(path) == before
        with sqlite3.connect(path) as db:
            db.execute('UPDATE calendar_player_sporting_checkpoints SET payload_json=?,fingerprint=?',
                (raw, fingerprint))
            parent, summary = db.execute(
                'SELECT revision_id,change_summary_json FROM branch_saved_revisions WHERE revision_id='
                '(SELECT parent_revision_id FROM branch_saved_revisions WHERE revision_id='
                '(SELECT saved_head_revision_id FROM run_branches WHERE branch_id=?))', ('branch',),
            ).fetchone()
            db.execute('UPDATE branch_saved_revisions SET change_summary_json=? WHERE revision_id=?',
                ('{"forged":true}', parent))
        # The unchanged current HEAD/cache cannot hide a changed physical ancestor.
        before = _dump(path)
        assert _request('GET', url)[0] == 409
        assert _dump(path) == before
        with sqlite3.connect(path) as db:
            db.execute('UPDATE branch_saved_revisions SET change_summary_json=? WHERE revision_id=?',
                (summary, parent))
        assert _request('GET', url) == (200, expected)
    with ApiServer(database_url=database) as restarted:
        before = _dump(path)
        assert _request('GET', replay_root(restarted) + '/parallel-a:final/replay') == (200, expected)
        assert _dump(path) == before
