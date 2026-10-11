"""Advisory bracket diagnostics for Admin/preflight surfaces.

These diagnostics are deliberately derived and non-authoritative. They must never
change tournament fingerprints or block an otherwise technically valid bracket.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from beta_engine.domain.rankings.official import FrozenInput


BracketDiagnosticCode = Literal[
    "odd_main_entrant_count",
    "majority_first_round_byes",
    "large_main_draw_over_64",
]


class TournamentBracketDiagnostic(FrozenInput):
    severity: Literal["warning"] = "warning"
    code: BracketDiagnosticCode
    message: str = Field(min_length=1)
    entrant_count: int = Field(ge=2)
    bracket_capacity: int = Field(ge=2)
    bye_count: int = Field(ge=0)
    first_round_match_count: int = Field(ge=1)
    first_round_bye_match_count: int = Field(ge=0)
    first_round_bye_share: float = Field(ge=0.0, le=1.0)


def main_bracket_diagnostics(
    *,
    entrant_count: int,
    bracket_capacity: int,
    bye_count: int,
    first_round_bye_match_count: int | None = None,
) -> tuple[TournamentBracketDiagnostic, ...]:
    """Return stable, non-blocking pre-alpha warnings for one Main bracket."""

    if entrant_count < 2:
        raise ValueError("Main bracket diagnostics require at least two entrants")
    if bracket_capacity < 2 or bracket_capacity % 2:
        raise ValueError("Main bracket diagnostics require an even bracket capacity")
    if bye_count < 0 or entrant_count + bye_count != bracket_capacity:
        raise ValueError(
            "Main bracket diagnostics require entrants plus BYEs to equal capacity"
        )

    first_round_match_count = bracket_capacity // 2
    bye_matches = (
        min(bye_count, first_round_match_count)
        if first_round_bye_match_count is None
        else first_round_bye_match_count
    )
    if bye_matches < 0 or bye_matches > first_round_match_count:
        raise ValueError("First-round BYE match count is outside bracket bounds")

    bye_share = bye_matches / first_round_match_count
    diagnostics: list[TournamentBracketDiagnostic] = []

    def warning(code: BracketDiagnosticCode, message: str) -> None:
        diagnostics.append(
            TournamentBracketDiagnostic(
                code=code,
                message=message,
                entrant_count=entrant_count,
                bracket_capacity=bracket_capacity,
                bye_count=bye_count,
                first_round_match_count=first_round_match_count,
                first_round_bye_match_count=bye_matches,
                first_round_bye_share=bye_share,
            )
        )

    if entrant_count % 2:
        warning(
            "odd_main_entrant_count",
            (
                f"! Main Draw has an odd entrant count ({entrant_count}). "
                "Odd fields always receive an Admin warning because opening-round "
                "paths cannot be fully symmetric."
            ),
        )

    if bye_matches * 2 > first_round_match_count:
        warning(
            "majority_first_round_byes",
            (
                f"! {bye_matches} of {first_round_match_count} first-round matches "
                "contain a BYE, so more than half of the opening round is "
                "non-competitive."
            ),
        )

    if entrant_count > 64:
        warning(
            "large_main_draw_over_64",
            (
                f"! Main Draw has {entrant_count} entrants. Fields above 64 players "
                "are exceptional and should be used intentionally rather than as "
                "the normal tournament format."
            ),
        )

    return tuple(diagnostics)
