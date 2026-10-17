"""W-aware immutable correction histories, zero histories and horizon lineage."""

from __future__ import annotations

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarRankingPlayer,
    CalendarRankingResult,
    CalendarRankingWeek,
    calculate_calendar_official_ranking,
)
from beta_engine.domain.rankings.calendar_source_history import (
    CalendarRankingResultVersion,
    CalendarRankingZeroVersion,
    resolve_calendar_ranking_sources,
)
from beta_engine.domain.rankings.calendar_official import CalendarDisciplinaryZero
from beta_engine.domain.rankings.official import OfficialRankingPolicy

pytestmark = pytest.mark.pr_critical
RUN, BRANCH = "history-run", "timeline-1"


def w(s: int, n: int) -> CalendarRankingWeek:
    return CalendarRankingWeek(season_index=s, week=n)


def player() -> CalendarRankingPlayer:
    return CalendarRankingPlayer(
        player_id="alex", tie_break_token="stable-alex", tour_entry_week=w(0, 1),
    )


def result(*, W: int, points: int = 80, published: CalendarRankingWeek | None = None):
    return CalendarRankingResult(
        edition_id="final", player_id="alex", source_fingerprint="match-receipt",
        completed_week=w(0, W - 1),
        first_publication_week=published or w(0, W),
        main_points=points,
    )


def rv(W: int, *, points: int = 80,
       effective: CalendarRankingWeek | None = None,
       previous: CalendarRankingResultVersion | None = None,
       branch: str = BRANCH,
       published: CalendarRankingWeek | None = None):
    return CalendarRankingResultVersion(
        run_id=RUN, branch_id=branch,
        effective_week=effective or w(0, W),
        result=result(W=W, points=points, published=published),
        previous_fingerprint=previous.fingerprint if previous else None,
    )


def zv(effective: CalendarRankingWeek, *,
       previous: CalendarRankingZeroVersion | None = None,
       duration: int = 2,
       original: CalendarRankingWeek | None = None,
       branch: str = BRANCH):
    return CalendarRankingZeroVersion(
        effective_week=effective,
        zero=CalendarDisciplinaryZero(
            zero_id="zero-1", run_id=RUN, branch_id=branch,
            player_id="alex", source_fingerprint="sanction-receipt",
            effective_week=original or w(1, 1), duration_weeks=duration,
        ),
        previous_fingerprint=previous.fingerprint if previous else None,
    )


@pytest.mark.parametrize("W,offset", [(52, 1), (61, 37), (80, 37)])
def test_effective_corrections_and_zero_decisions_are_exact_as_of_week(W, offset):
    clock = RunCalendar(W, offset, 2030, 3)
    initial = rv(W)
    corrected = rv(W, points=130, effective=w(1, 1), previous=initial)
    zero = zv(w(1, 1))
    amended_zero = zv(w(1, 2), duration=1, previous=zero)
    kwargs = dict(
        run_calendar=clock, run_id=RUN, branch_id=BRANCH,
        result_versions=(initial, corrected), zero_versions=(zero, amended_zero),
    )
    before = resolve_calendar_ranking_sources(week=w(0, W), **kwargs)
    during = resolve_calendar_ranking_sources(week=w(1, 1), **kwargs)
    after = resolve_calendar_ranking_sources(week=w(1, 2), **kwargs)
    assert before.results[0].points == 80
    assert before.disciplinary_zeros == ()
    assert during.results[0].points == 130
    assert during.disciplinary_zeros[0].duration_weeks == 2
    assert after.disciplinary_zeros[0].duration_weeks == 1
    assert before.source_fingerprint != during.source_fingerprint
    assert during.source_fingerprint != after.source_fingerprint

    policy = OfficialRankingPolicy(policy_id="Best 2", best_n=2)
    candidate = calculate_calendar_official_ranking(
        run_id=RUN, branch_id=BRANCH, run_calendar=clock,
        week=w(1, 1), policy=policy, players=(player(),),
        results=during.results, disciplinary_zeros=during.disciplinary_zeros,
    )
    assert candidate.rows[0].points == 130
    assert len(candidate.rows[0].disciplinary_zeros) == 1
    # The zero is corrected with original effective week unchanged, not
    # restarted by the correction; no phantom weekly penalty after expiry.
    expired = calculate_calendar_official_ranking(
        run_id=RUN, branch_id=BRANCH, run_calendar=clock,
        week=w(1, 2), policy=policy, players=(player(),),
        results=after.results, disciplinary_zeros=after.disciplinary_zeros,
    )
    assert expired.rows[0].disciplinary_zeros == ()
    assert expired.rows[0].points == 130


@pytest.mark.parametrize("W", [52, 61, 80])
def test_future_correction_is_invisible_and_old_manifest_hash_survives_extension(W):
    original = RunCalendar(W, 1, 2030, 2)
    extension = original.extend_to(4)
    first = rv(W)
    correction = rv(W, points=99, effective=w(1, 4), previous=first)
    args = dict(run_id=RUN, branch_id=BRANCH, week=w(1, 3),
                result_versions=(first, correction))
    before = resolve_calendar_ranking_sources(run_calendar=original, **args)
    after = resolve_calendar_ranking_sources(run_calendar=extension, **args)
    assert before == after
    assert before.results[0].points == 80
    assert before.source_fingerprint == after.source_fingerprint
    assert resolve_calendar_ranking_sources(
        run_calendar=extension, **{**args, "week": w(1, 4)}
    ).results[0].points == 99


@pytest.mark.parametrize("W", [52, 61, 80])
def test_immutable_ranking_predecessor_can_cross_a_strict_horizon_extension(W):
    original = RunCalendar(W, 1, 2030, 1)
    extension = original.extend_to(3)
    p = (player(),)
    policy = OfficialRankingPolicy(policy_id="Best 1", best_n=1)
    previous = calculate_calendar_official_ranking(
        run_id=RUN, branch_id=BRANCH, run_calendar=original,
        week=w(0, W), policy=policy, players=p, results=(result(W=W),),
    )
    signed_original = previous.model_dump_json()
    fingerprint = previous.fingerprint
    current = calculate_calendar_official_ranking(
        run_id=RUN, branch_id=BRANCH, run_calendar=extension,
        week=w(1, 1), policy=policy, players=p,
        results=(result(W=W),), previous=previous,
    )
    assert current.previous_fingerprint == fingerprint
    assert previous.model_dump_json() == signed_original
    assert previous.run_calendar == original.to_metadata()
    assert current.run_calendar == extension.to_metadata()
    with pytest.raises(ValueError, match="preceding week"):
        calculate_calendar_official_ranking(
            run_id=RUN, branch_id=BRANCH, run_calendar=original,
            week=w(0, W), policy=policy, players=p,
            results=(result(W=W),),
            previous=current,
        )
    different_basis = RunCalendar(W, 2, 2030, 3)
    with pytest.raises(ValueError, match="preceding week"):
        calculate_calendar_official_ranking(
            run_id=RUN, branch_id=BRANCH, run_calendar=different_basis,
            week=w(1, 1), policy=policy, players=p,
            results=(result(W=W),), previous=previous,
        )


def test_rejects_forged_or_misordered_result_sources_and_original_date_changes():
    clock = RunCalendar(52, 1, 2030, 3)
    first = rv(52)
    edited = rv(52, effective=w(1, 1), points=100, previous=first)
    common = dict(run_calendar=clock, run_id=RUN, branch_id=BRANCH,
                  week=w(1, 2))
    with pytest.raises(ValueError, match="order"):
        resolve_calendar_ranking_sources(
            **common, result_versions=(edited, first),
        )
    with pytest.raises(ValueError, match="lineage"):
        resolve_calendar_ranking_sources(
            **common, result_versions=(
                first, edited.model_copy(update={"previous_fingerprint": "a" * 64})
            ),
        )
    with pytest.raises(ValueError, match="original timing"):
        resolve_calendar_ranking_sources(
            **common, result_versions=(
                first, rv(52, points=99, effective=w(1, 1),
                          previous=first, published=w(1, 1)),
            ),
        )
    with pytest.raises(ValueError, match="scope mismatch"):
        resolve_calendar_ranking_sources(
            **common, result_versions=(rv(52, branch="foreign"),),
        )
    with pytest.raises(ValueError, match="publication origin"):
        resolve_calendar_ranking_sources(
            **common, result_versions=(rv(52, effective=w(1, 1)),),
        )
    with pytest.raises(ValueError, match="outside the Run horizon"):
        resolve_calendar_ranking_sources(
            **common, result_versions=(rv(52, effective=w(3, 1)),),
        )


def test_rejects_forged_zero_changes_duplicate_origin_and_future_effect():
    clock = RunCalendar(80, 37, 2030, 3)
    first = zv(w(1, 1))
    valid = zv(w(1, 2), previous=first, duration=3)
    common = dict(run_calendar=clock, run_id=RUN, branch_id=BRANCH,
                  week=w(1, 2))
    with pytest.raises(ValueError, match="lineage"):
        resolve_calendar_ranking_sources(
            **common, zero_versions=(first, valid.model_copy(
                update={"previous_fingerprint": "0" * 64}
            )),
        )
    with pytest.raises(ValueError, match="original identity"):
        resolve_calendar_ranking_sources(
            **common, zero_versions=(first, zv(
                w(1, 2), previous=first, original=w(1, 2),
            )),
        )
    with pytest.raises(ValueError, match="effective origin"):
        resolve_calendar_ranking_sources(
            **common, zero_versions=(zv(w(1, 2)),),
        )
    with pytest.raises(ValueError, match="scope mismatch"):
        resolve_calendar_ranking_sources(
            **common, zero_versions=(zv(w(1, 1), branch="foreign"),),
        )
    with pytest.raises(ValueError, match="order"):
        resolve_calendar_ranking_sources(
            **common, zero_versions=(valid, first),
        )


def test_calendar_sources_never_allow_legacy_defaults_or_outside_week():
    initial = rv(52)
    args = dict(run_id=RUN, branch_id=BRANCH,
                week=w(0, 52), result_versions=(initial,))
    with pytest.raises(ValueError, match="versioned"):
        resolve_calendar_ranking_sources(
            run_calendar=RunCalendar.legacy_fax(), **args,
        )
    with pytest.raises(ValueError, match="outside the Run horizon"):
        resolve_calendar_ranking_sources(
            run_calendar=RunCalendar(52, 1, 2030, 1),
            **{**args, "week": w(1, 1)},
        )
