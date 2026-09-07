"""Versioned ground-truth facts and a pure pre-alpha squash rules resolver.

Situation generation is probabilistic; adjudication is not. This is the stored
2025 singles-rules subset, not a complete referee/conduct/review simulator.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RallyTerminalTrigger(str, Enum):
    GOOD_RETURN_UNANSWERED = "GOOD_RETURN_UNANSWERED"
    SERVE_FAULT = "SERVE_FAULT"
    RETURN_DOWN = "RETURN_DOWN"
    RETURN_OUT = "RETURN_OUT"
    RETURN_NOT_UP = "RETURN_NOT_UP"
    INTERFERENCE_STOP = "INTERFERENCE_STOP"
    BALL_HIT_PLAYER = "BALL_HIT_PLAYER"
    PROCEDURAL_OR_OFFICIAL_STOP = "PROCEDURAL_OR_OFFICIAL_STOP"
    BALL_COURT_OR_EXTERNAL_STOP = "BALL_COURT_OR_EXTERNAL_STOP"
    HEALTH_STOP = "HEALTH_STOP"
    CONDUCT_STOP = "CONDUCT_STOP"


class OfficialRallyCall(str, Enum):
    POINT_AWARDED = "POINT_AWARDED"
    NO_LET = "NO_LET"
    YES_LET = "YES_LET"
    STROKE = "STROKE"


class RuleFacts(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    striker_player_id: str = Field(min_length=1)
    non_striker_player_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_players(self) -> RuleFacts:
        if self.striker_player_id == self.non_striker_player_id:
            raise ValueError("rules context requires distinct participants")
        return self


class StandardRallyRuleContext(RuleFacts):
    kind: Literal["STANDARD"] = "STANDARD"
    terminal_trigger: Literal[
        RallyTerminalTrigger.GOOD_RETURN_UNANSWERED,
        RallyTerminalTrigger.SERVE_FAULT,
        RallyTerminalTrigger.RETURN_DOWN,
        RallyTerminalTrigger.RETURN_OUT,
        RallyTerminalTrigger.RETURN_NOT_UP,
    ]


class InterferenceRuleContext(RuleFacts):
    kind: Literal["INTERFERENCE"] = "INTERFERENCE"
    fair_view: bool = True
    direct_access: bool = False
    reasonable_swing: bool = True
    front_wall_freedom: bool = True
    reasonable_fear_of_injury: bool = False
    good_return_possible: bool = True
    winning_return: bool = False
    clearing_effort: bool = True
    striker_effort: bool = True
    self_created_path: bool = False
    wrong_footed_recovery: bool = False
    minimal_interference: bool = False
    played_through: bool = False
    swing_prevented: bool = False
    excessive_swing: Literal["NONE", "CAUSED", "EXAGGERATED"] = "NONE"
    turning: bool = False
    turned_to_create_request: bool = False
    attempt: Literal["FIRST", "FURTHER"] = "FIRST"
    non_striker_had_time_to_clear: bool = True
    front_wall_path: Literal["DIRECT", "VIA_OTHER_WALL"] = "DIRECT"

    @model_validator(mode="after")
    def validate_facts(self) -> InterferenceRuleContext:
        if self.winning_return and not self.good_return_possible:
            raise ValueError("a winning return must be a possible good return")
        if self.swing_prevented and self.reasonable_swing:
            raise ValueError("prevented swing cannot also be unobstructed")
        if self.minimal_interference and not all(
            (self.fair_view, self.reasonable_swing, self.front_wall_freedom)
        ):
            raise ValueError(
                "minimal interference cannot deny view, swing or front-wall freedom"
            )
        if self.turned_to_create_request and not self.turning:
            raise ValueError("manufactured turning request requires turning")
        return self


class BallHitPlayerRuleContext(RuleFacts):
    kind: Literal["BALL_HIT_PLAYER"] = "BALL_HIT_PLAYER"
    hit_player: Literal["STRIKER", "NON_STRIKER"]
    ball_phase: Literal["TO_FRONT_WALL", "FROM_FRONT_WALL"]
    good_return_possible: bool = True
    winning_return: bool = False
    front_wall_path: Literal["DIRECT", "VIA_OTHER_WALL"] = "DIRECT"
    attempt: Literal["NONE", "FIRST", "FURTHER"] = "FIRST"
    turning: bool = False
    deliberate_interception: bool = False
    striker_position_caused_hit: bool = False
    interference: InterferenceRuleContext | None = None

    @model_validator(mode="after")
    def validate_facts(self) -> BallHitPlayerRuleContext:
        if self.winning_return and not self.good_return_possible:
            raise ValueError("a winning return must be a possible good return")
        if self.ball_phase == "TO_FRONT_WALL" and self.attempt == "NONE":
            raise ValueError("outbound ball requires an attempted shot")
        if self.interference is not None and (
            self.ball_phase != "FROM_FRONT_WALL"
            or self.hit_player != "STRIKER"
            or self.interference.striker_player_id != self.striker_player_id
            or self.interference.non_striker_player_id != self.non_striker_player_id
        ):
            raise ValueError("related interference must concern the struck striker")
        return self


class ExternalInterruptionRuleContext(RuleFacts):
    kind: Literal["EXTERNAL_INTERRUPTION"] = "EXTERNAL_INTERRUPTION"
    reason: Literal["COURT_CONDITION", "EXTERNAL_DISTRACTION", "BROKEN_BALL"]
    during_live_rally: Literal[True] = True
    neither_player_at_fault: Literal[True] = True
    interruption_elapsed_seconds: float = Field(gt=0, allow_inf_nan=False)


RallyRuleContext = Annotated[
    StandardRallyRuleContext
    | InterferenceRuleContext
    | BallHitPlayerRuleContext
    | ExternalInterruptionRuleContext,
    Field(discriminator="kind"),
]


class EffectiveRallyRulesSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["effective_rally_rules.v1"] = "effective_rally_rules.v1"
    ruleset_version: Literal["world_squash_singles_2025_v1_2_2"] = (
        "world_squash_singles_2025_v1_2_2"
    )
    resolver_version: Literal["pre_alpha_rules_v1"] = "pre_alpha_rules_v1"
    calibration_version: Literal["pre_alpha_rule_situations_v1"] = (
        "pre_alpha_rule_situations_v1"
    )
    interference_probability: float = Field(default=0.04, ge=0, le=0.25)
    ball_hit_probability: float = Field(default=0.004, ge=0, le=0.1)
    external_interruption_probability: float = Field(default=0.001, ge=0, le=0.1)
    # Generation guard only: never changes the verdict for an existing situation.
    max_consecutive_replays: int = Field(default=8, ge=1, le=32)
    unsupported_components: tuple[str, ...] = (
        "referee_errors_and_reviews",
        "conduct_escalation",
        "health_stops",
        "procedural_stops",
        "long_suspension_and_rescheduling",
        "shot_geometry",
    )


def _interference_verdict(
    facts: InterferenceRuleContext,
) -> tuple[OfficialRallyCall, str | None, str]:
    no_let, yes_let, stroke = (
        OfficialRallyCall.NO_LET,
        OfficialRallyCall.YES_LET,
        OfficialRallyCall.STROKE,
    )
    striker, other = facts.striker_player_id, facts.non_striker_player_id
    obstructed = not all(
        (
            facts.fair_view,
            facts.direct_access,
            facts.reasonable_swing,
            facts.front_wall_freedom,
        )
    )
    if not obstructed and not facts.reasonable_fear_of_injury:
        return no_let, other, "8.6.1_NO_INTERFERENCE"
    if not facts.good_return_possible:
        return no_let, other, "8.6.2_NO_GOOD_RETURN"
    if facts.played_through:
        return no_let, other, "8.6.3_PLAYED_THROUGH"
    if facts.minimal_interference:
        return no_let, other, "8.6.4_MINIMAL"
    if not facts.striker_effort or facts.self_created_path:
        return no_let, other, "8.8_STRIKER_PATH_OR_EFFORT"
    if facts.excessive_swing == "CAUSED":
        return no_let, other, "8.10.1_EXCESSIVE_SWING"
    if facts.excessive_swing == "EXAGGERATED":
        return yes_let, None, "8.10.2_EXAGGERATED_SWING"
    if facts.turned_to_create_request:
        return no_let, other, "8.13.3_MANUFACTURED_TURN"
    if facts.swing_prevented:
        return stroke, striker, "8.9.2_SWING_PREVENTED"
    if (
        facts.turning or facts.attempt == "FURTHER"
    ) and not facts.non_striker_had_time_to_clear:
        return yes_let, None, "8.12_8.13_NO_TIME_TO_CLEAR"
    if not facts.front_wall_freedom:
        if facts.turning or facts.attempt == "FURTHER":
            return yes_let, None, "8.11.1_TURN_OR_FURTHER_ATTEMPT"
        if facts.front_wall_path == "DIRECT":
            return stroke, striker, "8.11.1_DIRECT_FRONT_WALL"
        if facts.winning_return:
            return stroke, striker, "8.11.2_WINNING_RETURN"
        return yes_let, None, "8.11.2_VIA_OTHER_WALL"
    if facts.winning_return:
        return stroke, striker, "8.6.7_WINNING_RETURN"
    if facts.wrong_footed_recovery:
        return yes_let, None, "8.8.3_WRONG_FOOTED_RECOVERY"
    if not facts.clearing_effort:
        return stroke, striker, "8.6.5_INSUFFICIENT_CLEARING"
    return yes_let, None, "8.6.6_GOOD_RETURN_AND_CLEARING"


def _verdict(facts: RallyRuleContext) -> tuple[OfficialRallyCall, str | None, str]:
    point, let, stroke = (
        OfficialRallyCall.POINT_AWARDED,
        OfficialRallyCall.YES_LET,
        OfficialRallyCall.STROKE,
    )
    striker, other = facts.striker_player_id, facts.non_striker_player_id
    if isinstance(facts, StandardRallyRuleContext):
        return (
            point,
            striker
            if facts.terminal_trigger == RallyTerminalTrigger.GOOD_RETURN_UNANSWERED
            else other,
            "STANDARD_" + facts.terminal_trigger.value,
        )
    if isinstance(facts, InterferenceRuleContext):
        return _interference_verdict(facts)
    if isinstance(facts, ExternalInterruptionRuleContext):
        return let, None, "EXTERNAL_" + facts.reason
    if facts.ball_phase == "TO_FRONT_WALL":
        if facts.hit_player == "STRIKER":
            return point, other, "6.2.2_BALL_HIT_SHOT_MAKER"
        if not facts.good_return_possible:
            return point, other, "9.1.1_RETURN_NOT_GOOD"
        if facts.turning:
            return (
                stroke,
                striker if facts.deliberate_interception else other,
                "9.1.5_DELIBERATE_INTERCEPTION"
                if facts.deliberate_interception
                else "9.1.5_TURNING",
            )
        if facts.attempt == "FURTHER":
            return let, None, "9.1.4_FURTHER_ATTEMPT"
        if facts.front_wall_path == "DIRECT":
            return stroke, striker, "9.1.2_DIRECT_RETURN"
        if facts.winning_return:
            return stroke, striker, "9.1.3_WINNING_RETURN"
        return let, None, "9.1.3_VIA_OTHER_WALL"
    if facts.hit_player == "STRIKER":
        if facts.interference is not None:
            return _interference_verdict(facts.interference)
        return point, other, "9.2.3_HIT_STRIKER"
    if facts.attempt == "NONE":
        if facts.striker_position_caused_hit:
            return let, None, "9.2.1_STRIKER_POSITION"
        return point, striker, "9.2.1_HIT_NON_STRIKER"
    if facts.good_return_possible:
        return let, None, "9.2.2_GOOD_FURTHER_RETURN"
    return point, other, "9.2.2_NO_GOOD_RETURN"


class RallyRulesResolution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    ruleset_version: Literal["world_squash_singles_2025_v1_2_2"] = (
        "world_squash_singles_2025_v1_2_2"
    )
    resolver_version: Literal["pre_alpha_rules_v1"] = "pre_alpha_rules_v1"
    context: RallyRuleContext
    initial_call: OfficialRallyCall
    final_call: OfficialRallyCall
    point_winner_player_id: str | None
    replay_required: bool
    decision_code: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_verdict(self) -> RallyRulesResolution:
        call, winner, code = _verdict(self.context)
        if (
            self.initial_call != call
            or self.final_call != call
            or self.point_winner_player_id != winner
            or self.replay_required != (call == OfficialRallyCall.YES_LET)
            or self.decision_code != code
        ):
            raise ValueError(
                "stored rules verdict does not follow its ground-truth facts"
            )
        return self


class RallyRulesResolver:
    @staticmethod
    def resolve(context: RallyRuleContext) -> RallyRulesResolution:
        call, winner, code = _verdict(context)
        return RallyRulesResolution(
            context=context,
            initial_call=call,
            final_call=call,
            point_winner_player_id=winner,
            replay_required=call == OfficialRallyCall.YES_LET,
            decision_code=code,
        )
