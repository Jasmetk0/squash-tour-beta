"""Global isolated Player Test Lab over the canonical weekly development kernels."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Literal

from pydantic import Field, field_validator, model_validator

from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.matches.health import (
    PlayerMatchHealthProjection,
    project_player_health,
)
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.health import (
    PlayerHealthProfile,
    PlayerHealthRecord,
)
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    CompetitiveMatchCount,
    PlayerDevelopmentPolicy,
    PlayerSportingRecord,
    PlayerSportingWeekState,
    between_week_state_update,
    weekly_player_development_update,
)
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek


PLAYER_LAB_SCHEMA_VERSION = "player_test_lab_scenario.v1"
PLAYER_LAB_RESULT_VERSION = "player_test_lab_result.v1"
MAX_PLAYER_LAB_WEEKS = 61


def _fingerprint(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def _next_week(value: RankingWeek) -> RankingWeek:
    ordinal = value.ordinal + 1
    if ordinal >= 50 * 61:
        raise ValueError("Player Lab scenario exceeds the 2049/50 Week 61 Run horizon")
    return RankingWeek(season_index=ordinal // 61, week=(ordinal % 61) + 1)


def _age_at_week(*, birth_year: int, birth_year_week: int, week: RankingWeek) -> int:
    position = season_week_to_calendar_position(2000 + week.season_index, week.week)
    return age_at_calendar_position(
        birth_year=birth_year,
        birth_year_week=birth_year_week,
        calendar_year=position.calendar_year,
        year_week=position.year_week,
    )


class PlayerLabVariant(FrozenInput):
    """One explicit workload history over the same initial player state.

    V1 varies only facts already consumed by the canonical weekly sporting kernel:
    the number of completed competitive matches in each week. It deliberately does
    not invent Training Load or Health inputs that the production kernel does not
    yet own.
    """

    variant_id: str = Field(min_length=1, max_length=160)
    display_name: str = Field(min_length=1, max_length=160)
    competitive_match_counts: tuple[int, ...] = Field(min_length=1)
    health_timeline: tuple[PlayerHealthProfile, ...] | None = None

    @field_validator("competitive_match_counts", mode="before")
    @classmethod
    def normalize_json_counts(cls, value):
        if isinstance(value, list):
            return tuple(value)
        return value

    @field_validator("health_timeline", mode="before")
    @classmethod
    def normalize_json_health_timeline(cls, value):
        if value is None:
            return None
        if isinstance(value, list):
            return tuple(
                item
                if isinstance(item, PlayerHealthProfile)
                else PlayerHealthProfile.model_validate_json(
                    json.dumps(item, ensure_ascii=False)
                )
                for item in value
            )
        return value

    @model_validator(mode="after")
    def validate_counts(self):
        if any(type(value) is not int or value < 0 or value > 32 for value in self.competitive_match_counts):
            raise ValueError(
                "Player Lab weekly competitive match counts must be integers from 0 through 32"
            )
        if self.health_timeline is not None and len(self.health_timeline) != len(
            self.competitive_match_counts
        ) + 1:
            raise ValueError(
                "Player Lab Health timeline must contain start state plus one state per simulated week"
            )
        return self


class PlayerLabScenario(FrozenInput):
    schema_version: Literal["player_test_lab_scenario.v1"] = PLAYER_LAB_SCHEMA_VERSION
    scenario_id: str = Field(min_length=1, max_length=160)
    player: PlayerSportingRecord
    birth_year: int = Field(ge=1900, le=2049)
    birth_year_week: int = Field(ge=1, le=61)
    start_week: RankingWeek
    development_policy: PlayerDevelopmentPolicy = PlayerDevelopmentPolicy()
    variants: tuple[PlayerLabVariant, ...] = Field(min_length=1)
    source_kind: Literal["portable", "built_in_copy"] = "portable"
    source_reference: str | None = Field(default=None, max_length=500)
    source_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("player", mode="before")
    @classmethod
    def normalize_json_player(cls, value):
        if isinstance(value, dict):
            return PlayerSportingRecord.model_validate_json(
                json.dumps(value, ensure_ascii=False)
            )
        return value

    @field_validator("variants", mode="before")
    @classmethod
    def normalize_json_variants(cls, value):
        if isinstance(value, list):
            return tuple(value)
        return value

    @model_validator(mode="after")
    def validate_scenario(self):
        variant_ids = tuple(item.variant_id for item in self.variants)
        if variant_ids != tuple(sorted(set(variant_ids))):
            raise ValueError(
                "Player Lab variants must use canonical unique variant_id order"
            )
        lengths = {len(item.competitive_match_counts) for item in self.variants}
        if len(lengths) != 1:
            raise ValueError("Player Lab variants must cover the same number of weeks")
        duration = next(iter(lengths))
        if duration > MAX_PLAYER_LAB_WEEKS:
            raise ValueError(
                f"Player Lab scenarios support at most {MAX_PLAYER_LAB_WEEKS} weeks"
            )
        if self.start_week.ordinal + duration >= 50 * 61:
            raise ValueError("Player Lab scenario extends beyond the Run time horizon")
        for variant in self.variants:
            if variant.health_timeline is not None and any(
                profile.player_id != self.player.player_id
                for profile in variant.health_timeline
            ):
                raise ValueError(
                    "Player Lab Health timeline identity must match the scenario player"
                )
        age = _age_at_week(
            birth_year=self.birth_year,
            birth_year_week=self.birth_year_week,
            week=self.start_week,
        )
        if age < 0:
            raise ValueError("Player Lab player must already be born at start_week")
        return self

    @property
    def duration_weeks(self) -> int:
        return len(self.variants[0].competitive_match_counts)

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class BuiltInPlayerLabScenario(FrozenInput):
    scenario_id: str
    display_name: str
    description: str
    read_only: Literal[True] = True
    scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario: PlayerLabScenario


class PlayerLabCompatibility(FrozenInput):
    production_kernels: tuple[str, ...]
    portable: Literal[True] = True
    isolated: Literal[True] = True
    run_mutation_performed: Literal[False] = False
    run_live_link: Literal[False] = False
    health_supported: Literal[True] = True
    training_load_supported: Literal[False] = False
    career_ai_supported: Literal[False] = False
    warnings: tuple[str, ...]


class PlayerLabWeekSnapshot(FrozenInput):
    week: RankingWeek
    age: int = Field(ge=0)
    completed_competitive_matches: int = Field(ge=0)
    ovr: int = Field(ge=0, le=200)
    potential_ovr: int = Field(ge=0, le=200)
    current_form: int = Field(ge=0, le=200)
    match_sharpness: int = Field(ge=0, le=100)
    long_term_fatigue: int = Field(ge=0, le=100)
    changed_attribute_count: int = Field(ge=0, le=57)
    attribute_delta_total: int
    health_projection: PlayerMatchHealthProjection
    health_projection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class PlayerLabVariantResult(FrozenInput):
    variant_id: str
    display_name: str
    initial_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    initial_health_projection: PlayerMatchHealthProjection
    initial_health_projection_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    final_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshots: tuple[PlayerLabWeekSnapshot, ...]
    final_player: PlayerSportingRecord


class PlayerLabDiagnostics(FrozenInput):
    variant_count: int = Field(ge=1)
    duration_weeks: int = Field(ge=1, le=MAX_PLAYER_LAB_WEEKS)
    distinct_final_state_count: int = Field(ge=1)
    min_final_ovr: int = Field(ge=0, le=200)
    max_final_ovr: int = Field(ge=0, le=200)
    min_final_sharpness: int = Field(ge=0, le=100)
    max_final_sharpness: int = Field(ge=0, le=100)


class PlayerLabRequest(FrozenInput):
    scenario: PlayerLabScenario

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class PlayerLabResult(FrozenInput):
    schema_version: Literal["player_test_lab_result.v1"] = PLAYER_LAB_RESULT_VERSION
    scenario_id: str
    scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    compatibility: PlayerLabCompatibility
    variants: tuple[PlayerLabVariantResult, ...]
    diagnostics: PlayerLabDiagnostics


def _record(player_id: str = "LAB-PLAYER", value: int = 100) -> PlayerSportingRecord:
    return PlayerSportingRecord(
        player_id=player_id,
        attributes=tuple((name, value) for name in CANONICAL_PLAYER_ATTRIBUTES),
        potential_ovr=160,
        potential_identity=f"player-lab-potential:{player_id}",
        potential_provenance="Player Lab built-in diagnostic input",
        development_timing="Standard",
        current_form=100,
        long_term_form_norm=100,
        match_sharpness=80,
        long_term_fatigue=20,
    )


def _built_in_scenarios() -> tuple[BuiltInPlayerLabScenario, ...]:
    scenario = PlayerLabScenario(
        scenario_id="development-activity-baseline",
        player=_record(),
        birth_year=1980,
        birth_year_week=1,
        start_week=RankingWeek(season_index=0, week=1),
        variants=(
            PlayerLabVariant(
                variant_id="active",
                display_name="One competitive match per week",
                competitive_match_counts=(1, 1, 1, 1, 1, 1, 1, 1),
            ),
            PlayerLabVariant(
                variant_id="idle",
                display_name="No competitive matches",
                competitive_match_counts=(0, 0, 0, 0, 0, 0, 0, 0),
            ),
        ),
    )
    health_player = _record(player_id="LAB-HEALTH")
    start = RankingWeek(season_index=0, week=1)
    active = PlayerHealthProfile(
        player_id=health_player.player_id,
        records=(
            PlayerHealthRecord(
                record_id="ankle-1",
                kind="Injury",
                condition_key="ankle",
                lifecycle="Active",
                severity=40,
                affected_domains=("movement",),
                onset_week=start,
                recovery_window_min_weeks=2,
                recovery_window_max_weeks=5,
                provenance="Player Lab explicit diagnostic path",
            ),
        ),
    )
    recovering = PlayerHealthProfile(
        player_id=health_player.player_id,
        records=(
            active.records[0].model_copy(
                update={"lifecycle": "Recovering", "severity": 20}
            ),
        ),
    )
    recovered = PlayerHealthProfile(
        player_id=health_player.player_id,
        records=(
            active.records[0].model_copy(
                update={
                    "lifecycle": "Recovered",
                    "severity": 0,
                    "recovered_week": RankingWeek(season_index=0, week=4),
                }
            ),
        ),
    )
    healthy = PlayerHealthProfile(player_id=health_player.player_id)
    health_scenario = PlayerLabScenario(
        scenario_id="health-projection-explicit-recovery",
        player=health_player,
        birth_year=1980,
        birth_year_week=1,
        start_week=start,
        variants=(
            PlayerLabVariant(
                variant_id="explicit-injury",
                display_name="Explicit ankle recovery path",
                competitive_match_counts=(0, 0, 0),
                health_timeline=(active, active, recovering, recovered),
            ),
            PlayerLabVariant(
                variant_id="healthy-control",
                display_name="Healthy control",
                competitive_match_counts=(0, 0, 0),
                health_timeline=(healthy, healthy, healthy, healthy),
            ),
        ),
    )
    return (
        BuiltInPlayerLabScenario(
            scenario_id=scenario.scenario_id,
            display_name="Development activity baseline",
            description=(
                "Compares the same canonical player over eight weeks with one competitive "
                "match per week versus no competitive matches. V1 varies only an input the "
                "production sporting kernel already consumes."
            ),
            scenario_fingerprint=scenario.fingerprint,
            scenario=scenario,
        ),
        BuiltInPlayerLabScenario(
            scenario_id=health_scenario.scenario_id,
            display_name="Health projection explicit recovery",
            description=(
                "Compares an explicit Active → Recovering → Recovered Injury timeline "
                "against a healthy control through the same Match Health projection. "
                "The Lab does not generate healing or apply an unapproved numeric penalty."
            ),
            scenario_fingerprint=health_scenario.fingerprint,
            scenario=health_scenario,
        ),
    )


BUILT_IN_PLAYER_LAB_SCENARIOS = _built_in_scenarios()


class PlayerTestLabService:
    """Run portable development scenarios without creating or mutating a Product Run."""

    def list_built_in_scenarios(self) -> tuple[BuiltInPlayerLabScenario, ...]:
        return BUILT_IN_PLAYER_LAB_SCENARIOS

    @staticmethod
    def _initial_state(scenario: PlayerLabScenario) -> PlayerSportingWeekState:
        source_fingerprint = _fingerprint(
            {
                "player": scenario.player.model_dump(mode="json"),
                "birth_year": scenario.birth_year,
                "birth_year_week": scenario.birth_year_week,
            }
        )
        return PlayerSportingWeekState(
            run_id="player-test-lab",
            branch_id="isolated",
            week=scenario.start_week,
            players=(scenario.player,),
            effective_development_policy=scenario.development_policy,
            completed_context_fingerprint=_fingerprint(
                {"kind": "player_test_lab_bootstrap.v1", "source": source_fingerprint}
            ),
            source_initial_world_fingerprint=source_fingerprint,
            stage_provenance="player_test_lab.v1:portable-bootstrap",
        )

    @staticmethod
    def _run_variant(
        scenario: PlayerLabScenario,
        variant: PlayerLabVariant,
        initial: PlayerSportingWeekState,
    ) -> PlayerLabVariantResult:
        state = initial
        snapshots: list[PlayerLabWeekSnapshot] = []
        initial_attributes = dict(scenario.player.attributes)
        health_timeline = variant.health_timeline or tuple(
            PlayerHealthProfile(player_id=scenario.player.player_id)
            for _ in range(len(variant.competitive_match_counts) + 1)
        )
        initial_health_projection = project_player_health(health_timeline[0])

        for week_index, match_count in enumerate(variant.competitive_match_counts):
            player_before = state.players[0]
            context = CompletedWeekSportingContext(
                run_id=state.run_id,
                branch_id=state.branch_id,
                completed_week=state.week,
                competitive_match_counts=(
                    CompetitiveMatchCount(
                        player_id=player_before.player_id,
                        count=match_count,
                    ),
                ),
                source_fingerprints=(
                    _fingerprint(
                        {
                            "kind": "player_test_lab_completed_week.v1",
                            "state_fingerprint": state.fingerprint,
                            "match_count": match_count,
                        }
                    ),
                ),
                provenance="player_test_lab.v1:explicit-completed-week-input",
            )
            target = _next_week(state.week)
            age = _age_at_week(
                birth_year=scenario.birth_year,
                birth_year_week=scenario.birth_year_week,
                week=state.week,
            )
            developed = weekly_player_development_update(
                state,
                target=target,
                player_ages={player_before.player_id: age},
                context=context,
            )
            state = between_week_state_update(
                developed,
                context=context,
                target_effective_development_policy=scenario.development_policy,
            )
            player_after = state.players[0]
            current_attributes = dict(player_after.attributes)
            health_projection = project_player_health(
                health_timeline[week_index + 1]
            )
            snapshots.append(
                PlayerLabWeekSnapshot(
                    week=state.week,
                    age=_age_at_week(
                        birth_year=scenario.birth_year,
                        birth_year_week=scenario.birth_year_week,
                        week=state.week,
                    ),
                    completed_competitive_matches=match_count,
                    ovr=player_after.ovr,
                    potential_ovr=player_after.potential_ovr,
                    current_form=player_after.current_form,
                    match_sharpness=player_after.match_sharpness,
                    long_term_fatigue=player_after.long_term_fatigue,
                    changed_attribute_count=sum(
                        current_attributes[name] != initial_attributes[name]
                        for name in CANONICAL_PLAYER_ATTRIBUTES
                    ),
                    attribute_delta_total=sum(
                        current_attributes[name] - initial_attributes[name]
                        for name in CANONICAL_PLAYER_ATTRIBUTES
                    ),
                    health_projection=health_projection,
                    health_projection_fingerprint=health_projection.fingerprint,
                    state_fingerprint=state.fingerprint,
                )
            )

        return PlayerLabVariantResult(
            variant_id=variant.variant_id,
            display_name=variant.display_name,
            initial_state_fingerprint=initial.fingerprint,
            initial_health_projection=initial_health_projection,
            initial_health_projection_fingerprint=initial_health_projection.fingerprint,
            final_state_fingerprint=state.fingerprint,
            snapshots=tuple(snapshots),
            final_player=state.players[0],
        )

    def run(self, request: PlayerLabRequest) -> PlayerLabResult:
        scenario = request.scenario
        initial = self._initial_state(scenario)
        variants = tuple(
            self._run_variant(scenario, variant, initial)
            for variant in scenario.variants
        )
        final_ovrs = [item.final_player.ovr for item in variants]
        final_sharpness = [item.final_player.match_sharpness for item in variants]
        return PlayerLabResult(
            scenario_id=scenario.scenario_id,
            scenario_fingerprint=scenario.fingerprint,
            request_fingerprint=request.fingerprint,
            compatibility=PlayerLabCompatibility(
                production_kernels=(
                    "weekly_player_development_update",
                    "between_week_state_update",
                ),
                warnings=(
                    "Health timelines use canonical PlayerHealthProfile and the shared Match Health limitation projection.",
                    "Health recovery generation and numeric sporting effects remain uncalibrated; explicit Health timelines do not alter the development kernel yet.",
                    "Training Load, Match Preparation, Experience, Financial Level and career AI are not modeled by Player Lab V1.",
                ),
            ),
            variants=variants,
            diagnostics=PlayerLabDiagnostics(
                variant_count=len(variants),
                duration_weeks=scenario.duration_weeks,
                distinct_final_state_count=len(
                    {item.final_state_fingerprint for item in variants}
                ),
                min_final_ovr=min(final_ovrs),
                max_final_ovr=max(final_ovrs),
                min_final_sharpness=min(final_sharpness),
                max_final_sharpness=max(final_sharpness),
            ),
        )
