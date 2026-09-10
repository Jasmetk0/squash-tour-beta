"""Read-only Admin contracts for unpublished ranking candidates."""

from typing import Literal

from beta_engine.domain.rankings.official import FrozenInput, OfficialRankingSnapshot, RankingWeek
from beta_engine.domain.rankings.result_history import RankingResultVersion


class RankingCandidateDetail(FrozenInput):
    publication_status: Literal["candidate_only"] = "candidate_only"
    snapshot: OfficialRankingSnapshot
    fingerprint: str
    command_ids: tuple[str, ...]


class RankingCandidateHistory(FrozenInput):
    run_id: str
    branch_id: str
    publication_status: Literal["candidate_only"] = "candidate_only"
    candidates: tuple[RankingCandidateDetail, ...]


class RankingSourceDetail(FrozenInput):
    version: RankingResultVersion
    fingerprint: str
    counted: bool


class RankingCandidateSources(FrozenInput):
    run_id: str
    branch_id: str
    week: RankingWeek
    candidate_fingerprint: str
    publication_status: Literal["candidate_only"] = "candidate_only"
    sources: tuple[RankingSourceDetail, ...]
