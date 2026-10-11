"""Boundary validation for explicit decisions submitted with ranking preparation."""

from beta_engine.domain.rankings.zero_history import RankingZeroVersion


def validate_zero_batch(versions: tuple[RankingZeroVersion, ...], context) -> None:
    if versions and context.discipline != "stored_zeros":
        raise ValueError("Zero decision batches require stored_zeros mode")
    identities = [v.zero.zero_id for v in versions]
    if len(identities) != len(set(identities)):
        raise ValueError("Duplicate zero decision in ranking command")
    players = {p.player_id for p in context.players}
    for version in versions:
        if (version.zero.run_id, version.zero.branch_id) != (context.run_id, context.branch_id):
            raise ValueError("Zero decision and ranking command scope mismatch")
        if version.effective_week != context.target_week:
            raise ValueError("Zero decision must be effective at the ranking target boundary")
        if version.zero.player_id not in players:
            raise ValueError("Zero decision player is missing from the ranking roster")


def canonicalize_zero_batch(payload: dict) -> None:
    if payload.get("zero_versions"):
        payload["zero_versions"].sort(key=lambda v: v["zero"]["zero_id"])
    else:
        payload.pop("zero_versions", None)
