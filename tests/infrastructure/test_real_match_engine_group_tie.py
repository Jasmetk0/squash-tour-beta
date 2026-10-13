"""Real MatchEngine cyclic Group Tie -> audited SQLite decision -> final table.

Unlike other tie authority fixtures, every score/game/rally in this test comes
from MatchEngine.simulate. This is a *bounded deterministic seed-search
fixture*, NOT a claim that normal production Run auto-seeding creates a tie
or that the Chromium UI has yet completed a genuine cyclic tie.
"""
from __future__ import annotations

import hashlib
import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches import MatchContext, MatchEngine, MatchParticipantContext
from beta_engine.domain.matches.models import MatchTerminationReason
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsBuilder,
    TournamentGroupStandingsUnresolvedTie,
)
from beta_engine.infrastructure.db import (
    tournament_group_standings_authority as standings_module,
    tournament_group_tie_resolution_authority as tie_module,
)
from beta_engine.infrastructure.db.models import (
    Base, RunBranchModel, RunContainerModel,
    TournamentGroupTieResolutionAuthorityModel, TournamentGroupStandingsAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_group_standings_authority import (
    TournamentGroupStandingsAuthorityStore,
)
from beta_engine.infrastructure.db.tournament_group_tie_resolution_authority import (
    TournamentGroupTieResolutionAuthorityStore,
)
from beta_engine.application.run_saved_tour_group_schedule import RunSavedTourGroupSchedule
from beta_engine.application.run_saved_tour_group_standings import (
    resolve_saved_tour_group_standings, resolve_saved_tour_pending_group_ties,
)
from tests.domain.test_match_rally_log import _player
from tests.infrastructure.test_tournament_group_tie_resolution_authority import schedule

pytestmark = pytest.mark.pr_critical


def _engine_cyclic_receipts():
    """Three complete squash matches, played rather than invented.

    All players have identical sporting attributes. The bounded test seed
    search selects only complete naturally played matches whose true game and
    ball-point totals satisfy an exact cyclic tie. It does not edit any sport
    output or rerun a selected match with changed scoreboard data. The
    distinct identity-derived seeds in normal Run Simulation are not controlled
    this way.
    """
    frozen = schedule()
    players = {
        identity: MatchParticipantContext(player=_player(identity, 82))
        for identity in ("A", "B", "C")
    }
    # All three pairings are from the *real* frozen schedule. Player A/B seat
    # orientation is not a result or score override.
    pairings = (
        ("A-B", "A", "B"),
        ("A-C", "C", "A"),
        ("B-C", "B", "C"),
    )
    # For a three-player cycle, three genuine 2-0 results with an equal
    # (winner ball points, loser ball points) signature give each player exactly
    # one win, one loss, two games won/lost and identical 22+k/k+22 totals.
    # Select complete *actual* MatchEngine results; do not construct their games.
    # A fixed scan order makes failures reproducible after engine changes.
    natural = {match_id: {} for match_id, _, _ in pairings}
    results = None
    selected_seeds = None
    for seed in range(1, 161):
        for match_id, left, right in pairings:
            desired_winner = {"A-B": "A", "A-C": "C", "B-C": "B"}[match_id]
            result = MatchEngine(rng=DeterministicRng(seed)).simulate(
                MatchContext(
                    match_id=match_id,
                    player_a=players[left],
                    player_b=players[right],
                    best_of=3,
                    games_to=11,
                    win_by=2,
                ),
            )
            if result.termination_reason != MatchTerminationReason.COMPLETED:
                continue
            if result.winner_player_id != desired_winner or len(result.sets) != 2:
                continue
            score = (
                sum(item.winner_games for item in result.sets),
                sum(item.loser_games for item in result.sets),
            )
            natural[match_id].setdefault(score, (seed, result))

        shared_scores = (set(natural["A-B"]) & set(natural["A-C"])
                         & set(natural["B-C"]))
        if shared_scores:
            chosen = min(shared_scores)
            results = [natural[match_id][chosen][1] for match_id, _, _ in pairings]
            selected_seeds = tuple(
                natural[match_id][chosen][0] for match_id, _, _ in pairings
            )
            break
    assert results is not None, (
        "160 bounded natural MatchEngine seeds did not yield a genuine exact "
        "three-player cyclic tie; inspect player model or engine changes"
    )
    assert selected_seeds is not None
    receipts = []
    for (match_id, _, _), result in zip(pairings, results, strict=True):
        assert result.termination_reason == MatchTerminationReason.COMPLETED
        assert result.rally_log is not None
        assert len(result.rally_log.events) > 0
        assert result.rally_log.scoring_rallies == sum(
            item.winner_games + item.loser_games for item in result.sets
        )
        assert len(result.sets) == 2
        frozen_match = next(m for m in frozen.matches if m.match_id == match_id)
        result_fp = hashlib.sha256(json.dumps(
            result.model_dump(mode="json"), sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        receipts.append(TournamentGroupStandingsBuilder.receipt_from_result(
            scheduled_match=frozen_match,
            result=result,
            result_fingerprint=result_fp,
        ))

    # This assertion guards against the test ceasing to be a genuine exact tie
    # after an intentional MatchEngine semantics/version change.
    winner_graph = {r.winner_player_id for r in results}
    loser_graph = {r.loser_player_id for r in results}
    assert winner_graph == loser_graph == {"A", "B", "C"}
    assert len({r.result_fingerprint for r in receipts}) == 3
    assert all(r.result_kind == "played" and len(r.games) >= 2 for r in receipts)
    # Identical sporting ratios are derived from the actual simulated games.
    # Don't trust copied scoreboard values or hand-constructed set objects.
    try:
        TournamentGroupStandingsBuilder.build(
            schedule=frozen, receipts=tuple(receipts),
            command_id="real-engine-unresolved",
        )
    except TournamentGroupStandingsUnresolvedTie as error:
        assert error.case.player_ids == ("A", "B", "C")
        assert error.case.reason == "automatic_tie_breaks_exhausted"
        return frozen, tuple(receipts), error.case
    raise AssertionError("Real seeded match evidence did not produce an exact tie")


class _ScheduleStore:
    def __init__(self, session):
        self.session = session

    def get(self, *, run_id, branch_id, event_id):
        assert (run_id, branch_id, event_id) == ("run", "branch", "event")
        return self._frozen


def test_engine_generated_group_tie_audit_survives_real_sqlite_reopen(
    tmp_path, monkeypatch,
):
    frozen, receipts, genuine_case = _engine_cyclic_receipts()
    # The production stores validate their exact decision/case and persist
    # genuine authority rows. Only the input fetch adapters are substituted:
    # this test does not claim to exercise normal Run Match-Day orchestration.
    class FrozenScheduleStore(_ScheduleStore):
        _frozen = frozen

    monkeypatch.setattr(tie_module, "TournamentGroupMatchScheduleAuthorityStore", FrozenScheduleStore)
    monkeypatch.setattr(standings_module, "TournamentGroupMatchScheduleAuthorityStore", FrozenScheduleStore)
    monkeypatch.setattr(
        standings_module.TournamentGroupStandingsAuthorityStore,
        "_result_receipts", lambda self, **kwargs: receipts,
    )

    uri = f"sqlite:///{tmp_path / 'real-engine-tie.sqlite'}"
    engine = create_engine(uri)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(RunContainerModel(
            run_id="run", display_name="Engine-produced group cycle",
            timeline_start_season=2000, timeline_end_season=2049,
        ))
        session.add(RunBranchModel(
            branch_id="branch", run_id="run", display_name="Timeline 1",
        ))
        session.commit()

    archive_schedule = RunSavedTourGroupSchedule(
        run_id="run", revision_branch_id="branch", event_id="event",
        authority_fingerprint=frozen.fingerprint,
        group_count=1, group_size=3, match_day_count=3, matches=(),
    )
    with Session(engine) as session:
        store = TournamentGroupTieResolutionAuthorityStore(session)
        case = store.current_unresolved_case(
            run_id="run", branch_id="branch", event_id="event",
        )
        assert case == genuine_case
        authority = store.resolve(
            run_id="run", branch_id="branch", event_id="event",
            command_id="genuine-match-cycle-audit",
            case_fingerprint=case.fingerprint,
            ordered_player_ids=("C", "A", "B"),
            admin_reason="Compared actual simulated rally and game evidence.",
        )
        assert store.current_unresolved_case(
            run_id="run", branch_id="branch", event_id="event",
        ) is None
        session.commit()
    engine.dispose()

    engine = create_engine(uri)
    with Session(engine) as session:
        row = session.get(
            TournamentGroupTieResolutionAuthorityModel,
            ("run", "branch", "event", genuine_case.fingerprint),
        )
        assert row is not None
        assert row.authority_fingerprint == authority.fingerprint
        saved_tie = {
            "run_id": row.run_id, "branch_id": row.branch_id,
            "event_id": row.event_id, "command_id": row.command_id,
            "authority_fingerprint": row.authority_fingerprint,
            "case_fingerprint": row.case_fingerprint,
            "group_match_schedule_fingerprint": row.group_match_schedule_fingerprint,
            "payload_json": row.payload_json,
        }
        intermediate = {"group_tie_resolutions": [saved_tie]}
        assert resolve_saved_tour_group_standings(
            intermediate, run_id="run", branch_id="branch",
            event_id="event", group_schedule=archive_schedule,
        ) is None
        pending = resolve_saved_tour_pending_group_ties(
            intermediate, run_id="run", branch_id="branch",
            event_id="event", group_schedule=archive_schedule,
        )
        assert len(pending) == 1
        assert pending[0].case_fingerprint == genuine_case.fingerprint
        assert pending[0].admin_reason == "Compared actual simulated rally and game evidence."

        completed = TournamentGroupStandingsAuthorityStore(session).generate(
            run_id="run", branch_id="branch", event_id="event",
            command_id="genuine-match-cycle-final",
        )
        assert tuple(x.player_id for x in completed.groups[0].rows) == ("C", "A", "B")
        assert completed.admin_tie_resolutions == (authority.decision,)
        session.commit()
    engine.dispose()

    engine = create_engine(uri)
    with Session(engine) as session:
        row = session.get(
            TournamentGroupStandingsAuthorityModel,
            ("run", "branch", "event"),
        )
        assert row is not None
        frozen_final = {
            "run_id": row.run_id, "branch_id": row.branch_id,
            "event_id": row.event_id, "command_id": row.command_id,
            "authority_fingerprint": row.authority_fingerprint,
            "group_match_schedule_fingerprint": row.group_match_schedule_fingerprint,
            "group_rules_policy_fingerprint": row.group_rules_policy_fingerprint,
            "payload_json": row.payload_json,
        }
        published = resolve_saved_tour_group_standings(
            {**intermediate, "group_standings": [frozen_final]},
            run_id="run", branch_id="branch", event_id="event",
            group_schedule=archive_schedule,
        )
        assert published is not None
        assert published.authority_fingerprint == completed.fingerprint
        assert published.tie_decisions[0].case_fingerprint == genuine_case.fingerprint
        assert [r.player_id for r in published.groups[0].rows] == ["C", "A", "B"]
        assert resolve_saved_tour_pending_group_ties(
            {**intermediate, "group_standings": [frozen_final]},
            run_id="run", branch_id="branch", event_id="event",
            group_schedule=archive_schedule,
        ) == ()
        # The earlier saved projection never retroactively gains a final table.
        assert resolve_saved_tour_group_standings(
            intermediate, run_id="run", branch_id="branch", event_id="event",
            group_schedule=archive_schedule,
        ) is None
    engine.dispose()
