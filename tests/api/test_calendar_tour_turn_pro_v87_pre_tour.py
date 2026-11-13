"""Real HTTP/SQLite: Turn Pro runs in the exhibition weeks before Tour initialization.

A v87 Run advances at least once on the exhibition path before the Tour exists. That
Week Transition must give prospects the chance to turn pro, from what each one knew
about itself, without a missing or duplicated decision and without forcing anyone.
The test-only eager calibration is recorded exactly like the default one.
"""

from beta_engine.application import calendar_sporting_week_service as exhibition_service
import json
from types import SimpleNamespace

import pytest

from beta_engine.application import calendar_pre_tour_turn_pro as pre_tour
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.turn_pro_model import default_turn_pro_model_policy
from beta_engine.domain.tournaments.calendar_tour import parse_tour_json
from beta_engine.infrastructure.db.calendar_tour import _verify_pre_tour_turn_pro
from tests.api import test_calendar_population_sporting_checkpoint as population
from tests.api.test_calendar_initial_world_adoption import request as population_request
from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour, setup, tour_url
from tests.api.test_calendar_tour_turn_pro_v87_flow import EAGER, V87, _opening_pros
from tests.api.test_player_generation_calendar_gate import _generation
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def _player(server, player_id):
    code, body = _request("GET", tour_url(server) + f"/players/{player_id}")
    assert code == 200, body
    return body


def _populate(monkeypatch):
    monkeypatch.setattr(
        population, "population_request",
        lambda server, **changes: population_request(server, **{**changes, "lifecycle_policy": V87}),
    )
    monkeypatch.setattr(
        population, "_generation",
        lambda **changes: _generation(**{**changes, "min_age": 15, "max_age": 19}),
    )


def test_exhibition_week_turn_pro_is_recorded_replayable_and_not_repeated(tmp_path, monkeypatch):
    _populate(monkeypatch)
    # Eager calibration only for the pre-Tour week, so a decision is certain.
    monkeypatch.setattr(exhibition_service, "default_turn_pro_model_policy", lambda: EAGER)
    db = f"sqlite:///{tmp_path / 'v87-pre-tour.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(52, 35, 2030, 3), count=20, initialize=False)
        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
        with repo._session_factory() as session:
            checkpoint = load_checkpoint(session, run_id="run", branch_id="branch")
        weekly = checkpoint.weekly_advances[0]
        assert weekly.schema_version == "calendar_sporting_week_advance.v4"
        assert weekly.turn_pro_model == EAGER
        assert weekly.turn_pro_decisions  # Decisions already exist BEFORE Tour initialization.
        # Initializing later under a different default may not invent/redecide the past.
        monkeypatch.setattr(exhibition_service, "default_turn_pro_model_policy", default_turn_pro_model_policy)
        execute(server, command(inspect(server), "initialize"))
        save_tour(server)
        pros, everyone = _opening_pros(repo)
        prospects = everyone - pros
        view = inspect(server)
        record = view["state"]["pre_tour_turn_pro"]
        assert record["schema_version"] == "calendar_pre_tour_turn_pro.v1"
        assert record["model"] == EAGER.model_dump(mode="json")
        # Exactly one exhibition Week Transition (week 1 -> 2) preceded initialization.
        assert [w["target_week"]["week"] for w in record["weeks"]] == [2]
        decisions = record["weeks"][0]["decisions"]
        assert decisions == [d.model_dump(mode="json") for d in weekly.turn_pro_decisions]
        decided = {d["player_id"] for d in decisions}
        assert decided and decided <= prospects and not decided & pros
        for d in decisions:
            assert d["effective_week"]["week"] == 2 and d["decision_source"] == "player_ai"
            evidence = d["evidence"]
            assert evidence["observation"]["player_id"] == d["player_id"]
            assert evidence["observation"]["financial_level"] is None
            assert len(evidence["observation"]["perceived_attributes"]) == 57
        # The read-only player explanation shows the recorded decision and its week.
        some = sorted(decided)[0]
        history = _player(server, some)["turn_pro"]
        assert history["status"] == "professional" and history["source"] == "player_ai_decision"
        assert history["turn_pro_week"]["week"] == 2
        assert history["decision"]["evidence"]["observation"]["player_id"] == some
        # A prospect that did not turn pro stays a prospect (nobody is forced).
        waiting = sorted(prospects - decided)
        if waiting:
            assert _player(server, waiting[0])["turn_pro"]["status"] == "prospect"
        # The next Week Transition (default model, unpatched) never re-decides them.
        monkeypatch.setattr(exhibition_service, "default_turn_pro_model_policy", default_turn_pro_model_policy)
        result, _ = execute(server, command(inspect(server), "transition", name="after-pre-tour"))
        later = {d["player_id"] for d in result["impact"]["turn_pro_decisions"]}
        assert not later & decided
        save_tour(server)
        final = inspect(server)
        assert final["state"]["pre_tour_turn_pro"] == record
    # Cold restart: the recorded evidence is read back unchanged and still verifies.
    with ApiServer(database_url=db) as restarted:
        again = inspect(restarted)
        assert again == final
        assert _player(restarted, some)["turn_pro"]["decision"]["evidence"] == history["decision"]["evidence"]


def _checkpoint_for(record):
    """The exhibition advances a checkpoint must contain for this record (component)."""
    advances = [
        SimpleNamespace(
            schema_version="calendar_sporting_week_advance.v1",
            command_id=w["command_id"], seed=w["seed"],
            completed_week=parse_week(w["completed_week"]), target_week=parse_week(w["target_week"]),
        )
        for w in record["weeks"]
    ]
    return SimpleNamespace(weekly_advances=tuple(advances))


def parse_week(raw):
    from beta_engine.domain.calendar.run_week_position import RunWeekPosition

    return RunWeekPosition.model_validate_json(json.dumps(raw))


def test_pre_tour_record_rejects_missing_changed_or_forged_history(tmp_path, monkeypatch):
    """Component negatives on real HTTP-produced evidence (not a second integration)."""
    _populate(monkeypatch)
    monkeypatch.setattr(exhibition_service, "default_turn_pro_model_policy", lambda: EAGER)
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'neg.db'}") as server:
        setup(server, RunCalendar(52, 35, 2030, 3), count=20)
        raw = inspect(server)["state"]
    state = parse_tour_json(json.dumps(raw))
    world = SimpleNamespace(lifecycle_policy=SimpleNamespace(requires_turn_pro=True))
    checkpoint = _checkpoint_for(raw["pre_tour_turn_pro"])
    _verify_pre_tour_turn_pro(state, checkpoint, world)  # the genuine record verifies

    pre = state.pre_tour_turn_pro
    week = pre.weeks[0]
    decision = week.decisions[0]
    # Missing: an exhibition week without its Turn Pro evaluation.
    with pytest.raises(ValueError, match="lack their recorded Turn Pro"):
        _verify_pre_tour_turn_pro(state.model_copy(update={"pre_tour_turn_pro": None}), checkpoint, world)
    # Duplicated / reordered / foreign history: the week must equal the signed advance.
    forged_seed = pre.model_copy(update={"weeks": (week.model_copy(update={"seed": week.seed + 1}),)})
    with pytest.raises(ValueError, match="differ from the signed exhibition history"):
        _verify_pre_tour_turn_pro(state.model_copy(update={"pre_tour_turn_pro": forged_seed}), checkpoint, world)
    # A Turn Pro record where the world says the historical rule applies.
    with pytest.raises(ValueError, match="without a v87"):
        _verify_pre_tour_turn_pro(
            state, checkpoint, SimpleNamespace(lifecycle_policy=SimpleNamespace(requires_turn_pro=False))
        )
    # Changed decision: a draw that no longer matches the recorded model/observation.
    edited_obs = decision.evidence.observation.model_copy(
        update={"readiness": round(decision.evidence.observation.readiness * 0.5, 12)}
    )
    edited = decision.model_copy(
        update={"evidence": decision.evidence.model_copy(update={"observation": edited_obs})}
    )
    changed = pre.model_copy(update={"weeks": (week.model_copy(update={"decisions": (edited, *week.decisions[1:])}),)})
    with pytest.raises(ValueError, match="internally inconsistent"):
        _verify_pre_tour_turn_pro(state.model_copy(update={"pre_tour_turn_pro": changed}), checkpoint, world)
    # Changed model: the recorded calibration is bound to each decision's provenance.
    other = pre.model_copy(
        update={"model": pre.model.model_copy(update={"readiness_weight": 1.0})}
    )
    with pytest.raises(ValueError, match="draw|provenance"):
        _verify_pre_tour_turn_pro(state.model_copy(update={"pre_tour_turn_pro": other}), checkpoint, world)
    # Foreign Branch decision.
    foreign = decision.model_copy(update={"branch_id": "other-branch"})
    swapped = pre.model_copy(update={"weeks": (week.model_copy(update={"decisions": (foreign, *week.decisions[1:])}),)})
    with pytest.raises(ValueError, match="foreign Run or Branch"):
        _verify_pre_tour_turn_pro(state.model_copy(update={"pre_tour_turn_pro": swapped}), checkpoint, world)


def test_pre_tour_never_pro_retirement_is_saved_before_initialization_and_survives_restart(tmp_path, monkeypatch):
    """Real HTTP/SQLite exception; low chance is a recorded TEST calibration only."""
    from beta_engine.application import calendar_initial_world_adoption_service as adoption
    from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
    from tests.api.test_calendar_tour_player_career_v87 import career
    from tests.api.test_calendar_continuation_flow import root, save_continuation
    from tests.api.test_calendar_sporting_week_flow import advance, weekly_command

    never = EAGER.model_copy(update={"model_id": "test-never-pro.v2", "annual_base_by_age": (1e-12,)})
    policy = {**V87, "automatic_retirement_age": 16}
    monkeypatch.setattr(adoption, "default_turn_pro_model_policy", lambda: never)
    monkeypatch.setattr(exhibition_service, "default_turn_pro_model_policy", lambda: never)
    monkeypatch.setattr(population, "population_request",
                        lambda server, **changes: population_request(server, **{**changes, "lifecycle_policy": policy}))
    monkeypatch.setattr(population, "_generation",
                        lambda **changes: _generation(**{**changes, "min_age": 15, "max_age": 15}))
    db = f"sqlite:///{tmp_path / 'never-pro-pre-tour.db'}"
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, RunCalendar(4, 1, 2030, 3), count=20, initialize=False)
        with repo._session_factory() as session:
            checkpoint = load_checkpoint(session, run_id="run", branch_id="branch")
        # If the first birthday happens later, take the next real explicit weekly step.
        if not checkpoint.weekly_advances[0].retired_without_turn_pro_player_ids:
            code, view = _request("GET", root(server))
            assert code == 200
            prepared, _ = advance(server, weekly_command(view, name="retirement-week-3"))
            save_continuation(server, prepared)
            with repo._session_factory() as session:
                checkpoint = load_checkpoint(session, run_id="run", branch_id="branch")
        week = next(e for e in checkpoint.weekly_advances if e.retired_without_turn_pro_player_ids)
        player = week.retired_without_turn_pro_player_ids[0]
        assert player in week.retired_player_ids and not week.turn_pro_decisions
        source = week.fingerprint
        head = repo.get_viewer_branch_working_draft(run_id="run", branch_id="branch").base_saved_revision_id
        assert repo.verify_branch_saved_revision_hash(revision_id=head)

    # Today's model changes before initialization, but the retirement is already Signed.
    monkeypatch.setattr(exhibition_service, "default_turn_pro_model_policy", lambda: EAGER)
    with ApiServer(database_url=db) as restarted:
        execute(restarted, command(inspect(restarted), "initialize"))
        save_tour(restarted)
        code, body = career(restarted, player)
        assert code == 200, body
        assert body["overview"]["status"] == "retired"
        summary = body["retirement_summary"]
        assert summary["without_turn_pro"] is True
        assert summary["source"]["fingerprint"] == source
        assert summary["retired_week"]["week"] == week.target_week.week
        code, past = career(restarted, player, 0)
        assert code == 200 and past["retirement_summary"] is None
        assert past["overview"]["status"] == "not_professional"
    with ApiServer(database_url=db) as again:
        assert career(again, player) == (200, body)
