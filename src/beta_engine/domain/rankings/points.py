"""Pure validation and stage mapping for authored ranking point tables."""

from typing import Any

LEGACY_POINT_STAGE_KEYS = {
    "winner": "champion",
    "semifinalist": "semifinal",
    "quarterfinalist": "quarterfinal",
}

CANONICAL_RANKING_POINT_STAGES = frozenset({
    "champion", "finalist", "semifinal", "quarterfinal",
    "round_of_16", "round_of_32", "round_of_64", "round_of_128",
    "qualification_winner", "qualification_final",
    "qualification_semifinal", "qualification_round",
})


def is_valid_ranking_point(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def normalize_ranking_points_table(values: dict[str, Any]) -> dict[str, int]:
    """Validate authored points and normalize legacy names at an input boundary."""
    normalized: dict[str, int] = {}
    for raw_key, value in values.items():
        key = LEGACY_POINT_STAGE_KEYS.get(str(raw_key), str(raw_key))
        if key not in CANONICAL_RANKING_POINT_STAGES:
            raise ValueError(f"unknown ranking point stage '{raw_key}'")
        if key in normalized:
            raise ValueError(f"ranking point stage '{key}' was authored more than once")
        if not is_valid_ranking_point(value):
            raise ValueError(f"ranking point '{key}' must be an integer greater than or equal to zero")
        normalized[key] = value
    return normalized


def knockout_loss_point_stage(*, draw_type: str, round_number: int, final_round: int) -> str:
    """Canonical loss stage measured against the physical bracket final."""
    distance = final_round - round_number
    if draw_type == "qualification":
        if distance == 0:
            return "qualification_final"
        if distance == 1:
            return "qualification_semifinal"
        return "qualification_round"
    mapping = {
        0: "finalist",
        1: "semifinal",
        2: "quarterfinal",
        3: "round_of_16",
        4: "round_of_32",
        5: "round_of_64",
        6: "round_of_128",
    }
    return mapping.get(distance, "main_draw_participant")
