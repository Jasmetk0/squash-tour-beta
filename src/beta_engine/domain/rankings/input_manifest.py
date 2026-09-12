"""Complete immutable inputs for verifying an already stored ranking calculation."""

from pydantic import Field, model_serializer

from beta_engine.domain.rankings.official import (
    WithDisciplinaryZeros, OfficialRankingPlayer, OfficialRankingResult,
    OfficialRankingSnapshot, calculate_official_ranking,
)


class RankingInputManifest(WithDisciplinaryZeros):
    zeros_from_history: bool = False
    command_request_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_serializer(mode="wrap")
    def serialize_manifest(self, handler):
        data = handler(self)
        if self.command_request_fingerprint is None:
            data.pop("command_request_fingerprint", None)
        if not self.disciplinary_zeros:
            data.pop("disciplinary_zeros", None)
        if not self.zeros_from_history:
            data.pop("zeros_from_history", None)
        return data

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
