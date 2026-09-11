"""Stage the ranking component of a transition from explicitly resolved inputs.

No clock advancement or public publication is performed. The caller resolves
historical sources and owns the transaction around this and other components.
"""

from typing import Literal, Protocol
from pydantic import model_validator

from beta_engine.domain.rankings.official import (
    WithDisciplinaryZeros,
    OfficialRankingPlayer,
    OfficialRankingPolicy,
    OfficialRankingResult,
    OfficialRankingSnapshot,
    RankingWeek,
    calculate_official_ranking,
)


class RankingCandidateStore(Protocol):
    def history(
        self, *, run_id: str, branch_id: str
    ) -> tuple[OfficialRankingSnapshot, ...]: ...

    def append(
        self, snapshot: OfficialRankingSnapshot, *, bootstrap: bool = False
    ) -> OfficialRankingSnapshot: ...


class RankingTransitionContext(WithDisciplinaryZeros):
    run_id: str
    branch_id: str
    completed_week: RankingWeek
    target_week: RankingWeek
    # Explicit even at rollover: never infer the next season's effective policy.
    policy: OfficialRankingPolicy
    players: tuple[OfficialRankingPlayer, ...]
    # Required acknowledgement of this calculator's supported scope.
    discipline: Literal["none", "resolved_zeros"]

    @model_validator(mode="after")
    def acknowledge_discipline(self):
        if self.disciplinary_zeros and self.discipline != "resolved_zeros":
            raise ValueError("Disciplinary zeros require explicit resolved_zeros mode")
        return self



class ResolvedRankingTransition(RankingTransitionContext):
    results: tuple[OfficialRankingResult, ...]


class RankingResultHistory(Protocol):
    def resolve(
        self, *, run_id: str, branch_id: str, week: RankingWeek
    ) -> tuple[OfficialRankingResult, ...]: ...


def stage_official_ranking_from_history(
    store: RankingCandidateStore,
    sources: RankingResultHistory,
    context: RankingTransitionContext,
) -> OfficialRankingSnapshot:
    """Resolve persisted sources at the target boundary, then calculate/stage.

    Both adapters must participate in the same caller-owned transaction.
    Lifecycle, policy and token resolution still belong to the caller.
    """
    context = RankingTransitionContext.model_validate_json(context.model_dump_json())
    results = sources.resolve(
        run_id=context.run_id, branch_id=context.branch_id, week=context.target_week
    )
    return stage_official_ranking_transition(
        store, ResolvedRankingTransition(**context.model_dump(), results=results)
    )


def stage_official_ranking_transition(
    store: RankingCandidateStore, request: ResolvedRankingTransition
) -> OfficialRankingSnapshot:
    """Extend an existing candidate lineage, or verify an exact historical retry.

    Bootstrap is a separate explicit operation. Inputs must contain the complete
    historically resolved roster and results, including uncounted Best N results.
    The adapter validates observable boundaries, not the truth of source claims.
    """
    request = ResolvedRankingTransition.model_validate_json(request.model_dump_json())
    if not request.run_id or not request.branch_id:
        raise ValueError("Ranking Run/Branch identity is required")
    if request.target_week.ordinal != request.completed_week.ordinal + 1:
        raise ValueError("Ranking target must immediately follow completed week")
    if any(
        r.completed_week.ordinal > request.completed_week.ordinal
        for r in request.results
    ):
        raise ValueError("Ranking inputs contain future completed results")
    if any(
        r.first_publication_week.ordinal > request.target_week.ordinal
        for r in request.results
    ):
        raise ValueError("Ranking inputs contain future publication results")
    history = store.history(run_id=request.run_id, branch_id=request.branch_id)
    previous = next((s for s in history if s.week == request.completed_week), None)
    if previous is None:
        raise ValueError("Transition requires the completed week's stored candidate")
    candidate = calculate_official_ranking(
        run_id=request.run_id,
        branch_id=request.branch_id,
        week=request.target_week,
        policy=request.policy,
        players=request.players,
        results=request.results,
        previous=previous, disciplinary_zeros=request.disciplinary_zeros,
    )
    return store.append(candidate)
