"""Real HTTP/SQLite: next-slot Execute verifies only its appended increment.

Every case runs the production FastAPI/SQLite stack on a copy of the genuinely
produced ``prepared_slots`` Run (real MatchEngine matches). The narrow path must
give exactly the results of the original complete post-write context, fall back
to it for anything it cannot prove, and never weaken a rejection or rollback.
"""

import hashlib
import json
from itertools import count
from uuid import NAMESPACE_URL, uuid5

import pytest

from tests.api.test_calendar_global_slots import copy_database
from tests.api.test_calendar_tour_flow import command, inspect, save_tour, tour_url
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


@pytest.fixture
def stable_ids(monkeypatch):
    """Deterministic Saved revision/draft IDs so two copies are comparable.

    The same factory as scripts/profile_native_week_ab.py: only the API ID
    source is replaced; every gate still runs. Call it again to restart the
    sequence for the next copy.
    """
    from beta_engine.api import deps

    def restart():
        ids = count()
        monkeypatch.setattr(deps, "uuid4", lambda: uuid5(NAMESPACE_URL, f"appended-slot:{next(ids)}"))

    restart()
    return restart


@pytest.fixture
def paths(monkeypatch):
    """Spy on which post-write verification actually accepted each Execute."""
    from beta_engine.application import (
        calendar_tour_appended_slot_verification as module,
    )
    from beta_engine.application.calendar_tour_service import CalendarTourService

    seen = {"narrow": 0, "full": 0}
    narrow, full = module.verify_appended_slot, CalendarTourService._context

    def counted_narrow(*args, **kwargs):
        result = narrow(*args, **kwargs)
        seen["narrow"] += result is not None
        return result

    def counted_full(self, *args, **kwargs):
        seen["full"] += 1
        return full(self, *args, **kwargs)

    monkeypatch.setattr(module, "verify_appended_slot", counted_narrow)
    monkeypatch.setattr(CalendarTourService, "_context", counted_full)
    return seen


def _approved(server, cmd):
    code, preview = _request("POST", tour_url(server) + "/preview", cmd)
    assert code == 200, preview
    return {"command": cmd, "expected_preview_fingerprint": preview["preview_fingerprint"],
            "explicit_confirmation": True}


def _rows(repo):
    from beta_engine.infrastructure.db.models import (
        CalendarPlayerSportingCheckpointModel,
        CalendarTourAuthorityModel,
    )

    with repo._session_factory() as session:
        return tuple(
            (row.payload_json, row.fingerprint)
            for row in (session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch")),
                        session.get(CalendarTourAuthorityModel, ("run", "branch")))
        )


def _history(repo):
    value = repo.get_branch_saved_revision_history(run_id="run", branch_id="branch")
    return [(x.sequence, x.revision_id, x.parent_revision_id, x.kind, x.content_hash,
             hashlib.sha256(json.dumps(x.payload, sort_keys=True).encode()).hexdigest())
            for x in value.saved_revisions]


def _week(server, *, inspection):
    """Every remaining global slot of the week, one Save after the second."""
    suffix = "?include_inspection=true" if inspection else ""
    results = []
    for number in range(8):
        view = inspect(server)
        if view["next_slot"] is None:
            break
        request = _approved(server, command(view, "next-slot", name=f"appended-{number}"))
        code, value = _request("POST", tour_url(server) + "/execute" + suffix, request)
        assert code == 201, value
        results.append(value)
        # An exact retry returns the stored receipt and changes nothing.
        assert _request("POST", tour_url(server) + "/execute" + suffix, request) == (201, value)
        if number == 0:
            # A different payload under the same command ID stays rejected.
            other = json.loads(json.dumps(request))
            other["command"]["seed"] += 1
            assert _request("POST", tour_url(server) + "/execute", other)[0] == 409
        if number == 1:
            # Save after the second slot only: the first slot is verified on a
            # clean Saved owner, the second on an unsaved Working predecessor.
            save_tour(server)
    if not inspect(server)["saved"]:
        save_tour(server)
    return results


@pytest.mark.parametrize("inspection", [False, True])
def test_appended_slots_equal_the_full_postwrite_context_and_survive_restart(
    tmp_path, prepared_slots, monkeypatch, stable_ids, paths, inspection,
):
    from beta_engine.application import (
        calendar_tour_appended_slot_verification as module,
    )

    outcomes = {}
    for mode in ("narrow", "full"):
        path = tmp_path / f"{mode}.db"
        copy_database(prepared_slots, path)
        paths.update(narrow=0, full=0)
        stable_ids()
        with monkeypatch.context() as patch:
            if mode == "full":
                patch.setattr(module, "begin_appended_slot", lambda *args: None)
            with ApiServer(database_url=f"sqlite:///{path}") as server:
                repo = server.app.state.runtime.repository
                results = _week(server, inspection=inspection)
                outcomes[mode] = {"results": results, "view": inspect(server),
                                  "rows": _rows(repo), "history": _history(repo),
                                  "narrow": paths["narrow"]}
            with ApiServer(database_url=f"sqlite:///{path}") as restarted:
                repo = restarted.app.state.runtime.repository
                assert inspect(restarted) == outcomes[mode]["view"]
                assert _rows(repo) == outcomes[mode]["rows"]
                assert _history(repo) == outcomes[mode]["history"]
    narrow, full = outcomes["narrow"], outcomes["full"]
    assert len(narrow["results"]) == 2
    assert narrow["narrow"] == 2 and full["narrow"] == 0
    for key in ("results", "view", "rows", "history"):
        assert narrow[key] == full[key], key
    if inspection:
        assert all(r["schema_version"] == "calendar_tour_execution_inspection.v1" for r in narrow["results"])


def test_next_reader_and_save_reuse_the_recorded_replay_without_matchengine(
    tmp_path, prepared_slots, monkeypatch, paths,
):
    from beta_engine.domain.matches.match_engine import MatchEngine

    path = tmp_path / "proof.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        view = inspect(server)
        request = _approved(server, command(view, "next-slot", name="proof-slot"))
        code, value = _request("POST", tour_url(server) + "/execute", request)
        assert code == 201, value
        assert paths["narrow"] == 1

        def unexpected(*_args, **_kwargs):
            raise AssertionError("A verified Working payload was replayed again")

        with monkeypatch.context() as patch:
            patch.setattr(MatchEngine, "simulate", unexpected)
            draft = inspect(server)
            assert not draft["saved"] and draft["next_slot"]["number"] == 5
            assert _request("POST", tour_url(server) + "/execute", request) == (201, value)
            save_tour(server)
        assert inspect(server)["saved"]


def _install_then(mutate):
    from beta_engine.application.calendar_tour_service import CalendarTourService

    original = CalendarTourService._install_prepared

    def install(self, session, request, prepared):
        result = original(self, session, request, prepared)
        mutate(session)
        session.flush()
        return result

    return install


def _rehash_checkpoint(session, change):
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.models import (
        CalendarPlayerSportingCheckpointModel,
        CalendarTourAuthorityModel,
    )

    row = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch"))
    tour = session.get(CalendarTourAuthorityModel, ("run", "branch"))
    body = json.loads(row.payload_json)
    change(body)
    row.payload_json, row.fingerprint = json.dumps(body), canonical_hash(body)
    state = json.loads(tour.payload_json)
    state["checkpoint_fingerprint"] = row.fingerprint
    tour.payload_json, tour.fingerprint = json.dumps(state), canonical_hash(state)


def _earlier_event(body):
    body["events"][-2]["scheduled"][-1]["seed"] += 1


def _appended_event(body):
    body["events"][-1]["scheduled"][-1]["seed"] += 1


def _foreign_owner(body):
    body["branch_id"] = "foreign-owner"


def _stale_fingerprint(session):
    from beta_engine.infrastructure.db.models import (
        CalendarPlayerSportingCheckpointModel,
    )

    row = session.get(CalendarPlayerSportingCheckpointModel, ("run", "branch"))
    row.fingerprint = "0" * 64


def _changed_lifecycle(session):
    from sqlalchemy import select

    from beta_engine.infrastructure.db.models import PlayerLifecycleWeekStateModel

    row = session.scalars(select(PlayerLifecycleWeekStateModel)
                          .where(PlayerLifecycleWeekStateModel.run_id == "run")
                          .order_by(PlayerLifecycleWeekStateModel.week_ordinal.desc())).first()
    row.fingerprint = "f" * 64


@pytest.mark.parametrize("corruption", [
    "earlier-event", "appended-event", "foreign-owner", "stale-fingerprint", "unrelated-row",
])
def test_unproven_or_corrupt_write_falls_back_and_rolls_back(
    tmp_path, prepared_slots, monkeypatch, paths, corruption,
):
    from beta_engine.application.calendar_tour_service import CalendarTourService

    mutate = {
        "earlier-event": lambda s: _rehash_checkpoint(s, _earlier_event),
        "appended-event": lambda s: _rehash_checkpoint(s, _appended_event),
        "foreign-owner": lambda s: _rehash_checkpoint(s, _foreign_owner),
        "stale-fingerprint": _stale_fingerprint,
        "unrelated-row": _changed_lifecycle,
    }[corruption]
    path = tmp_path / "corrupt.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        # A first ordinary slot makes the corrupted one an append to an
        # existing global-slot history (the "earlier event" exists).
        first = _approved(server, command(inspect(server), "next-slot", name="first-slot"))
        assert _request("POST", tour_url(server) + "/execute", first)[0] == 201
        view = inspect(server)
        before = _dump(path)
        request = _approved(server, command(view, "next-slot", name="corrupted-slot"))
        paths.update(narrow=0, full=0)
        with monkeypatch.context() as patch:
            patch.setattr(CalendarTourService, "_install_prepared", _install_then(mutate))
            code, refused = _request("POST", tour_url(server) + "/execute", request)
        assert code == 409, refused
        # The narrow path proved nothing; the original complete context ran
        # after the write (2 = before and after) and rejected it atomically.
        assert paths == {"narrow": 0, "full": 2}
        assert _dump(path) == before
        code, value = _request("POST", tour_url(server) + "/execute", request)
        assert code == 201, value
        assert paths["narrow"] == 1


def test_benign_unrelated_write_uses_the_full_context_which_still_accepts(
    tmp_path, prepared_slots, monkeypatch, paths,
):
    """An extra same-value row change is outside the proof: full path decides."""
    from beta_engine.application.calendar_tour_service import CalendarTourService
    from beta_engine.infrastructure.db.models import RunBranchModel

    def touch(session):
        branch = session.get(RunBranchModel, "branch")
        session.execute(RunBranchModel.__table__.update()
                        .where(RunBranchModel.branch_id == "branch")
                        .values(display_name=branch.display_name))

    path = tmp_path / "benign.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        request = _approved(server, command(inspect(server), "next-slot", name="benign-slot"))
        paths.update(narrow=0, full=0)
        with monkeypatch.context() as patch:
            patch.setattr(CalendarTourService, "_install_prepared", _install_then(touch))
            code, value = _request("POST", tour_url(server) + "/execute", request)
        assert code == 201, value
        assert paths == {"narrow": 0, "full": 2}


def test_replaced_partial_slot_and_other_actions_keep_the_full_context(
    tmp_path, prepared_slots, paths,
):
    path = tmp_path / "partial.db"
    copy_database(prepared_slots, path)
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        request = _approved(server, command(inspect(server), "next-match", name="partial"))
        paths.update(narrow=0, full=0)
        assert _request("POST", tour_url(server) + "/execute", request)[0] == 201
        assert paths == {"narrow": 0, "full": 2}
        # Completing that partial slot replaces its last event: not an append.
        request = _approved(server, command(inspect(server), "next-slot", name="complete-partial"))
        paths.update(narrow=0, full=0)
        code, value = _request("POST", tour_url(server) + "/execute", request)
        assert code == 201, value
        assert paths == {"narrow": 0, "full": 2}
        # The following ordinary slot appends again.
        request = _approved(server, command(inspect(server), "next-slot", name="finals"))
        paths.update(narrow=0, full=0)
        assert _request("POST", tour_url(server) + "/execute", request)[0] == 201
        assert paths == {"narrow": 1, "full": 1}
