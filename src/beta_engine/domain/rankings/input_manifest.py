"""Complete immutable inputs for verifying an already stored ranking calculation."""

from beta_engine.domain.rankings.official import (
    WithDisciplinaryZeros, OfficialRankingPlayer, OfficialRankingResult,
    OfficialRankingSnapshot, calculate_official_ranking,
)


class RankingInputManifest(WithDisciplinaryZeros):
    players: tuple[OfficialRankingPlayer, ...]
    results: tuple[OfficialRankingResult, ...]

    def verify(
        self, snapshot: OfficialRankingSnapshot,
        previous: OfficialRankingSnapshot | None,
    ) -> None:
        manifest = RankingInputManifest.model_validate_json(self.model_dump_json())
        reconstructed = calculate_official_ranking(
            run_id=snapshot.run_id, branch_id=snapshot.branch_id,
            week=snapshot.week, policy=snapshot.policy,
            players=manifest.players, results=manifest.results, previous=previous, disciplinary_zeros=manifest.disciplinary_zeros,
        )
        if reconstructed.fingerprint != snapshot.fingerprint:
            raise ValueError("Ranking input manifest does not reproduce stored candidate")
