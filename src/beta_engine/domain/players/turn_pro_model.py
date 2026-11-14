"""Pre-alpha player-AI model for the Master v87 Turn Pro week (pure, deterministic).

Each Week Transition, every eligible prospect has a weekly chance to turn pro. The
chance comes from an annual base by age, scaled in hazard space by strength relative
to current Tour Players ("readiness") and by an opportunity such as a small upcoming
event of the Run's association in the player's country. The annual chance is turned
into a weekly one with the Run's own weeks-per-year W, so W52 and W61 Runs turn pro
at the same rate per year of age.

There is no forced entry age (owner decision): the annual base rises towards
near-certainty, while a rare career may still end without Turn Pro and is recorded.
All numbers in ``default_turn_pro_model_policy`` are provisional calibration.

Randomness: one uniform draw per (seed, Run, Branch, player, target week), derived by
hashing. It does not depend on processing order or on how many other players are
evaluated, so logically simultaneous decisions stay order-independent.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Iterable
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.turn_pro import (
    PlayerTurnProDecision,
    TurnProDecisionEvidence,
)
from beta_engine.domain.players.turn_pro_perception import (
    SelfPerceptionPolicy,
    TurnProObservation,
    default_self_perception_policy,
    perceive_self,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash

FIRST_TURN_PRO_AGE = 15


class TurnProModelPolicy(FrozenInput):
    """Versioned, fingerprinted parameters; never read from current defaults on replay."""

    schema_version: Literal["turn_pro_model.v1"] = "turn_pro_model.v1"
    model_id: str = Field(min_length=1)
    # Annual chance by completed age, starting at 15; the last value applies beyond.
    annual_base_by_age: tuple[float, ...] = Field(min_length=1)
    # Hazard multiplier exp(readiness_weight * (readiness - readiness_reference)).
    readiness_weight: float = Field(ge=0)
    readiness_reference: float = Field(ge=0, le=1)
    home_opportunity_multiplier: float = Field(ge=1)
    provenance: str = Field(min_length=1)
    # Model v2 (owner clarification 11 Nov 2026): readiness comes only from the
    # prospect's own self-perception, never from others' hidden strength, and
    # the player's own personality scales the hazard. Omitted in v1 policies.
    perception: SelfPerceptionPolicy | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    ambition_weight: float | None = Field(
        default=None, ge=0, exclude_if=lambda v: v is None
    )
    professionalism_weight: float | None = Field(
        default=None, ge=0, exclude_if=lambda v: v is None
    )

    # Versioned evidence boundary: when set, every positive decision stores the
    # prospect's own observation (``TurnProDecisionEvidence``). Policies recorded
    # before this field existed omit it and keep their exact bytes/fingerprint.
    decision_evidence: Literal["observation.v1"] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )

    @property
    def uses_self_perception(self) -> bool:
        return self.perception is not None

    @model_validator(mode="after")
    def validate_bases(self):
        if self.decision_evidence is not None and not self.uses_self_perception:
            raise ValueError("Decision evidence needs the self-perception model")
        if self.uses_self_perception != (
            self.ambition_weight is not None and self.professionalism_weight is not None
        ):
            raise ValueError("Self-perception model requires its personality weights")
        bases = self.annual_base_by_age
        if any(not 0 < b < 1 for b in bases):
            raise ValueError("Annual Turn Pro bases must be strictly between 0 and 1")
        if list(bases) != sorted(bases):
            raise ValueError("Annual Turn Pro bases must not fall with age")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def default_turn_pro_model_policy() -> TurnProModelPolicy:
    """Current default: v2 self-perception model (Master v87, 11 Nov 2026)."""
    return TurnProModelPolicy(
        model_id="pre-alpha-turn-pro.v2",
        annual_base_by_age=(0.05, 0.20, 0.40, 0.55, 0.65, 0.75, 0.85, 0.95),
        readiness_weight=2.0,
        readiness_reference=0.5,
        home_opportunity_multiplier=1.5,
        perception=default_self_perception_policy(),
        ambition_weight=1.2,
        professionalism_weight=0.4,
        decision_evidence="observation.v1",
        provenance=(
            "Provisional pre-alpha calibration; readiness from self-perception "
            "only (owner clarification 11 Nov 2026); age bases from research "
            "'Přechod mezi profesionály ve sportu'"
        ),
    )


def true_strength_turn_pro_model_policy_v1() -> TurnProModelPolicy:
    """Historical v1 calibration (true relative strength); replay only."""
    return TurnProModelPolicy(
        model_id="pre-alpha-turn-pro.v1",
        annual_base_by_age=(0.05, 0.20, 0.40, 0.55, 0.65, 0.75, 0.85, 0.95),
        readiness_weight=2.0,
        readiness_reference=0.3,
        home_opportunity_multiplier=1.5,
        provenance=(
            "Provisional pre-alpha calibration; research 'Přechod mezi profesionály "
            "ve sportu' (2026-11-11): median about 17.5-19, almost all by 22"
        ),
    )


class TurnProCandidate(FrozenInput):
    """One eligible prospect's inputs, known through the end of the completed week."""

    player_id: str = Field(min_length=1)
    age: int = Field(ge=FIRST_TURN_PRO_AGE, le=120)
    # v1: share of current Tour Players this prospect is stronger than.
    # v2: the prospect's own perceived readiness (``observation.readiness``).
    readiness: float = Field(ge=0, le=1)
    home_opportunity: bool = False
    observation: TurnProObservation | None = Field(
        default=None, exclude_if=lambda v: v is None
    )

    @model_validator(mode="after")
    def observation_matches(self):
        if self.observation is not None and (
            self.observation.player_id != self.player_id
            or self.observation.readiness != self.readiness
        ):
            raise ValueError("Turn Pro candidate differs from its observation")
        return self


def weekly_turn_pro_chance(
    policy: TurnProModelPolicy, candidate: TurnProCandidate, *, weeks_per_year: int
) -> float:
    if weeks_per_year < 1:
        raise ValueError("Run weeks per year must be positive")
    bases = policy.annual_base_by_age
    base = bases[min(candidate.age - FIRST_TURN_PRO_AGE, len(bases) - 1)]
    annual_hazard = -math.log1p(-base)
    annual_hazard *= math.exp(
        policy.readiness_weight * (candidate.readiness - policy.readiness_reference)
    )
    if candidate.home_opportunity:
        annual_hazard *= policy.home_opportunity_multiplier
    if policy.uses_self_perception:
        observation = candidate.observation
        if observation is None or observation.policy_fingerprint != policy.perception.fingerprint:
            raise ValueError("Self-perception model requires the matching observation")
        # Own personality is self-known; unknown traits stay neutral.
        if observation.ambition is not None:
            annual_hazard *= math.exp(policy.ambition_weight * (observation.ambition - 0.5))
        if observation.professionalism is not None:
            annual_hazard *= math.exp(
                policy.professionalism_weight * (observation.professionalism - 0.5)
            )
    elif candidate.observation is not None:
        raise ValueError("A true-strength v1 model cannot consume an observation")
    return -math.expm1(-annual_hazard / weeks_per_year)


def turn_pro_draw(
    *, seed: int, run_id: str, branch_id: str, player_id: str, target: RunWeekPosition
) -> float:
    """Uniform [0, 1) draw keyed to one player and week, independent of order."""
    digest = canonical_hash(
        {
            "kind": "turn_pro_model.v1",
            "seed": seed,
            "run": run_id,
            "branch": branch_id,
            "player": player_id,
            "week": target.ordinal,
        }
    )
    return int(digest[:13], 16) / 16**13


def decide_turn_pro(
    *,
    predecessor,
    target: RunWeekPosition,
    candidates: Iterable[TurnProCandidate],
    policy: TurnProModelPolicy,
    seed: int,
) -> tuple[PlayerTurnProDecision, ...]:
    """Decide, at the Week Transition into ``target``, who turns pro that week.

    ``predecessor`` is the lifecycle of the completed week; every candidate must be an
    active player in it who has not turned pro. The result can be passed unchanged to
    ``advance_calendar_lifecycle(..., turn_pro=...)``.
    """
    if not predecessor.policy.requires_turn_pro:
        raise ValueError("Turn Pro model requires the v87 lifecycle policy")
    if target.ordinal != predecessor.week.ordinal + 1:
        raise ValueError("Turn Pro is decided only at the consecutive Week Transition")
    by_id = {p.player_id: p for p in predecessor.players}
    ordered = tuple(sorted(candidates, key=lambda c: c.player_id))
    if len({c.player_id for c in ordered}) != len(ordered):
        raise ValueError("Duplicate Turn Pro candidate")
    for candidate in ordered:
        player = by_id.get(candidate.player_id)
        if player is None:
            raise ValueError("Turn Pro candidate is absent from lifecycle")
        if player.status != "active" or getattr(player, "tour_entry_week", None):
            raise ValueError("Turn Pro candidate must be an active prospect")
        if candidate.age < player.age:
            raise ValueError("Turn Pro candidate age predates its lifecycle age")
    source = canonical_hash(
        {
            "kind": "turn_pro_model.v1",
            "lifecycle": predecessor.fingerprint,
            "target": target.ordinal,
            "seed": seed,
            "policy": policy.fingerprint,
            "candidates": [c.model_dump(mode="json") for c in ordered],
        }
    )
    decisions = []
    for candidate in ordered:
        chance = weekly_turn_pro_chance(
            policy, candidate, weeks_per_year=target.calendar.weeks_per_year
        )
        draw = turn_pro_draw(
            seed=seed,
            run_id=predecessor.run_id,
            branch_id=predecessor.branch_id,
            player_id=candidate.player_id,
            target=target,
        )
        if draw < chance:
            decisions.append(
                PlayerTurnProDecision(
                    run_id=predecessor.run_id,
                    branch_id=predecessor.branch_id,
                    player_id=candidate.player_id,
                    effective_week=target,
                    decision_source="player_ai",
                    source_state_fingerprint=source,
                    provenance=_decision_provenance(policy, chance, draw),
                    evidence=(
                        TurnProDecisionEvidence(
                            age=candidate.age,
                            home_opportunity=candidate.home_opportunity,
                            observation=candidate.observation,
                        )
                        if policy.decision_evidence is not None
                        else None
                    ),
                )
            )
    return tuple(decisions)


def _decision_provenance(policy: TurnProModelPolicy, chance: float, draw: float) -> str:
    return (
        f"{policy.schema_version}:{policy.model_id}; "
        f"weekly_chance={chance:.12f}; draw={draw:.12f}"
    )


def _require_consistent_observation(observation, perception) -> None:
    """The stored observation must agree with itself and the recorded policy.

    Overall level is the mean of the 57 perceived attributes, group values their
    group means and readiness the policy's logistic of the overall level. Without
    this a stored readiness could be edited whenever it does not move the chance.
    """
    from beta_engine.domain.players.attribute_catalog import (
        ATTRIBUTE_TO_GROUP,
        CANONICAL_PLAYER_ATTRIBUTES,
    )

    names = tuple(name for name, _ in observation.perceived_attributes)
    if names != CANONICAL_PLAYER_ATTRIBUTES:
        raise ValueError("Turn Pro observation is internally inconsistent: attributes")
    values = dict(observation.perceived_attributes)
    overall = sum(values.values()) / len(values)
    if abs(overall - observation.perceived_overall) > 1e-5:
        raise ValueError("Turn Pro observation is internally inconsistent: overall level")
    for group, value in observation.perceived_groups:
        members = [values[a] for a in CANONICAL_PLAYER_ATTRIBUTES if ATTRIBUTE_TO_GROUP[a] == group]
        if not members or abs(sum(members) / len(members) - value) > 1e-5:
            raise ValueError("Turn Pro observation is internally inconsistent: group level")
    readiness = 1.0 / (
        1.0 + math.exp(-(observation.perceived_overall - perception.professional_threshold)
                       / perception.readiness_scale)
    )
    if abs(readiness - observation.readiness) > 1e-6:
        raise ValueError("Turn Pro observation is internally inconsistent: readiness")


def verify_turn_pro_decision_evidence(
    decision: PlayerTurnProDecision, *, policy: TurnProModelPolicy, seed: int
) -> None:
    """Mathematical replay of one positive decision from its own recorded evidence.

    Recomputes the weekly chance from the recorded model, the prospect's observation
    and age, then the keyed draw for (seed, Run, Branch, player, week). It proves the
    stored decision is consistent with the model and what the prospect knew; it does
    NOT prove the observation matches the player's true attributes (that needs the
    completed week's sporting record, available only on the native replay path) nor
    that no other prospect was omitted (the candidate set is not stored).
    """
    evidence = decision.evidence
    if policy.decision_evidence is None:
        if evidence is not None:
            raise ValueError("Turn Pro evidence is not allowed by its recorded model")
        raise ValueError("Turn Pro model recorded no decision evidence to replay")
    if evidence is None:
        raise ValueError("Turn Pro decision lacks its recorded evidence")
    observation = evidence.observation
    if observation.policy_fingerprint != policy.perception.fingerprint:
        raise ValueError("Turn Pro observation was made under a different perception policy")
    _require_consistent_observation(observation, policy.perception)
    candidate = TurnProCandidate(
        player_id=decision.player_id,
        age=evidence.age,
        readiness=observation.readiness,
        home_opportunity=evidence.home_opportunity,
        observation=observation,
    )
    chance = weekly_turn_pro_chance(
        policy, candidate, weeks_per_year=decision.effective_week.calendar.weeks_per_year
    )
    draw = turn_pro_draw(
        seed=seed,
        run_id=decision.run_id,
        branch_id=decision.branch_id,
        player_id=decision.player_id,
        target=decision.effective_week,
    )
    if not draw < chance:
        raise ValueError("Turn Pro draw does not fall below the recomputed weekly chance")
    if decision.provenance != _decision_provenance(policy, chance, draw):
        raise ValueError("Turn Pro provenance differs from the recomputed chance and draw")


def readiness_against(prospect_strength: float, reference_strengths: Iterable[float]) -> float:
    """Share of the reference group the prospect is strictly stronger than."""
    reference = tuple(reference_strengths)
    if not reference:
        raise ValueError("Readiness requires a non-empty reference group")
    return sum(value < prospect_strength for value in reference) / len(reference)


def build_turn_pro_candidates(
    predecessor,
    target_lifecycle,
    strength_by_player: dict[str, float],
    *,
    home_opportunity_by_player: dict[str, bool] | None = None,
) -> tuple[TurnProCandidate, ...]:
    """Candidates and inputs from information known through the completed week.

    ``predecessor`` is the completed week's lifecycle; ``target_lifecycle`` is the
    same history advanced to the target week *without* new decisions, used only for
    ages and retirement at the target. Strength comes from the completed week's
    sporting state. Readiness compares a prospect with current active Tour Players;
    while a Run has none yet it falls back to the whole active population.
    """
    target_by_id = {p.player_id: p for p in target_lifecycle.players}
    prospects = []
    tour = []
    population = []
    for player in sorted(predecessor.players, key=lambda p: p.player_id):
        if player.status != "active":
            continue
        strength = strength_by_player.get(player.player_id)
        if strength is None:
            raise ValueError("Turn Pro readiness requires every active player's strength")
        population.append((player.player_id, strength))
        if getattr(player, "tour_entry_week", None) is not None:
            tour.append(strength)
            continue
        future = target_by_id.get(player.player_id)
        if future is None or future.status != "active":
            continue
        prospects.append((player.player_id, future.age, strength))
    home = home_opportunity_by_player or {}

    def reference_for(pid):
        if tour:
            return tour
        # Fallback: everyone else in the active population, never the player itself.
        return [v for other, v in population if other != pid]

    return tuple(
        TurnProCandidate(
            player_id=pid,
            age=age,
            readiness=(
                readiness_against(strength, reference_for(pid))
                if tour or len(population) > 1
                else 0.0
            ),
            home_opportunity=bool(home.get(pid, False)),
        )
        for pid, age, strength in prospects
    )


class InitialTurnProPlayer(FrozenInput):
    """One opening-population player's inputs for the retrospective Run-start check."""

    player_id: str = Field(min_length=1)
    # Completed Run weeks since birth at opening Week 1 (the stored calendar age).
    age_weeks: int = Field(ge=0)
    strength: float
    observation: TurnProObservation | None = Field(default=None, exclude_if=lambda v: v is None)


class InitialTurnProEvidence(FrozenInput):
    """Master v87 professionals already present at opening Week 1, with its inputs.

    The opening population has a simulated history before Run start, so the same
    pre-alpha model is integrated retrospectively from age 15 to opening Week 1:
    with a constant readiness, ``W`` weekly chances compound to exactly
    ``1 - exp(-cumulative annual hazard)``. Readiness is relative to the rest of the
    opening population (there are no earlier Tour Players), and home opportunities
    are not modelled before the Run. The evidence is recomputable and verified.
    """

    schema_version: Literal["initial_turn_pro.v1", "initial_turn_pro.v2"] = "initial_turn_pro.v1"
    model: TurnProModelPolicy
    seed: int
    professional_player_ids: tuple[str, ...]
    sporting_bootstrap_policy: dict | None = Field(default=None, exclude_if=lambda v: v is None)

    @model_validator(mode="after")
    def canonical_ids(self):
        if self.schema_version == "initial_turn_pro.v2":
            if not self.model.uses_self_perception or self.sporting_bootstrap_policy is None:
                raise ValueError("Opening Turn Pro v2 needs its self-perception and recorded bootstrap policy")
        elif self.model.uses_self_perception or self.sporting_bootstrap_policy is not None:
            raise ValueError("Historical opening v1 retains its true-strength model and bytes")
        ids = self.professional_player_ids
        if list(ids) != sorted(set(ids)):
            raise ValueError("Initial professionals require canonical distinct ids")
        return self


def initial_turn_pro_chance(
    policy: TurnProModelPolicy, *, age_weeks: int, readiness: float, weeks_per_year: int,
    observation: TurnProObservation | None = None,
) -> float:
    """Probability of having turned pro between age 15 and opening Week 1."""
    if weeks_per_year < 1:
        raise ValueError("Run weeks per year must be positive")
    bases = policy.annual_base_by_age
    scale = math.exp(policy.readiness_weight * (readiness - policy.readiness_reference))
    if policy.uses_self_perception:
        if observation is None or observation.policy_fingerprint != policy.perception.fingerprint:
            raise ValueError("Opening self-perception requires the matching own observation")
        if readiness != observation.readiness:
            raise ValueError("Opening readiness differs from the player's own observation")
        if observation.ambition is not None:
            scale *= math.exp(policy.ambition_weight * (observation.ambition - 0.5))
        if observation.professionalism is not None:
            scale *= math.exp(policy.professionalism_weight * (observation.professionalism - 0.5))
    exposed = age_weeks - FIRST_TURN_PRO_AGE * weeks_per_year
    hazard = 0.0
    year = 0
    while exposed > 0:
        weeks = min(exposed, weeks_per_year)
        base = bases[min(year, len(bases) - 1)]
        hazard += -math.log1p(-base) * scale * weeks / weeks_per_year
        exposed -= weeks
        year += 1
    return -math.expm1(-hazard)


def initial_turn_pro_draw(*, seed: int, run_id: str, player_id: str) -> float:
    """Opening draw keyed by Run, not Branch: pre-Run history is shared by every fork."""
    digest = canonical_hash(
        {"kind": "initial_turn_pro.v1", "seed": seed, "run": run_id, "player": player_id}
    )
    return int(digest[:13], 16) / 16**13


def initial_professional_ids(
    *,
    run_id: str,
    players: Iterable[InitialTurnProPlayer],
    policy: TurnProModelPolicy,
    seed: int,
    weeks_per_year: int,
) -> tuple[str, ...]:
    ordered = tuple(sorted(players, key=lambda p: p.player_id))
    if len({p.player_id for p in ordered}) != len(ordered):
        raise ValueError("Duplicate initial Turn Pro player")
    strengths = sorted(p.strength for p in ordered)
    chosen = []
    for player in ordered:
        if policy.uses_self_perception:
            observation = player.observation
            if observation is None or observation.player_id != player.player_id:
                raise ValueError("Opening Turn Pro needs the player's own observation")
            readiness = observation.readiness
        else:
            # Historical v1 reconstruction only: preserve its exact computation.
            observation = None
            weaker = bisect.bisect_left(strengths, player.strength)
            readiness = weaker / (len(ordered) - 1) if len(ordered) > 1 else 0.0
        chance = initial_turn_pro_chance(
            policy,
            age_weeks=player.age_weeks,
            readiness=readiness,
            weeks_per_year=weeks_per_year,
            observation=observation,
        )
        draw = initial_turn_pro_draw(seed=seed, run_id=run_id, player_id=player.player_id)
        if draw < chance:
            chosen.append(player.player_id)
    return tuple(chosen)


def build_observed_turn_pro_candidates(
    predecessor,
    target_lifecycle,
    sporting_by_player,
    *,
    policy: TurnProModelPolicy,
    seed: int,
    target: RunWeekPosition,
    traits_by_player=None,
    home_opportunity_by_player: dict[str, bool] | None = None,
) -> tuple[TurnProCandidate, ...]:
    """Model v2 candidates from each prospect's own self-perception only.

    ``sporting_by_player`` holds the completed week's sporting records (own true
    attributes, which the prospect perceives imperfectly). Other players'
    strength is never read. ``traits_by_player`` holds own personality traits
    (``ambition``, ``professionalism``); a missing entry stays unknown/neutral.
    """
    if not policy.uses_self_perception:
        raise ValueError("Observed candidates require the self-perception model")
    target_by_id = {p.player_id: p for p in target_lifecycle.players}
    traits = traits_by_player or {}
    home = home_opportunity_by_player or {}
    candidates = []
    for player in sorted(predecessor.players, key=lambda p: p.player_id):
        if player.status != "active" or getattr(player, "tour_entry_week", None) is not None:
            continue
        future = target_by_id.get(player.player_id)
        if future is None or future.status != "active":
            continue
        record = sporting_by_player.get(player.player_id)
        if record is None:
            raise ValueError("Turn Pro self-perception requires the prospect's own record")
        trait = traits.get(player.player_id)
        observation = perceive_self(
            policy=policy.perception,
            run_id=predecessor.run_id,
            player_id=player.player_id,
            attributes=record.attributes,
            seed=seed,
            week_ordinal=target.ordinal,
            ambition=None if trait is None else trait.ambition,
            professionalism=None if trait is None else trait.professionalism,
        )
        candidates.append(
            TurnProCandidate(
                player_id=player.player_id,
                age=future.age,
                readiness=observation.readiness,
                home_opportunity=bool(home.get(player.player_id, False)),
                observation=observation,
            )
        )
    return tuple(candidates)


def turn_pro_candidates_for(
    policy: TurnProModelPolicy,
    predecessor,
    target_lifecycle,
    sporting_records,
    *,
    seed: int,
    target: RunWeekPosition,
    traits_by_player=None,
    home_opportunity_by_player: dict[str, bool] | None = None,
) -> tuple[TurnProCandidate, ...]:
    """Candidates for the model version actually recorded/used.

    v2 (current default) reads only each prospect's own self-perception and
    personality. v1 (true relative strength) exists only to replay history that
    was already recorded with it; it is never the default any more.
    """
    records = {p.player_id: p for p in sporting_records}
    if policy.uses_self_perception:
        return build_observed_turn_pro_candidates(
            predecessor,
            target_lifecycle,
            records,
            policy=policy,
            seed=seed,
            target=target,
            traits_by_player=traits_by_player,
            home_opportunity_by_player=home_opportunity_by_player,
        )
    return build_turn_pro_candidates(
        predecessor,
        target_lifecycle,
        {pid: record.ovr for pid, record in records.items()},
        home_opportunity_by_player=home_opportunity_by_player,
    )


def traits_from_world(world) -> dict:
    """Own personality traits of InitialWorld players (prospects born later: unknown)."""
    return {
        p.player_id: p.hidden_career_traits
        for p in getattr(world, "players", ())
        if getattr(p, "hidden_career_traits", None) is not None
    }
