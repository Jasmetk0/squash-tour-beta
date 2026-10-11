"""Explicit ranking policy for one pure single-group Tournament Edition."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field

from beta_engine.domain.rankings.official import FrozenInput


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentPureGroupsRankingPolicyAuthority(FrozenInput):
    """Ranking reward policy for a pure one-group event.

    Master v68 explicitly permits ranking rewards for group wins but does not define
    a universal final-position ranking table. Therefore this policy owns only the
    actually-played group-win reward; the sporting champion still comes from standings.
    """

    schema_version: Literal["tournament_pure_groups_ranking_policy_authority.v1"] = (
        "tournament_pure_groups_ranking_policy_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    configured_by_command_id: str = Field(min_length=1, max_length=128)
    scope_policy_id: Literal["single_group_only.v1"] = "single_group_only.v1"
    group_component_policy_id: Literal["played_group_match_win_only.v1"] = (
        "played_group_match_win_only.v1"
    )
    played_group_win_points: int = Field(ge=0)

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))
