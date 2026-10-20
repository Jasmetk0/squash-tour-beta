"""Pure weekly reducer regression; actual Signed ownership has its HTTP gate."""

from types import SimpleNamespace

import pytest

from beta_engine.domain.players.calendar_native_competition import (
    competition_checkpoint,
)
from beta_engine.domain.rankings.calendar_official import (
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.official import OfficialRankingPolicy
from beta_engine.domain.tournaments.calendar_native_tour_week import (
    prepare_native_tour_week,
)
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarTourPolicy,
    ranking_week,
)
from beta_engine.infrastructure.db.run_prospect_source_state import (
    RUN_PROSPECT_EPOCH_SCHEMA,
    RUN_PROSPECT_SOURCE_SCHEMA,
    RunProspectSourceEpochs,
    RunProspectSourceSnapshot,
)
from tests.domain.test_calendar_native_sporting_checkpoint import prepared
from tests.domain.test_calendar_prospect_birth_event import birth_row, week

pytestmark = pytest.mark.pr_critical


@pytest.mark.parametrize("width,offset", [(52, 1), (61, 37)])
@pytest.mark.parametrize("competition", [False, True])
@pytest.mark.parametrize("birth_week", [3, 4])
def test_week_keeps_historical_epochs_while_selecting_only_its_birth_source(
    width, offset, competition, birth_week
):
    checkpoint, inputs = prepared(width, offset)
    if competition:
        checkpoint = competition_checkpoint(checkpoint)
    clock = checkpoint.week.calendar
    old = RunProspectSourceSnapshot(
        RUN_PROSPECT_SOURCE_SCHEMA, checkpoint.run_id,
        inputs["source"].records, inputs["source"].fingerprint,
    )
    new_row = birth_row(week(clock, 0, birth_week), "next-cohort")
    new = RunProspectSourceSnapshot(
        RUN_PROSPECT_SOURCE_SCHEMA, checkpoint.run_id,
        tuple(sorted((*old.records, new_row), key=lambda r: r["prospect_id"])),
        "a" * 64,
    )
    chain = RunProspectSourceEpochs(
        RUN_PROSPECT_EPOCH_SCHEMA, checkpoint.run_id,
        ((0, old), (2, new)), "e" * 64,
    )
    policy = CalendarTourPolicy(
        effective_week=inputs["lifecycle"][0].week,
        ranking=OfficialRankingPolicy(policy_id="source-epoch-regression", best_n=15),
    )
    ranking = calculate_calendar_official_ranking(
        run_id=checkpoint.run_id, branch_id=checkpoint.branch_id,
        run_calendar=clock, week=ranking_week(checkpoint.week),
        policy=policy.ranking, players=(), results=(),
    )
    state = SimpleNamespace(editions=(), policies=(policy,), rankings=(ranking,))
    historical_bytes = tuple(s.model_dump_json() for s in inputs["lifecycle"])
    impact, successor = prepare_native_tour_week(
        state=state, checkpoint=checkpoint,
        world=SimpleNamespace(world_package_id="world"), source=chain,
        lifecycle=inputs["lifecycle"], health=inputs["health"], clock=clock,
        knockout=inputs["knockout"], command={"action": "transition", "seed": 123},
    )
    assert impact["admitted_player_ids"] == (("next-cohort",) if birth_week == 3 else ())
    event = (
        successor.events[-1].advance.source_birth_event
        if competition else successor.native_weeks[-1].advance.source_birth_event
    )
    assert event.source_run_prospect_fingerprint == new.fingerprint
    assert event.source_run_prospect_fingerprint != chain.fingerprint
    assert tuple(s.model_dump_json() for s in inputs["lifecycle"]) == historical_bytes
    assert impact["ranking"]["rows"] == []
    # Publishing another future epoch cannot reinterpret this confirmed week,
    # including the ranking-adoption proof embedded in its complete receipt.
    future = RunProspectSourceSnapshot(
        RUN_PROSPECT_SOURCE_SCHEMA, checkpoint.run_id,
        tuple(sorted((*new.records, birth_row(week(clock, 0, 5), "later-cohort")),
                     key=lambda r: r["prospect_id"])),
        "b" * 64,
    )
    extended = RunProspectSourceEpochs(
        RUN_PROSPECT_EPOCH_SCHEMA, checkpoint.run_id,
        (*chain.epochs, (4, future)), "f" * 64,
    )
    replayed = prepare_native_tour_week(
        state=state, checkpoint=checkpoint,
        world=SimpleNamespace(world_package_id="world"), source=extended,
        lifecycle=inputs["lifecycle"], health=inputs["health"], clock=clock,
        knockout=inputs["knockout"], command={"action": "transition", "seed": 123},
    )
    assert replayed == (impact, successor)
    # Flattening to today's otherwise valid snapshot must still fail the exact
    # historical birthday comparison; the fix does not waive source authority.
    with pytest.raises(ValueError, match="birth event differs from the Signed source"):
        prepare_native_tour_week(
            state=state, checkpoint=checkpoint,
            world=SimpleNamespace(world_package_id="world"), source=new,
            lifecycle=inputs["lifecycle"], health=inputs["health"], clock=clock,
            knockout=inputs["knockout"], command={"action": "transition", "seed": 123},
        )


@pytest.mark.parametrize("width,offset", [(52, 1), (61, 37)])
def test_first_future_epoch_preserves_the_original_v1_ranking_proof(width, offset):
    from beta_engine.domain.players.calendar_native_ranking_bridge import (
        calculate_native_ranking_from_signed_lifecycle,
    )
    checkpoint, inputs = prepared(width, offset)
    old = RunProspectSourceSnapshot(
        RUN_PROSPECT_SOURCE_SCHEMA, checkpoint.run_id,
        inputs["source"].records, inputs["source"].fingerprint,
    )
    new = RunProspectSourceSnapshot(
        RUN_PROSPECT_SOURCE_SCHEMA, checkpoint.run_id,
        (*old.records, birth_row(week(checkpoint.week.calendar, 0, 4), "future")),
        "a" * 64,
    )
    chain = RunProspectSourceEpochs(
        RUN_PROSPECT_EPOCH_SCHEMA, checkpoint.run_id,
        ((0, old), (2, new)), "e" * 64,
    )
    policy = OfficialRankingPolicy(policy_id="historical-proof", best_n=15)
    previous = calculate_calendar_official_ranking(
        run_id=checkpoint.run_id, branch_id=checkpoint.branch_id,
        run_calendar=checkpoint.week.calendar,
        week=ranking_week(inputs["lifecycle"][0].week), policy=policy,
        players=(), results=(),
    )
    args = {
        "states": inputs["lifecycle"], "world_package_id": "world",
        "submissions": (), "previous": previous, "policy": policy,
    }
    assert calculate_native_ranking_from_signed_lifecycle(source=chain, **args) == (
        calculate_native_ranking_from_signed_lifecycle(source=old, **args)
    )
