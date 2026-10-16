"""Read-only initial-player pool preview from Run-owned World Package state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, ValidationError

from beta_engine.application.run_package_service import RunPackageService
from beta_engine.application.world_package_run_adapter import WorldPackageRunAdapter
from beta_engine.domain.players.initial_pool import (
    InitialPlayerPoolGenerator, InitialPoolResult, InitialPoolGeneratedPlayer,
    InitialPoolNamingPolicy,
)
from beta_engine.domain.run_packages import canonical_hash


# These are source-model ability fields (1–99), NOT canonical 57 attributes
# or OVR on the 0–200 scale. Extend only with an authoritative profile model.
EditableInitialField = Literal[
    "current_ability", "potential_ability",
    "attributes.technique", "attributes.movement", "attributes.physical",
    "attributes.mental", "attributes.consistency", "attributes.clutch",
    "attributes.recovery",
]


class RunWorldPreviewFieldLock(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    player_id: str = Field(min_length=1, max_length=128)
    field: EditableInitialField
    value: int = Field(ge=1, le=99)


def _apply_preview_field_locks(
    result: InitialPoolResult,
    locks: list[RunWorldPreviewFieldLock],
    *,
    season: str,
    seed: int,
    generator: InitialPlayerPoolGenerator,
) -> InitialPoolResult:
    if not locks:
        return result
    by_id: dict[str, list[RunWorldPreviewFieldLock]] = {}
    for lock in locks:
        by_id.setdefault(lock.player_id, []).append(lock)
    available = {player.player_id for player in result.players}
    missing = sorted(set(by_id) - available)
    if missing:
        raise ValueError(
            "Conflicting field locks: player IDs missing after regeneration: "
            + ", ".join(missing[:8])
        )
    updated = []
    for player in result.players:
        selected = by_id.get(player.player_id)
        if not selected:
            updated.append(player)
            continue
        # Whole-player Keep already preserves the edited source provenance;
        # don't re-fingerprint its identical locked fields on each session pass.
        if player.manual_override and all(
            (getattr(player.attributes, lock.field.split(".", 1)[1])
             if lock.field.startswith("attributes.")
             else getattr(player, lock.field)) == lock.value
            for lock in selected
        ):
            updated.append(player)
            continue
        values = player.model_dump(mode="python")
        attrs = player.attributes.model_dump(mode="python")
        for lock in selected:
            if lock.field.startswith("attributes."):
                attrs[lock.field.split(".", 1)[1]] = lock.value
            else:
                values[lock.field] = lock.value
        values["attributes"] = attrs
        values["manual_override"] = True
        values["locked"] = False
        if values["current_ability"] > values["potential_ability"] + 4:
            raise ValueError(
                f"Conflicting field locks for {player.player_id}: "
                "current_ability must not exceed potential_ability by more than 4"
            )
        if values["potential_ability"] > player.hidden_career_traits.potential_ceiling:
            raise ValueError(
                f"Conflicting field locks for {player.player_id}: "
                f"potential_ability {values['potential_ability']} exceeds "
                f"the existing hidden potential_ceiling "
                f"{player.hidden_career_traits.potential_ceiling}"
            )
        # Stable per-player provenance changes when manually authored source
        # fields change, even if the sampled seed and internal player ID do not.
        values["generation_fingerprint"] = canonical_hash({
            "original_fingerprint": player.generation_fingerprint,
            "preview_field_locks": [
                {"field": lock.field, "value": lock.value} for lock in selected
            ],
        })
        try:
            updated.append(InitialPoolGeneratedPlayer.model_validate(values))
        except ValidationError as exc:
            raise ValueError(
                f"Conflicting field locks for {player.player_id}: {exc.errors()[0]['msg']}"
            ) from exc
    return result.model_copy(update={
        "players": updated,
        "summary": generator._summarize(updated),
        "metadata": result.metadata.model_copy(update={
            "generation_fingerprint": generator._fingerprint(
                updated, season=season, seed=seed,
            ),
        }),
    })


class RunWorldKeepStep(BaseModel):
    """One prior, reproducible Keep pass. No player data is trusted from client."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    seed: int
    keep_from_seed: int
    keep_from_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    keep_player_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_lineage_step(self) -> "RunWorldKeepStep":
        if self.seed == self.keep_from_seed:
            raise ValueError("Keep history step requires a changed seed")
        if self.keep_player_ids != sorted(set(self.keep_player_ids)):
            raise ValueError("Keep history requires sorted unique player IDs")
        if any(not value or len(value) > 128 for value in self.keep_player_ids):
            raise ValueError("Keep history contains invalid player IDs")
        return self


class RunWorldPreviewAutomaticField(BaseModel):
    """Value-free Automatic reset resolved only against authenticated sources."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    player_id: str = Field(min_length=1, max_length=128)
    field: EditableInitialField


class RunWorldVerifiedSessionStep(BaseModel):
    """One authenticated session operation, never a browser-supplied player."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    kind: Literal["edit", "keep"]
    source_preview_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed: int
    keep_player_ids: list[str] = Field(default_factory=list)
    field_locks: list[RunWorldPreviewFieldLock] = Field(default_factory=list, max_length=2000)
    automatic_fields: list[RunWorldPreviewAutomaticField] = Field(
        default_factory=list, max_length=2000,
    )

    @model_validator(mode="after")
    def validate_step(self) -> "RunWorldVerifiedSessionStep":
        if self.keep_player_ids != sorted(set(self.keep_player_ids)):
            raise ValueError("Session step Keep IDs must be sorted and unique")
        if any(not player_id or len(player_id) > 128 for player_id in self.keep_player_ids):
            raise ValueError("Session step contains invalid Keep player ID")
        if self.kind == "edit" and self.keep_player_ids:
            raise ValueError("Field edit cannot change Keep selection")
        identities = [(lock.player_id, lock.field) for lock in self.field_locks]
        if identities != sorted(set(identities)):
            raise ValueError("Session step field locks must be sorted and unique")
        automatic = [(item.player_id, item.field) for item in self.automatic_fields]
        if automatic != sorted(set(automatic)):
            raise ValueError("Session Automatic fields must be sorted and unique")
        if set(automatic) & set(identities):
            raise ValueError("Session Automatic cannot also lock the same field")
        if self.kind == "keep" and automatic:
            raise ValueError("Session Keep cannot perform implicit Automatic edits")
        return self


class RunWorldExactCountryQuota(BaseModel):
    """An exact whole-batch count in a saved World; unlike overlapping conditions,
    country identities are disjoint, so the automatic remainder is well-defined.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    country_code: str = Field(pattern=r"^[A-Z]{3}$")
    count: int = Field(ge=0, le=2000)


class RunWorldInitialPoolPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    world_package_id: str = Field(
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
    )
    season: str = Field(default="2000/2001", min_length=4, max_length=32)
    seed: int
    # Opt-in preserves old request fingerprints and archived proposal replay.
    naming_policy: InitialPoolNamingPolicy | None = None
    target_pool_size: int = Field(default=128, ge=1, le=2000)
    country_code: str | None = Field(default=None, min_length=3, max_length=3)
    region: str | None = Field(default=None, min_length=1)  # Legacy OR predicate
    geographic_region: str | None = Field(default=None, min_length=1)
    travel_region: str | None = Field(default=None, min_length=1)
    min_age: int | None = Field(default=None, ge=15, le=45)
    max_age: int | None = Field(default=None, ge=15, le=45)
    # Explicit total only. Missing/empty retains the historical generation path.
    country_quotas: list[RunWorldExactCountryQuota] = Field(default_factory=list, max_length=250)
    # Session-only Keep. Each prior pass is reproducibly replayed from the
    # saved World, never from browser-supplied player values or permanent locks.
    keep_from_seed: int | None = None
    keep_from_preview_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    keep_player_ids: list[str] = Field(default_factory=list)
    keep_history: list[RunWorldKeepStep] = Field(default_factory=list, max_length=16)
    field_locks: list[RunWorldPreviewFieldLock] = Field(default_factory=list, max_length=2000)
    # Opt-in v2. The exact original legacy request and its fingerprint anchor
    # an append-only sequence of authenticated Keep/edit operations. The old
    # request and historical hash bytes remain completely unchanged.
    session_schema_version: Literal["run_world_generation_session.v2"] | None = None
    session_origin_request: RunWorldInitialPoolPreviewRequest | None = None
    session_origin_fingerprint: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    session_steps: list[RunWorldVerifiedSessionStep] = Field(default_factory=list, max_length=48)

    @model_validator(mode="after")
    def validate_age_range(self) -> "RunWorldInitialPoolPreviewRequest":
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("Age condition requires minimum age no higher than maximum age")
        keep = (self.keep_from_seed, self.keep_from_preview_fingerprint)
        if any(value is not None for value in keep) or self.keep_player_ids:
            if any(value is None for value in keep):
                raise ValueError("Session Keep requires both source seed and exact preview fingerprint")
            if self.seed == self.keep_from_seed:
                raise ValueError("Session Keep regeneration seed must differ from the source seed")
            if not 0 < len(self.keep_player_ids) < self.target_pool_size:
                raise ValueError("Session Keep must preserve a nonempty proper subset of the preview")
            if sorted(set(self.keep_player_ids)) != self.keep_player_ids:
                raise ValueError("Session Keep player IDs must be sorted, unique and nonempty")
            if any(not player_id or len(player_id) > 128 for player_id in self.keep_player_ids):
                raise ValueError("Session Keep player IDs are invalid")
        if self.keep_history:
            if self.keep_from_seed is None:
                raise ValueError("Keep history requires an active final Keep pass")
            previous_seed = self.keep_history[0].keep_from_seed
            for step in self.keep_history:
                if step.keep_from_seed != previous_seed:
                    raise ValueError("Keep history has broken seed ancestry")
                if len(step.keep_player_ids) >= self.target_pool_size:
                    raise ValueError("Keep history cannot preserve the entire batch")
                previous_seed = step.seed
            if previous_seed != self.keep_from_seed:
                raise ValueError("Keep history does not lead to the reviewed source seed")
        quotas = [quota.country_code for quota in self.country_quotas]
        if quotas != sorted(set(quotas)):
            raise ValueError("Exact country quotas must have sorted unique country codes")
        if sum(quota.count for quota in self.country_quotas) > self.target_pool_size:
            raise ValueError("Exact country quotas exceed total generated players")
        identities = [(lock.player_id, lock.field) for lock in self.field_locks]
        if identities != sorted(set(identities)):
            raise ValueError("Preview field locks must have unique, sorted player/field keys")
        enabled = self.session_schema_version is not None
        if enabled:
            if not self.session_origin_request or not self.session_origin_fingerprint or not self.session_steps:
                raise ValueError("Versioned session requires exact origin request, fingerprint and operations")
            if self.session_origin_request.session_schema_version is not None:
                raise ValueError("Nested session origins are forbidden")
            previous_keeps = (
                len(self.session_origin_request.keep_history) +
                int(self.session_origin_request.keep_from_seed is not None)
            )
            if previous_keeps + sum(step.kind == "keep" for step in self.session_steps) > 17:
                raise ValueError("Versioned session Keep limit exceeded")
        elif self.session_origin_request is not None or self.session_origin_fingerprint is not None or self.session_steps:
            raise ValueError("Session operations require the v2 schema version")
        return self

    def fingerprint_payload(self) -> dict:
        """Do not include absent new typed fields in existing Keep fingerprints.

        Preserve the original session Keep keys (including their defaults) as
        already stored by the current buuk production preview.
        """
        payload = self.model_dump(mode="json")
        if self.naming_policy is None:
            payload.pop("naming_policy", None)  # old request bytes unchanged
        if payload.get("geographic_region") is None:
            payload.pop("geographic_region", None)
        if payload.get("travel_region") is None:
            payload.pop("travel_region", None)
        if not payload.get("keep_history"):
            payload.pop("keep_history", None)  # original and one-pass digests unchanged
        if not payload.get("field_locks"):
            payload.pop("field_locks", None)  # existing hash/replay stays intact
        if not payload.get("country_quotas"):
            payload.pop("country_quotas", None)  # historical fingerprints preserved
        if self.session_origin_request is None:
            payload.pop("session_origin_request", None)
        else:
            payload["session_origin_request"] = self.session_origin_request.fingerprint_payload()
        if self.session_schema_version is None:
            payload.pop("session_schema_version", None)
        if self.session_origin_fingerprint is None:
            payload.pop("session_origin_fingerprint", None)
        if not self.session_steps:
            payload.pop("session_steps", None)
        else:
            # Old V2 fingerprints did not contain automatic_fields.
            for step in payload["session_steps"]:
                if not step.get("automatic_fields"):
                    step.pop("automatic_fields", None)
        return payload


class RunWorldInitialPoolPreview(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["run_world_initial_pool_preview.v1"] = (
        "run_world_initial_pool_preview.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    world_package_id: str = Field(min_length=1)
    run_package_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_country_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_generation_content_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    request: RunWorldInitialPoolPreviewRequest
    result: InitialPoolResult
    preview_only: Literal[True] = True

    @property
    def preview_fingerprint(self) -> str:
        payload = self.model_dump(mode="json")
        payload["request"] = self.request.fingerprint_payload()
        return canonical_hash(payload)


@dataclass(slots=True)
class RunWorldInitialPoolPreviewService:
    package_service: RunPackageService
    world_adapter: WorldPackageRunAdapter
    # Required dependency: no implicit unguarded fallback in new Run callers.
    calendar_guard: Callable[[str, str], None]

    def preview(
        self,
        *,
        run_id: str,
        branch_id: str,
        request: RunWorldInitialPoolPreviewRequest,
        _preserved_players: list[InitialPoolGeneratedPlayer] | None = None,
    ) -> RunWorldInitialPoolPreview:
        # All entrypoints (raw preview, Keep/edit sessions, adoption preflight
        # and new saved proposals) use this boundary. A hidden Home link alone
        # cannot stop a direct generator URL from showing misdated players.
        self.calendar_guard(run_id, branch_id)
        if request.session_schema_version is not None:
            if _preserved_players is not None:
                raise ValueError("Cannot inject Keep players into a versioned session")
            return self._preview_verified_session(
                run_id=run_id, branch_id=branch_id, request=request,
            )
        state = self.package_service.get(run_id=run_id, branch_id=branch_id)
        if state is None:
            raise ValueError("Run Package state is empty")

        countries = self.world_adapter.project_countries(
            state, package_id=request.world_package_id
        )
        generation = self.world_adapter.project_generation(
            state, package_id=request.world_package_id
        )

        # These are hard generation conditions, not distribution hints.
        # Diagnose contradictions against the Run-owned snapshot itself;
        # never fall back to another country, region, or global World.
        selected_countries = list(countries.countries)
        if request.country_code:
            code = request.country_code.upper()
            if not any(country.code == code for country in selected_countries):
                raise ValueError(
                    f"Country condition '{code}' is unavailable in saved World "
                    f"'{request.world_package_id}'"
                )
            selected_countries = [
                country for country in selected_countries if country.code == code
            ]
        if request.region:
            if not any(
                request.region in (country.region, country.effective_travel_region)
                for country in selected_countries
            ):
                if request.country_code:
                    raise ValueError(
                        f"Conflicting generation conditions: country "
                        f"'{request.country_code.upper()}' does not belong to "
                        f"region '{request.region}' in the saved World"
                    )
                raise ValueError(
                    f"Region condition '{request.region}' has no eligible "
                    "countries in the saved World"
                )

        # Geographic and Travel Region are distinct hard predicates. The old
        # `region` OR predicate remains for saved requests and replay.
        for requested, attribute, kind in (
            (request.geographic_region, "region", "Geographic Region"),
            (request.travel_region, "effective_travel_region", "Travel Region"),
        ):
            if requested:
                selected_countries = [
                    country for country in selected_countries
                    if getattr(country, attribute) == requested
                ]
                if not selected_countries:
                    raise ValueError(
                        f"Conflicting generation conditions: {kind} '{requested}' "
                        "has no eligible countries under saved-World conditions"
                    )

        generator = InitialPlayerPoolGenerator(identity_config=generation.identity_config)
        preserved = list(_preserved_players or [])
        if _preserved_players is not None and request.keep_from_seed is not None:
            raise ValueError("Internal preserved players must use a fresh generation step")
        if request.keep_from_seed is not None:
            # Rebuild the exact original preview against the current Run/Branch
            # World source, instead of trusting snapshots supplied by the browser.
            if request.keep_history:
                previous = request.keep_history[-1]
                original_request = request.model_copy(update={
                    "seed": previous.seed,
                    "keep_from_seed": previous.keep_from_seed,
                    "keep_from_preview_fingerprint": previous.keep_from_preview_fingerprint,
                    "keep_player_ids": list(previous.keep_player_ids),
                    "keep_history": request.keep_history[:-1],
                })
            else:
                original_request = request.model_copy(update={
                    "seed": request.keep_from_seed,
                    "keep_from_seed": None,
                    "keep_from_preview_fingerprint": None,
                    "keep_player_ids": [],
                    "keep_history": [],
                })
            original = self.preview(
                run_id=run_id, branch_id=branch_id, request=original_request,
            )
            if original.preview_fingerprint != request.keep_from_preview_fingerprint:
                raise ValueError("Session Keep source preview is stale or belongs to a different Run/World")
            source_players = {player.player_id: player for player in original.result.players}
            unknown_ids = set(request.keep_player_ids) - set(source_players)
            if unknown_ids:
                raise ValueError("Session Keep contains player IDs absent from the exact source preview")
            preserved = [
                source_players[player_id].model_copy(update={"locked": True})
                for player_id in request.keep_player_ids
            ]

        result = generator.generate(
            countries=(selected_countries if request.geographic_region or request.travel_region
                       else list(countries.countries)),
            season=request.season,
            seed=request.seed,
            target_pool_size=request.target_pool_size,
            country_code=request.country_code,
            region=request.region,
            min_age=request.min_age,
            max_age=request.max_age,
            existing_locked_players=preserved,
            country_quotas=(
                {quota.country_code: quota.count for quota in request.country_quotas}
                if request.country_quotas else None
            ),
            naming_policy=request.naming_policy,
            dry_run=True,
        )
        if preserved:
            # Repeatable Keep is only for the preview session. Never turn it
            # into a permanent player Lock in adopted/saved InitialWorld.
            unlocked_players = [
                player.model_copy(update={"locked": False})
                for player in result.players
            ]
            result = result.model_copy(update={
                "players": unlocked_players,
                "summary": generator._summarize(unlocked_players),
                "metadata": result.metadata.model_copy(update={
                    "generation_fingerprint": generator._fingerprint(
                        unlocked_players, season=request.season, seed=request.seed,
                    ),
                }),
            })

        result = _apply_preview_field_locks(
            result, request.field_locks, season=request.season, seed=request.seed,
            generator=generator,
        )

        return RunWorldInitialPoolPreview(
            run_id=run_id,
            branch_id=branch_id,
            world_package_id=request.world_package_id,
            run_package_state_fingerprint=state.fingerprint,
            world_country_content_fingerprint=countries.content_fingerprint,
            world_generation_content_fingerprint=generation.content_fingerprint,
            request=request,
            result=result,
        )


    @staticmethod
    def _bare_session_request(
        original: RunWorldInitialPoolPreviewRequest, *, seed: int,
    ) -> RunWorldInitialPoolPreviewRequest:
        """One fresh step with the same exact World and hard conditions."""
        return original.model_copy(update={
            "seed": seed,
            "keep_from_seed": None,
            "keep_from_preview_fingerprint": None,
            "keep_player_ids": [],
            "keep_history": [],
            "field_locks": [],
            "session_schema_version": None,
            "session_origin_request": None,
            "session_origin_fingerprint": None,
            "session_steps": [],
        })

    def _legacy_keep_source(
        self, request: RunWorldInitialPoolPreviewRequest,
    ) -> RunWorldInitialPoolPreviewRequest | None:
        """Reproduce the immediate v1 Keep ancestor without changing its hash."""
        if request.keep_from_seed is None:
            return None
        if request.keep_history:
            previous = request.keep_history[-1]
            return request.model_copy(update={
                "seed": previous.seed,
                "keep_from_seed": previous.keep_from_seed,
                "keep_from_preview_fingerprint": previous.keep_from_preview_fingerprint,
                "keep_player_ids": list(previous.keep_player_ids),
                "keep_history": request.keep_history[:-1],
            })
        return request.model_copy(update={
            "seed": request.keep_from_seed,
            "keep_from_seed": None,
            "keep_from_preview_fingerprint": None,
            "keep_player_ids": [],
            "keep_history": [],
        })

    def _session_stage_core(
        self, *, run_id: str, branch_id: str,
        original: RunWorldInitialPoolPreviewRequest, seed: int,
        preserved: list[InitialPoolGeneratedPlayer],
    ) -> InitialPoolResult:
        # Only server-reconstructed identities and objects enter this call.
        bare = self._bare_session_request(original, seed=seed)
        return self.preview(
            run_id=run_id, branch_id=branch_id, request=bare,
            _preserved_players=preserved,
        ).result

    @staticmethod
    def _source_fields(player: InitialPoolGeneratedPlayer) -> dict[str, int]:
        return {
            "current_ability": player.current_ability,
            "potential_ability": player.potential_ability,
            **{
                "attributes." + key: getattr(player.attributes, key)
                for key in (
                    "technique", "movement", "physical", "mental",
                    "consistency", "clutch", "recovery",
                )
            },
        }

    def _legacy_automatic_baselines(
        self, *, run_id: str, branch_id: str,
        original: RunWorldInitialPoolPreviewRequest,
    ) -> dict[str, dict[str, int]]:
        """Trace each sampled profile through old authenticated Keep history."""
        lineage = []
        cursor: RunWorldInitialPoolPreviewRequest | None = original
        while cursor is not None:
            lineage.append(cursor)
            cursor = self._legacy_keep_source(cursor)
        bases: dict[str, dict[str, int]] = {}
        previous: InitialPoolResult | None = None
        for stage in reversed(lineage):
            authentic = self.preview(
                run_id=run_id, branch_id=branch_id, request=stage,
            )
            prior = {} if previous is None else {
                p.player_id: p for p in previous.players
            }
            selected = set(stage.keep_player_ids)
            if selected - set(prior):
                raise ValueError("Automatic source Keep lineage has missing identities")
            preserved = [
                prior[pid].model_copy(update={"locked": True})
                for pid in stage.keep_player_ids
            ]
            core = self._session_stage_core(
                run_id=run_id, branch_id=branch_id, original=stage,
                seed=stage.seed, preserved=preserved,
            )
            bases = {
                player.player_id: (
                    bases[player.player_id] if player.player_id in selected
                    else self._source_fields(player)
                )
                for player in core.players
            }
            if {p.player_id for p in authentic.result.players} != set(bases):
                raise ValueError("Automatic source baseline does not match reviewed cohort")
            previous = authentic.result
        return bases

    @staticmethod
    def _apply_automatic_fields(
        result: InitialPoolResult,
        automatic: list[RunWorldPreviewAutomaticField],
        baselines: dict[str, dict[str, int]],
        *, generator: InitialPlayerPoolGenerator, season: str, seed: int,
    ) -> InitialPoolResult:
        if not automatic:
            return result
        grouped: dict[str, list[RunWorldPreviewAutomaticField]] = {}
        for item in automatic:
            grouped.setdefault(item.player_id, []).append(item)
        available = {p.player_id for p in result.players}
        if set(grouped) - available:
            raise ValueError("Session Automatic refers to an absent player identity")
        updated = []
        for player in result.players:
            resets = grouped.get(player.player_id)
            if not resets:
                updated.append(player)
                continue
            if player.player_id not in baselines:
                raise ValueError("Session Automatic has no authenticated source baseline")
            values = player.model_dump(mode="python")
            attrs = player.attributes.model_dump(mode="python")
            for item in resets:
                original = baselines[player.player_id][item.field]
                if item.field.startswith("attributes."):
                    attrs[item.field.split(".", 1)[1]] = original
                else:
                    values[item.field] = original
            values["attributes"] = attrs
            values["generation_fingerprint"] = canonical_hash({
                "source_fingerprint": player.generation_fingerprint,
                "session_automatic_fields": [
                    {"field": item.field} for item in resets
                ],
            })
            try:
                updated.append(InitialPoolGeneratedPlayer.model_validate(values))
            except ValidationError as exc:
                raise ValueError(
                    f"Conflicting Automatic fields for {player.player_id}: "
                    f"{exc.errors()[0]['msg']}"
                ) from exc
        return result.model_copy(update={
            "players": updated,
            "summary": generator._summarize(updated),
            "metadata": result.metadata.model_copy(update={
                "generation_fingerprint": generator._fingerprint(
                    updated, season=season, seed=seed,
                ),
            }),
        })

    def _preview_verified_session(
        self, *, run_id: str, branch_id: str,
        request: RunWorldInitialPoolPreviewRequest,
    ) -> RunWorldInitialPoolPreview:
        original = request.session_origin_request
        assert original is not None
        # No step can alter a condition, source, quota or previous legacy Keep
        # ancestry. All those settings are frozen at session creation.
        variable = {
            "seed", "field_locks", "session_schema_version",
            "session_origin_request", "session_origin_fingerprint", "session_steps",
        }
        immutable = lambda value: value.model_dump(mode="json", exclude=variable)
        if immutable(request) != immutable(original):
            raise ValueError("Session cannot silently alter World, conditions, quotas or Keep ancestry")
        source = self.preview(run_id=run_id, branch_id=branch_id, request=original)
        if source.preview_fingerprint != request.session_origin_fingerprint:
            raise ValueError("Versioned session origin is stale or unauthenticated")
        previous = source
        legacy_source = self._legacy_keep_source(original)
        first_preserved: list[InitialPoolGeneratedPlayer] = []
        if legacy_source is not None:
            legacy = self.preview(run_id=run_id, branch_id=branch_id, request=legacy_source)
            by_id = {player.player_id: player for player in legacy.result.players}
            first_preserved = [
                by_id[player_id].model_copy(update={"locked": True})
                for player_id in original.keep_player_ids
            ]
        core = self._session_stage_core(
            run_id=run_id, branch_id=branch_id, original=original,
            seed=original.seed, preserved=first_preserved,
        )
        generation = self.world_adapter.project_generation(
            self.package_service.get(run_id=run_id, branch_id=branch_id),
            package_id=request.world_package_id,
        )
        generator = InitialPlayerPoolGenerator(identity_config=generation.identity_config)
        baselines = (
            self._legacy_automatic_baselines(
                run_id=run_id, branch_id=branch_id, original=original,
            ) if any(step.automatic_fields for step in request.session_steps)
            else None
        )
        for index, step in enumerate(request.session_steps):
            if previous.preview_fingerprint != step.source_preview_fingerprint:
                raise ValueError("Versioned session operation has stale or forged source fingerprint")
            if step.kind == "edit":
                if step.seed != previous.request.seed:
                    raise ValueError("Session field edit cannot change seed")
            else:
                expected_locks = [
                    lock for lock in previous.request.field_locks
                    if lock.player_id in step.keep_player_ids
                ]
                if step.field_locks != expected_locks:
                    raise ValueError(
                        "Session Keep cannot silently alter existing field locks; "
                        "apply an authenticated field edit first"
                    )
                if step.seed == previous.request.seed:
                    raise ValueError("Session Keep requires a new seed")
                if not 0 < len(step.keep_player_ids) < request.target_pool_size:
                    raise ValueError("Session Keep requires a nonempty proper subset")
                by_id = {player.player_id: player for player in previous.result.players}
                if set(step.keep_player_ids) - set(by_id):
                    raise ValueError("Session Keep IDs are absent from authenticated source")
                preserved = [
                    by_id[player_id].model_copy(update={"locked": True})
                    for player_id in step.keep_player_ids
                ]
                core = self._session_stage_core(
                    run_id=run_id, branch_id=branch_id, original=original,
                    seed=step.seed, preserved=preserved,
                )
                if baselines is not None:
                    baselines = {
                        player.player_id: (
                            baselines[player.player_id]
                            if player.player_id in step.keep_player_ids
                            else self._source_fields(player)
                        )
                        for player in core.players
                    }
            before_edits = self._apply_automatic_fields(
                core, step.automatic_fields, baselines or {},
                generator=generator, season=request.season, seed=step.seed,
            )
            # Keep the verified unedited stage updated for future V2 edits.
            # Otherwise a subsequent step could silently resurrect a previously
            # reset inherited manual value.
            core = before_edits
            result = _apply_preview_field_locks(
                core, step.field_locks, season=request.season,
                seed=step.seed, generator=generator,
            )
            partial_request = request.model_copy(update={
                "seed": step.seed,
                "field_locks": list(step.field_locks),
                "session_steps": request.session_steps[:index + 1],
            })
            previous = source.model_copy(update={
                "request": partial_request, "result": result,
            })
        if previous.request.seed != request.seed or previous.request.field_locks != request.field_locks:
            raise ValueError("Final session seed/field locks do not match authenticated last step")
        return previous
