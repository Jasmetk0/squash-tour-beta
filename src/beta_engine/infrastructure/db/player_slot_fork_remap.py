from __future__ import annotations

import json
from dataclasses import dataclass, field

from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerSportingWeekState,
)
from beta_engine.domain.simulation_slots import WeekSimulationSchedule, fingerprint
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
    TournamentDrawInputAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_process_authority import (
    TournamentDrawProcessAuthority,
    TournamentDrawProcessAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_revision_authority import (
    TournamentDrawRevision,
    TournamentDrawRevisionBuilder,
)
from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthority,
    TournamentPlayerReplacementCutoffAuthorityBuilder,
)
from beta_engine.domain.tournaments.lucky_loser_authority import (
    TournamentLuckyLoserFillAuthority,
    TournamentLuckyLoserOrderAuthority,
    TournamentLuckyLoserQualificationWinnerEvidence,
    TournamentLuckyLoserVacancyAuthority,
)
from beta_engine.domain.tournaments.replacement_source_authority import (
    TournamentDrawStartEvidence,
    TournamentReplacementSourceAuthority,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryField,
    TournamentEntryFieldResolver,
)
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
    TournamentWildCardAuthorityBuilder,
)
from beta_engine.domain.tournaments.week_tournament_lock import (
    WeekTournamentLockAuthority,
)
from beta_engine.infrastructure.db.models import (
    AdoptedTournamentAuthorityModel,
    AuthoritativeSimulationCommandModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    TournamentDrawAuthorityModel,
    TournamentDrawInputAuthorityModel,
    TournamentDrawProcessAuthorityModel,
    TournamentDrawRevisionModel,
    TournamentEntryFieldVersionModel,
    TournamentWildCardAuthorityModel,
    WeekSimulationScheduleModel,
    WeekTournamentLockAuthorityModel,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
    _applications_fingerprint,
    _applications_json,
    _request_fingerprint as entry_request_fingerprint,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
    _request_fingerprint as draw_authority_request_fingerprint,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
    _request_fingerprint as draw_input_request_fingerprint,
)
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
    _fingerprint as draw_process_request_fingerprint,
)
from beta_engine.infrastructure.db.tournament_draw_revision import (
    _fp as draw_revision_request_fingerprint,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    PLAYER_SPORTING_COMPONENT_KEY,
    _component as sporting_component,
    load_saved_sporting_bundle,
)
from beta_engine.infrastructure.db.simulation_slot_fork_remap import (
    RemappedSimulationSlotCore,
    SimulationSlotForkRemapUnsupportedError,
    remap_completed_simulation_slot_core,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    COMPONENT_KEY as SIMULATION_SLOT_COMPONENT_KEY,
    _component as simulation_component,
    _load as load_saved_simulation_slots,
)


@dataclass(frozen=True)
class SimulationPositionForkIdentityGraph:
    run_id: str
    source_branch_id: str
    target_branch_id: str
    target_base_revision_id: str
    schedule_fingerprints: dict[str, str]
    slot_plan_fingerprints: dict[str, str]
    group_command_fingerprints: dict[str, str]
    result_fingerprints: dict[str, str]
    terminal_checkpoint_payloads: dict[str, str]
    owned_tournament_fingerprints: dict[str, str]
    week_tournament_lock_fingerprints: dict[str, str]
    tournament_authority_fingerprints: dict[str, str]
    sporting_fingerprints: dict[str, str]
    lifecycle_fingerprints: dict[str, str]
    transition_authority_fingerprints: dict[str, str]
    ranking_snapshot_fingerprints: dict[str, str]
    terminal_checkpoint_fingerprints: dict[str, str]
    sporting_context_fingerprints: dict[str, str]
    entry_validation_fingerprints: dict[str, str] = field(default_factory=dict)


_POSITION_BASIS_KEYS = {
    "scope",
    "schedule",
    "entry_slot_ordinals",
    "wc_slot_ordinals",
    "week_tournament_lock",
    "week_tournament_lock_conflicts",
    "entry_validation_slots",
    "current_slot_kind",
    "current_slot_ordinal",
    "proposed_schedule_requirement",
    "slots",
    "groups",
    "owned",
    "tournament_authority",
    "sporting",
    "lifecycle",
    "branch_head",
    "draft",
    "transition_authority",
    "world",
    "terminal",
    "empty_week_context",
}


def _map_optional_position_identity(
    value,
    *,
    mapping: dict[str, str],
    label: str,
):
    if value is None:
        return None
    if not isinstance(value, str):
        raise SimulationSlotForkRemapUnsupportedError(
            f"Simulation opening Position {label} identity is invalid"
        )
    return _mapped_fingerprint(value, fingerprint_map=mapping, label=label)


def _retarget_simulation_opening_position_basis(
    source_basis: dict,
    *,
    graph: SimulationPositionForkIdentityGraph,
) -> dict:
    """Rebuild one historical opening Position from explicit target identity maps."""

    if set(source_basis) != _POSITION_BASIS_KEYS:
        unknown = sorted(set(source_basis) ^ _POSITION_BASIS_KEYS)
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation opening Position basis schema is unsupported: "
            + ", ".join(unknown)
        )

    scope = source_basis["scope"]
    if (
        not isinstance(scope, list)
        or len(scope) != 3
        or scope[0] != graph.run_id
        or scope[1] != graph.source_branch_id
        or not isinstance(scope[2], int)
    ):
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation opening Position scope is corrupt"
        )

    target_entry_validation_slots = []
    for item in source_basis["entry_validation_slots"]:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation opening Position Entry validation identity is corrupt"
            )
        decision_slot_ordinal, validation_fingerprint = item
        if not isinstance(decision_slot_ordinal, int):
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation opening Position Entry validation ordinal is corrupt"
            )
        target_entry_validation_slots.append(
            [
                decision_slot_ordinal,
                _mapped_fingerprint(
                    validation_fingerprint,
                    fingerprint_map=graph.entry_validation_fingerprints,
                    label="resolved Entry validation Slot",
                ),
            ]
        )

    target_slots = []
    for item in source_basis["slots"]:
        if not isinstance(item, (list, tuple)) or len(item) != 4:
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation opening Position Slot identity is corrupt"
            )
        slot_id, status, plan_fingerprint, terminal_payload = item
        target_slots.append(
            [
                slot_id,
                status,
                _mapped_fingerprint(
                    plan_fingerprint,
                    fingerprint_map=graph.slot_plan_fingerprints,
                    label="Simulation Slot plan",
                ),
                (
                    None
                    if terminal_payload is None
                    else _mapped_fingerprint(
                        terminal_payload,
                        fingerprint_map=graph.terminal_checkpoint_payloads,
                        label="Simulation Slot terminal checkpoint payload",
                    )
                ),
            ]
        )

    target_groups = []
    for item in source_basis["groups"]:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation opening Position Group identity is corrupt"
            )
        group_id, command_fingerprint, result_fingerprint = item
        target_groups.append(
            [
                group_id,
                _mapped_fingerprint(
                    command_fingerprint,
                    fingerprint_map=graph.group_command_fingerprints,
                    label="Simulation Group command",
                ),
                _mapped_fingerprint(
                    result_fingerprint,
                    fingerprint_map=graph.result_fingerprints,
                    label="Simulation Group result",
                ),
            ]
        )

    target_owned = []
    for item in source_basis["owned"]:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation opening Position owned tournament identity is corrupt"
            )
        event_id, source_fingerprint = item
        target_owned.append(
            [
                event_id,
                (
                    None
                    if source_fingerprint is None
                    else _mapped_fingerprint(
                        source_fingerprint,
                        fingerprint_map=graph.owned_tournament_fingerprints,
                        label="Owned Tournament Ranking Source",
                    )
                ),
            ]
        )

    source_draft = source_basis["draft"]
    if (
        not isinstance(source_draft, (list, tuple))
        or len(source_draft) != 3
        or not isinstance(source_draft[0], str)
        or not isinstance(source_draft[1], str)
        or not isinstance(source_draft[2], int)
    ):
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation opening Position Working Draft identity is corrupt"
        )

    source_world = source_basis["world"]
    target_world = None
    if source_world is not None:
        if (
            not isinstance(source_world, (list, tuple))
            or len(source_world) != 2
            or not isinstance(source_world[0], int)
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation opening Position World identity is corrupt"
            )
        target_world = [
            source_world[0],
            _mapped_fingerprint(
                source_world[1],
                fingerprint_map=graph.ranking_snapshot_fingerprints,
                label="Official Ranking World head",
            ),
        ]

    return {
        "scope": [graph.run_id, graph.target_branch_id, scope[2]],
        "schedule": _map_optional_position_identity(
            source_basis["schedule"],
            mapping=graph.schedule_fingerprints,
            label="Week Simulation Schedule",
        ),
        "entry_slot_ordinals": source_basis["entry_slot_ordinals"],
        "wc_slot_ordinals": source_basis["wc_slot_ordinals"],
        "week_tournament_lock": _map_optional_position_identity(
            source_basis["week_tournament_lock"],
            mapping=graph.week_tournament_lock_fingerprints,
            label="Week Tournament Lock",
        ),
        "week_tournament_lock_conflicts": source_basis[
            "week_tournament_lock_conflicts"
        ],
        "entry_validation_slots": target_entry_validation_slots,
        "current_slot_kind": source_basis["current_slot_kind"],
        "current_slot_ordinal": source_basis["current_slot_ordinal"],
        "proposed_schedule_requirement": source_basis[
            "proposed_schedule_requirement"
        ],
        "slots": target_slots,
        "groups": target_groups,
        "owned": target_owned,
        "tournament_authority": _map_optional_position_identity(
            source_basis["tournament_authority"],
            mapping=graph.tournament_authority_fingerprints,
            label="Adopted Tournament Authority",
        ),
        "sporting": _map_optional_position_identity(
            source_basis["sporting"],
            mapping=graph.sporting_fingerprints,
            label="Player sporting state",
        ),
        "lifecycle": _map_optional_position_identity(
            source_basis["lifecycle"],
            mapping=graph.lifecycle_fingerprints,
            label="Player lifecycle state",
        ),
        "branch_head": graph.target_base_revision_id,
        "draft": [graph.target_base_revision_id, "clean", 0],
        "transition_authority": _map_optional_position_identity(
            source_basis["transition_authority"],
            mapping=graph.transition_authority_fingerprints,
            label="Ranking Transition Authority",
        ),
        "world": target_world,
        "terminal": _map_optional_position_identity(
            source_basis["terminal"],
            mapping=graph.terminal_checkpoint_fingerprints,
            label="terminal sporting checkpoint",
        ),
        "empty_week_context": _map_optional_position_identity(
            source_basis["empty_week_context"],
            mapping=graph.sporting_context_fingerprints,
            label="empty-week sporting context",
        ),
    }


_SIMULATION_PUBLIC_RESULT_KEYS = {
    "run_id",
    "branch_id",
    "current_week",
    "current_slot_kind",
    "current_slot_id",
    "slot_ordinal",
    "unresolved_group_ids",
    "eligible_match_ids",
    "blocked_match_ids",
    "current_slot_complete",
    "supported_tournament_complete",
    "week_ready_for_transition",
    "transition_blockers",
    "terminal_sporting_fingerprint",
    "position_fingerprint",
}


def _retarget_simulation_public_result(
    source_result: dict,
    *,
    source_closing_basis: dict,
    target_closing_basis: dict,
    graph: SimulationPositionForkIdentityGraph,
) -> dict:
    public = {
        key: value
        for key, value in source_result.items()
        if key != "_request_evidence"
    }
    if set(public) != _SIMULATION_PUBLIC_RESULT_KEYS:
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation public result schema is unsupported for target replay"
        )
    if (
        public.get("run_id") != graph.run_id
        or public.get("branch_id") != graph.source_branch_id
        or public.get("position_fingerprint") != fingerprint(source_closing_basis)
    ):
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation public result identity does not match closing Position evidence"
        )
    target = dict(public)
    target["branch_id"] = graph.target_branch_id
    target["position_fingerprint"] = fingerprint(target_closing_basis)
    target["terminal_sporting_fingerprint"] = _map_optional_position_identity(
        public.get("terminal_sporting_fingerprint"),
        mapping=graph.terminal_checkpoint_fingerprints,
        label="public result terminal sporting checkpoint",
    )
    return target


def _retarget_simulation_command_receipt_as_historical(
    row: AuthoritativeSimulationCommandModel,
    *,
    target_branch_id: str,
    target_base_revision_id: str,
    position_identity_graph: SimulationPositionForkIdentityGraph | None = None,
) -> AuthoritativeSimulationCommandModel:
    try:
        source_result = json.loads(row.result_json)
    except (TypeError, ValueError) as exc:
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation command receipt JSON is corrupt"
        ) from exc
    if not isinstance(source_result, dict):
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation command receipt result must be an object"
        )
    if not target_base_revision_id.strip():
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation command receipt remap requires a target Saved Revision id"
        )

    request_evidence = source_result.get("_request_evidence")
    request_evidence_fingerprint = (
        fingerprint(request_evidence)
        if isinstance(request_evidence, dict)
        else None
    )

    target_request_evidence = None
    target_request_fingerprint = None
    target_result = None
    target_result_fingerprint = None
    if (
        isinstance(request_evidence, dict)
        and request_evidence.get("schema_version")
        in {
            "authoritative_simulation_request_evidence.v2",
            "authoritative_simulation_request_evidence.v3",
        }
    ):
        source_command = request_evidence.get("command")
        source_basis = request_evidence.get("opening_position_basis")
        mode = request_evidence.get("mode")
        if (
            mode not in {"match", "slot"}
            or not isinstance(source_command, dict)
            or not isinstance(source_basis, dict)
            or source_command.get("run_id") != row.run_id
            or source_command.get("branch_id") != row.branch_id
            or source_command.get("command_id") != row.command_id
            or source_command.get("expected_revision_id") != source_basis.get("branch_head")
            or source_command.get("expected_position_fingerprint")
            != fingerprint(source_basis)
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation source request evidence cannot be reconstructed safely"
            )
        if position_identity_graph is not None:
            try:
                target_basis = _retarget_simulation_opening_position_basis(
                    source_basis,
                    graph=position_identity_graph,
                )
            except SimulationSlotForkRemapUnsupportedError:
                target_basis = None
            if target_basis is not None:
                target_command = dict(source_command)
                target_command.update(
                    {
                        "branch_id": target_branch_id,
                        "expected_revision_id": target_base_revision_id,
                        "expected_position_fingerprint": fingerprint(target_basis),
                    }
                )
                source_closing_basis = request_evidence.get(
                    "closing_position_basis"
                )
                target_closing_basis = None
                if request_evidence.get("schema_version") == (
                    "authoritative_simulation_request_evidence.v3"
                ):
                    if not isinstance(source_closing_basis, dict):
                        raise SimulationSlotForkRemapUnsupportedError(
                            "Simulation v3 request evidence is missing closing Position basis"
                        )
                    try:
                        target_closing_basis = (
                            _retarget_simulation_opening_position_basis(
                                source_closing_basis,
                                graph=position_identity_graph,
                            )
                        )
                    except SimulationSlotForkRemapUnsupportedError:
                        target_closing_basis = None

                target_request_evidence = {
                    "schema_version": (
                        "authoritative_simulation_request_evidence.v3"
                        if target_closing_basis is not None
                        else "authoritative_simulation_request_evidence.v2"
                    ),
                    "mode": mode,
                    "command": target_command,
                    "opening_position_basis": target_basis,
                }
                if target_closing_basis is not None:
                    target_request_evidence["closing_position_basis"] = (
                        target_closing_basis
                    )
                    try:
                        target_result = _retarget_simulation_public_result(
                            source_result,
                            source_closing_basis=source_closing_basis,
                            target_closing_basis=target_closing_basis,
                            graph=position_identity_graph,
                        )
                    except SimulationSlotForkRemapUnsupportedError:
                        target_result = None
                    if target_result is not None:
                        target_result_fingerprint = fingerprint(target_result)
                target_request_fingerprint = fingerprint(
                    {"mode": mode, "command": target_command}
                )

    historical_schema = (
        "authoritative_simulation_historical_fork_receipt.v5"
        if target_result is not None
        else (
            "authoritative_simulation_historical_fork_receipt.v3"
            if target_request_evidence is not None
            else "authoritative_simulation_historical_fork_receipt.v2"
        )
    )
    historical = {
        "schema_version": historical_schema,
        "run_id": row.run_id,
        "branch_id": target_branch_id,
        "command_id": row.command_id,
        "target_base_revision_id": target_base_revision_id,
        "source_branch_id": row.branch_id,
        "source_status": row.status,
        "source_request_fingerprint": row.request_fingerprint,
        "source_request_evidence_fingerprint": request_evidence_fingerprint,
        "source_result": source_result,
        "retryable": target_result is not None,
        "provenance": (
            "materialized Branch fork preserves source Simulation command history; "
            "exact target retry is enabled only when target request and result "
            "identity are both reconstructed and integrity-bound"
        ),
    }
    if target_request_evidence is not None:
        historical.update(
            {
                "target_request_evidence": target_request_evidence,
                "target_request_evidence_fingerprint": fingerprint(
                    target_request_evidence
                ),
                "target_request_fingerprint": target_request_fingerprint,
            }
        )
    if target_result is not None:
        historical.update(
            {
                "target_result": target_result,
                "target_result_fingerprint": target_result_fingerprint,
            }
        )
    historical_request = {
        "schema_version": (
            "authoritative_simulation_historical_fork_request.v5"
            if target_result is not None
            else (
                "authoritative_simulation_historical_fork_request.v3"
                if target_request_evidence is not None
                else "authoritative_simulation_historical_fork_request.v2"
            )
        ),
        "run_id": row.run_id,
        "branch_id": target_branch_id,
        "command_id": row.command_id,
        "target_base_revision_id": target_base_revision_id,
        "source_branch_id": row.branch_id,
        "source_request_fingerprint": row.request_fingerprint,
        "source_request_evidence_fingerprint": request_evidence_fingerprint,
    }
    if target_request_evidence is not None:
        historical_request.update(
            {
                "target_request_evidence_fingerprint": fingerprint(
                    target_request_evidence
                ),
                "target_request_fingerprint": target_request_fingerprint,
            }
        )
    if target_result is not None:
        historical_request["target_result_fingerprint"] = target_result_fingerprint
    request_fingerprint = fingerprint(historical_request)
    return AuthoritativeSimulationCommandModel(
        run_id=row.run_id,
        branch_id=target_branch_id,
        command_id=row.command_id,
        request_fingerprint=request_fingerprint,
        status="historical_fork",
        result_json=json.dumps(
            historical,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


@dataclass(frozen=True)
class CoupledPlayerSlotForkRemap:
    sporting_component: dict
    simulation_component: dict
    result_fingerprints: dict[str, str]
    match_effect_fingerprints: dict[str, str]
    terminal_checkpoint_fingerprints: dict[str, str]
    sporting_fingerprints: dict[str, str]
    schedule_fingerprints: dict[str, str]
    slot_plan_fingerprints: dict[str, str]
    group_command_fingerprints: dict[str, str]
    terminal_checkpoint_payloads: dict[str, str]
    week_tournament_lock_fingerprints: dict[str, str]
    adopted_tournament_authority_fingerprints: dict[str, str]
    owned_tournament_fingerprints: dict[str, str]
    sporting_context_fingerprints: dict[str, str]
    entry_validation_fingerprints: dict[str, str]
    frozen_fingerprints: dict[str, str]


def _retarget_frozen_evidence(
    value,
    *,
    target_branch_id: str,
    fingerprint_map: dict[str, str],
):
    """Retarget validated frozen evidence without rewriting its sporting facts."""

    def remap(node):
        if isinstance(node, dict):
            return {
                key: (
                    target_branch_id
                    if key == "branch_id"
                    else remap(item)
                )
                for key, item in node.items()
            }
        if isinstance(node, list):
            return [remap(item) for item in node]
        if isinstance(node, tuple):
            return tuple(remap(item) for item in node)
        if isinstance(node, str):
            return fingerprint_map.get(node, node)
        return node

    payload = remap(value.model_dump(mode="python"))
    return type(value).model_validate(payload)


def _mapped_fingerprint(
    value: str,
    *,
    fingerprint_map: dict[str, str],
    label: str,
) -> str:
    try:
        return fingerprint_map[value]
    except KeyError as exc:
        raise SimulationSlotForkRemapUnsupportedError(
            f"{label} references branch-owned fingerprint without a target mapping"
        ) from exc


def _retarget_cutoff_authority(
    value: TournamentPlayerReplacementCutoffAuthority,
    *,
    target_branch_id: str,
    fingerprint_map: dict[str, str],
) -> TournamentPlayerReplacementCutoffAuthority:
    played_matches = tuple(
        item.model_copy(
            update={
                "result_fingerprint": _mapped_fingerprint(
                    item.result_fingerprint,
                    fingerprint_map=fingerprint_map,
                    label="Replacement cutoff evidence",
                )
            }
        )
        for item in value.played_matches
    )
    target = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
        run_id=value.run_id,
        branch_id=target_branch_id,
        event_id=value.event_id,
        player_id=value.player_id,
        played_matches=played_matches,
        draw_type=value.draw_type,
    )
    if target.status != value.status:
        raise SimulationSlotForkRemapUnsupportedError(
            "Replacement cutoff status changed while retargeting frozen evidence"
        )
    return target


def _retarget_q_winner_evidence(
    value: TournamentLuckyLoserQualificationWinnerEvidence | None,
    *,
    fingerprint_map: dict[str, str],
) -> TournamentLuckyLoserQualificationWinnerEvidence | None:
    if value is None:
        return None
    return value.model_copy(
        update={
            "evidence_fingerprint": _mapped_fingerprint(
                value.evidence_fingerprint,
                fingerprint_map=fingerprint_map,
                label="Qualification winner evidence",
            )
        }
    )


def _retarget_draw_start_evidence(
    value: TournamentDrawStartEvidence | None,
    *,
    fingerprint_map: dict[str, str],
    label: str,
) -> TournamentDrawStartEvidence | None:
    if value is None:
        return None
    return value.model_copy(
        update={
            "result_fingerprint": _mapped_fingerprint(
                value.result_fingerprint,
                fingerprint_map=fingerprint_map,
                label=label,
            )
        }
    )


def _retarget_lucky_loser_order_authority(
    value: TournamentLuckyLoserOrderAuthority,
    *,
    target_branch_id: str,
    fingerprint_map: dict[str, str],
) -> TournamentLuckyLoserOrderAuthority:
    local_map = dict(fingerprint_map)
    target_auto_byes = []
    for item in value.qualification_auto_bye_terminals:
        target_item = item.model_copy(
            update={
                "qualification_bracket_fingerprint": _mapped_fingerprint(
                    item.qualification_bracket_fingerprint,
                    fingerprint_map=fingerprint_map,
                    label="Lucky Loser auto-BYE terminal",
                )
            }
        )
        target_auto_byes.append(target_item)
        local_map[item.fingerprint] = target_item.fingerprint

    target_candidates = tuple(
        item.model_copy(
            update={
                "elimination_result_fingerprint": _mapped_fingerprint(
                    item.elimination_result_fingerprint,
                    fingerprint_map=fingerprint_map,
                    label="Lucky Loser candidate elimination",
                )
            }
        )
        for item in value.candidates
    )
    target_terminal_fingerprints = tuple(
        _mapped_fingerprint(
            item,
            fingerprint_map=local_map,
            label="Lucky Loser terminal evidence",
        )
        for item in value.qualification_terminal_result_fingerprints
    )
    target = value.model_copy(
        update={
            "branch_id": target_branch_id,
            "draw_authority_fingerprint": _mapped_fingerprint(
                value.draw_authority_fingerprint,
                fingerprint_map=fingerprint_map,
                label="Lucky Loser Draw authority",
            ),
            "tournament_ranking_authority_fingerprint": _mapped_fingerprint(
                value.tournament_ranking_authority_fingerprint,
                fingerprint_map=fingerprint_map,
                label="Lucky Loser ranking authority",
            ),
            "qualification_terminal_result_fingerprints": (
                target_terminal_fingerprints
            ),
            "qualification_auto_bye_terminals": tuple(target_auto_byes),
            "candidates": target_candidates,
        }
    )
    return TournamentLuckyLoserOrderAuthority.model_validate(
        target.model_dump(mode="python")
    )


def _retarget_replacement_source_authority(
    value: TournamentReplacementSourceAuthority,
    *,
    target_branch_id: str,
    fingerprint_map: dict[str, str],
) -> TournamentReplacementSourceAuthority:
    target_order = (
        _retarget_lucky_loser_order_authority(
            value.lucky_loser_order_authority,
            target_branch_id=target_branch_id,
            fingerprint_map=fingerprint_map,
        )
        if value.lucky_loser_order_authority is not None
        else None
    )
    target = value.model_copy(
        update={
            "branch_id": target_branch_id,
            "predecessor_draw_fingerprint": _mapped_fingerprint(
                value.predecessor_draw_fingerprint,
                fingerprint_map=fingerprint_map,
                label="Replacement source Draw",
            ),
            "predecessor_draw_input_fingerprint": _mapped_fingerprint(
                value.predecessor_draw_input_fingerprint,
                fingerprint_map=fingerprint_map,
                label="Replacement source Draw Input",
            ),
            "qualification_winner_evidence": _retarget_q_winner_evidence(
                value.qualification_winner_evidence,
                fingerprint_map=fingerprint_map,
            ),
            "qualification_start_evidence": _retarget_draw_start_evidence(
                value.qualification_start_evidence,
                fingerprint_map=fingerprint_map,
                label="Replacement source Qualification-start evidence",
            ),
            "main_start_evidence": _retarget_draw_start_evidence(
                value.main_start_evidence,
                fingerprint_map=fingerprint_map,
                label="Replacement source Main-start evidence",
            ),
            "replacement_cutoff_authority": _retarget_cutoff_authority(
                value.replacement_cutoff_authority,
                target_branch_id=target_branch_id,
                fingerprint_map=fingerprint_map,
            ),
            "lucky_loser_order_authority": target_order,
            "base_wild_card_authority_fingerprint": (
                _mapped_fingerprint(
                    value.base_wild_card_authority_fingerprint,
                    fingerprint_map=fingerprint_map,
                    label="Replacement source Wild Card authority",
                )
                if value.base_wild_card_authority_fingerprint is not None
                else None
            ),
        }
    )
    return TournamentReplacementSourceAuthority.model_validate(
        target.model_dump(mode="python")
    )


def _retarget_lucky_loser_vacancy_authority(
    value: TournamentLuckyLoserVacancyAuthority,
    *,
    target_branch_id: str,
    fingerprint_map: dict[str, str],
) -> TournamentLuckyLoserVacancyAuthority:
    target = value.model_copy(
        update={
            "branch_id": target_branch_id,
            "predecessor_draw_fingerprint": _mapped_fingerprint(
                value.predecessor_draw_fingerprint,
                fingerprint_map=fingerprint_map,
                label="Lucky Loser vacancy Draw",
            ),
            "predecessor_draw_input_fingerprint": _mapped_fingerprint(
                value.predecessor_draw_input_fingerprint,
                fingerprint_map=fingerprint_map,
                label="Lucky Loser vacancy Draw Input",
            ),
            "withdrawn_player_cutoff_authority": _retarget_cutoff_authority(
                value.withdrawn_player_cutoff_authority,
                target_branch_id=target_branch_id,
                fingerprint_map=fingerprint_map,
            ),
            "qualification_start_authority": _retarget_cutoff_authority(
                value.qualification_start_authority,
                target_branch_id=target_branch_id,
                fingerprint_map=fingerprint_map,
            ),
            "qualification_winner_evidence": _retarget_q_winner_evidence(
                value.qualification_winner_evidence,
                fingerprint_map=fingerprint_map,
            ),
        }
    )
    return TournamentLuckyLoserVacancyAuthority.model_validate(
        target.model_dump(mode="python")
    )


def _retarget_lucky_loser_fill_authority(
    value: TournamentLuckyLoserFillAuthority,
    *,
    target_branch_id: str,
    fingerprint_map: dict[str, str],
) -> TournamentLuckyLoserFillAuthority:
    target_order = _retarget_lucky_loser_order_authority(
        value.order_authority,
        target_branch_id=target_branch_id,
        fingerprint_map=fingerprint_map,
    )
    selected = next(
        (
            item
            for item in target_order.candidates
            if item.player_id == value.selected_candidate.player_id
            and item.priority_ordinal == value.selected_candidate.priority_ordinal
        ),
        None,
    )
    if selected is None:
        raise SimulationSlotForkRemapUnsupportedError(
            "Lucky Loser selected candidate is absent after evidence retarget"
        )
    target = value.model_copy(
        update={
            "branch_id": target_branch_id,
            "predecessor_draw_fingerprint": _mapped_fingerprint(
                value.predecessor_draw_fingerprint,
                fingerprint_map=fingerprint_map,
                label="Lucky Loser fill Draw",
            ),
            "predecessor_draw_input_fingerprint": _mapped_fingerprint(
                value.predecessor_draw_input_fingerprint,
                fingerprint_map=fingerprint_map,
                label="Lucky Loser fill Draw Input",
            ),
            "order_authority": target_order,
            "selected_candidate": selected,
        }
    )
    return TournamentLuckyLoserFillAuthority.model_validate(
        target.model_dump(mode="python")
    )


def remap_coupled_player_slot_history(
    payload,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    target_base_revision_id: str | None = None,
    v1_source_fingerprint_map: dict[str, str],
    tournament_ranking_authority_map: dict[
        str, TournamentRankingSnapshotAuthority
    ] | None = None,
    lifecycle_fingerprint_map: dict[str, str] | None = None,
    ranking_snapshot_fingerprint_map: dict[str, str] | None = None,
    transition_authority_fingerprint_map: dict[str, str] | None = None,
    entry_validation_fingerprint_map: dict[str, str] | None = None,
) -> CoupledPlayerSlotForkRemap | None:
    """Remap sporting + completed Slot core in canonical week order.

    Each target sporting state becomes the opening authority for that week's target
    Simulation Slot ledger. The rebuilt ledger then provides the evidence needed to
    rebuild that week's completed sporting context and therefore the next sporting state.
    """
    source_bundle = load_saved_sporting_bundle(
        payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    source_slot_component = load_saved_simulation_slots(
        payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    if source_bundle is None or source_slot_component is None:
        return None

    tournament_ranking_authority_map = tournament_ranking_authority_map or {}
    lifecycle_fingerprint_map = lifecycle_fingerprint_map or {}
    ranking_snapshot_fingerprint_map = ranking_snapshot_fingerprint_map or {}
    transition_authority_fingerprint_map = (
        transition_authority_fingerprint_map or {}
    )
    entry_validation_fingerprint_map = entry_validation_fingerprint_map or {}

    auxiliary = set(source_slot_component) - {
        "fingerprint",
        "slots",
        "groups",
        "authorities",
        "schedules",
        "entry_fields",
        "wild_card_authorities",
        "draw_inputs",
        "draw_authorities",
        "draw_process_authorities",
        "draw_revisions",
        "week_tournament_locks",
        "commands",
    }
    nonempty_auxiliary = {
        key for key in auxiliary if source_slot_component.get(key)
    }
    if nonempty_auxiliary:
        raise SimulationSlotForkRemapUnsupportedError(
            "Coupled player/Slot fork does not yet support auxiliary authorities: "
            + ", ".join(sorted(nonempty_auxiliary))
        )

    source_command_rows = [
        AuthoritativeSimulationCommandModel(**value)
        for value in source_slot_component.get("commands", [])
    ]
    source_entry_rows = [
        TournamentEntryFieldVersionModel(**value)
        for value in source_slot_component.get("entry_fields", [])
    ]
    source_wc_rows = [
        TournamentWildCardAuthorityModel(**value)
        for value in source_slot_component.get("wild_card_authorities", [])
    ]
    source_draw_input_rows = [
        TournamentDrawInputAuthorityModel(**value)
        for value in source_slot_component.get("draw_inputs", [])
    ]
    source_draw_rows = [
        TournamentDrawAuthorityModel(**value)
        for value in source_slot_component.get("draw_authorities", [])
    ]
    source_draw_process_rows = [
        TournamentDrawProcessAuthorityModel(**value)
        for value in source_slot_component.get("draw_process_authorities", [])
    ]
    source_draw_revision_rows = [
        TournamentDrawRevisionModel(**value)
        for value in source_slot_component.get("draw_revisions", [])
    ]
    source_week_lock_rows = [
        WeekTournamentLockAuthorityModel(**value)
        for value in source_slot_component.get("week_tournament_locks", [])
    ]

    if source_command_rows and not (target_base_revision_id or "").strip():
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation command history requires a target Saved Revision id"
        )
    target_entry_rows: list[TournamentEntryFieldVersionModel] = []
    target_wc_rows: list[TournamentWildCardAuthorityModel] = []
    target_draw_input_rows: list[TournamentDrawInputAuthorityModel] = []
    target_draw_rows: list[TournamentDrawAuthorityModel] = []
    target_draw_process_rows: list[TournamentDrawProcessAuthorityModel] = []
    target_draw_revision_rows: list[TournamentDrawRevisionModel] = []
    target_week_lock_rows: list[WeekTournamentLockAuthorityModel] = []
    week_tournament_lock_fingerprint_map: dict[str, str] = {}
    target_fields_by_event: dict[str, tuple[TournamentEntryField, ...]] = {}
    target_apps_by_event: dict[str, tuple[TournamentEntryApplication, ...]] = {}
    target_ranking_by_event: dict[str, TournamentRankingSnapshotAuthority] = {}
    target_wc_by_event: dict[str, TournamentWildCardAuthority] = {}
    target_draw_input_by_event: dict[str, TournamentDrawInputAuthority] = {}
    target_draw_by_event: dict[str, TournamentDrawAuthority] = {}
    source_draw_by_event: dict[str, TournamentDrawAuthority] = {}
    target_process_by_event: dict[str, TournamentDrawProcessAuthority] = {}
    target_draw_fingerprint_map: dict[str, str] = {}
    target_frozen_fingerprint_map: dict[str, str] = {}

    source_entries_by_event: dict[str, list[TournamentEntryFieldVersionModel]] = {}
    for row in source_entry_rows:
        source_entries_by_event.setdefault(row.event_id, []).append(row)

    for event_id, rows in source_entries_by_event.items():
        ordered = tuple(sorted(rows, key=lambda row: row.sequence))
        source_authority_fingerprint = ordered[0].ranking_authority_fingerprint
        target_authority = tournament_ranking_authority_map.get(
            source_authority_fingerprint
        )
        if target_authority is None:
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Entry Field references ranking authority without a target mapping"
            )
        source_authority = None
        source_fields: tuple[TournamentEntryField, ...] = ()
        # Reconstruct source authority from the frozen field contract: every row must
        # point at the same source authority fingerprint, which is already mapped.
        if any(
            row.ranking_authority_fingerprint != source_authority_fingerprint
            for row in ordered
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Entry Field history changes ranking authority mid-lineage"
            )

        target_fields: list[TournamentEntryField] = []
        previous_target: TournamentEntryField | None = None
        for row in ordered:
            source_field, source_apps = TournamentEntryFieldStore._load_row(row)
            target_apps = tuple(
                TournamentEntryApplication.model_validate_json(
                    app.model_copy(update={"branch_id": target_branch_id}).model_dump_json()
                )
                for app in source_apps
            )
            apps_fp = _applications_fingerprint(target_apps)
            if row.sequence == 1:
                target_field = TournamentEntryFieldResolver.build_initial(
                    authority=target_authority,
                    applications=target_apps,
                    capacity=source_field.capacity,
                )
                request_fp = entry_request_fingerprint(
                    {
                        "mode": "initial",
                        "run_id": run_id,
                        "branch_id": target_branch_id,
                        "event_id": event_id,
                        "authority_fingerprint": target_authority.fingerprint,
                        "applications_fingerprint": apps_fp,
                        "capacity": source_field.capacity.model_dump(mode="json"),
                    }
                )
            else:
                if previous_target is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Tournament Entry Field repair has no target predecessor"
                    )
                source_previous = TournamentEntryFieldStore._load_row(
                    ordered[row.sequence - 2]
                )[0]
                newly_withdrawn = tuple(
                    sorted(
                        set(source_field.withdrawn_player_ids)
                        - set(source_previous.withdrawn_player_ids)
                    )
                )
                target_field = TournamentEntryFieldResolver.repair_pre_draw(
                    authority=target_authority,
                    applications=target_apps,
                    previous=previous_target,
                    withdrawn_player_ids=newly_withdrawn,
                )
                request_fp = entry_request_fingerprint(
                    {
                        "mode": "pre_draw_repair",
                        "run_id": run_id,
                        "branch_id": target_branch_id,
                        "event_id": event_id,
                        "authority_fingerprint": target_authority.fingerprint,
                        "applications_fingerprint": apps_fp,
                        "predecessor_fingerprint": previous_target.fingerprint,
                        "withdrawn_player_ids": newly_withdrawn,
                    }
                )
            target_entry_rows.append(
                TournamentEntryFieldVersionModel(
                    run_id=run_id,
                    branch_id=target_branch_id,
                    event_id=event_id,
                    sequence=row.sequence,
                    command_id=row.command_id,
                    request_fingerprint=request_fp,
                    field_fingerprint=target_field.fingerprint,
                    predecessor_fingerprint=(
                        previous_target.fingerprint
                        if previous_target is not None
                        else None
                    ),
                    ranking_authority_fingerprint=target_authority.fingerprint,
                    applications_fingerprint=apps_fp,
                    applications_json=_applications_json(target_apps),
                    payload_json=target_field.model_dump_json(),
                )
            )
            target_fields.append(target_field)
            previous_target = target_field
        target_fields_by_event[event_id] = tuple(target_fields)
        target_apps_by_event[event_id] = tuple(
            TournamentEntryApplication.model_validate_json(
                app.model_copy(update={"branch_id": target_branch_id}).model_dump_json()
            )
            for app in TournamentEntryFieldStore._load_row(ordered[-1])[1]
        )
        target_ranking_by_event[event_id] = target_authority
        target_frozen_fingerprint_map[source_authority_fingerprint] = (
            target_authority.fingerprint
        )
        for source_row, target_field in zip(ordered, target_fields, strict=True):
            target_frozen_fingerprint_map[source_row.field_fingerprint] = (
                target_field.fingerprint
            )

    for row in source_week_lock_rows:
        source_lock = WeekTournamentLockAuthority.model_validate_json(row.payload_json)
        target_evidence = []
        for evidence in source_lock.event_evidence:
            mapped_field = target_frozen_fingerprint_map.get(
                evidence.entry_field_fingerprint
            )
            if mapped_field is None:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Week Tournament Lock references Entry Field without a target mapping"
                )
            target_evidence.append(
                evidence.model_copy(
                    update={"entry_field_fingerprint": mapped_field}
                )
            )
        target_lock = WeekTournamentLockAuthority.model_validate(
            source_lock.model_copy(
                update={
                    "branch_id": target_branch_id,
                    "event_evidence": tuple(target_evidence),
                }
            ).model_dump(mode="python")
        )
        target_week_lock_rows.append(
            WeekTournamentLockAuthorityModel(
                run_id=run_id,
                branch_id=target_branch_id,
                week_ordinal=row.week_ordinal,
                command_id=row.command_id,
                request_fingerprint=row.request_fingerprint,
                authority_fingerprint=target_lock.fingerprint,
                payload_json=target_lock.model_dump_json(),
            )
        )
        week_tournament_lock_fingerprint_map[row.authority_fingerprint] = (
            target_lock.fingerprint
        )

    for row in source_wc_rows:
        source_authority = TournamentWildCardAuthority.model_validate_json(
            row.payload_json
        )
        fields = target_fields_by_event.get(row.event_id)
        if not fields or row.field_sequence != len(fields):
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament WC authority has no matching target terminal Entry Field"
            )
        target_field = fields[-1]
        target_authority = TournamentWildCardAuthorityBuilder.build(
            field=target_field,
            field_sequence=row.field_sequence,
            command_id=row.command_id,
            original_wild_card_player_ids=source_authority.original_wild_card_player_ids,
            reserve_wild_card_player_ids=source_authority.reserve_wild_card_player_ids,
            unavailable_player_ids=source_authority.unavailable_player_ids,
            decision_week=source_authority.decision_week,
            decision_slot_ordinal=source_authority.decision_slot_ordinal,
            selection_policy_id=source_authority.selection_policy_id,
            operator_label=source_authority.operator_label,
            audit_reason=source_authority.audit_reason,
        )
        request = {
            "entry_field_fingerprint": target_field.fingerprint,
            "field_sequence": row.field_sequence,
            "original_wild_card_player_ids": list(
                source_authority.original_wild_card_player_ids
            ),
            "reserve_wild_card_player_ids": list(
                source_authority.reserve_wild_card_player_ids
            ),
            "unavailable_player_ids": sorted(
                set(source_authority.unavailable_player_ids)
            ),
        }
        if source_authority.decision_week is not None:
            request["decision_week"] = source_authority.decision_week.model_dump(
                mode="json"
            )
            request["decision_slot_ordinal"] = (
                source_authority.decision_slot_ordinal
            )
        if source_authority.selection_policy_id is not None:
            request["selection_policy_id"] = source_authority.selection_policy_id
            request["operator_label"] = source_authority.operator_label
            request["audit_reason"] = source_authority.audit_reason
        target_wc_rows.append(
            TournamentWildCardAuthorityModel(
                run_id=run_id,
                branch_id=target_branch_id,
                event_id=row.event_id,
                command_id=row.command_id,
                request_fingerprint=fingerprint(request),
                authority_fingerprint=target_authority.fingerprint,
                entry_field_fingerprint=target_field.fingerprint,
                field_sequence=row.field_sequence,
                payload_json=target_authority.model_dump_json(),
            )
        )
        target_wc_by_event[row.event_id] = target_authority
        target_frozen_fingerprint_map[row.authority_fingerprint] = (
            target_authority.fingerprint
        )

    for row in source_draw_input_rows:
        source_draw_input = TournamentDrawInputAuthority.model_validate_json(
            row.payload_json
        )
        fields = target_fields_by_event.get(row.event_id)
        target_ranking_authority = tournament_ranking_authority_map.get(
            source_draw_input.tournament_ranking_authority_fingerprint
        )
        if not fields or target_ranking_authority is None:
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Draw Input has no mapped ranking/Entry Field dependencies"
            )
        target_field = fields[-1]
        target_wc = target_wc_by_event.get(row.event_id)
        target_draw_input = TournamentDrawInputAuthorityBuilder.build(
            authority=target_ranking_authority,
            field=target_field,
            field_sequence=row.field_sequence,
            command_id=row.command_id,
            draw_seed=source_draw_input.draw_seed,
            main_seed_count=source_draw_input.main_seed_count,
            qualification_seed_count=source_draw_input.qualification_seed_count,
            schema_version=source_draw_input.schema_version,
            wild_card_authority=target_wc,
        )
        request = TournamentDrawInputAuthorityStore._request(
            ranking_authority_fingerprint=target_ranking_authority.fingerprint,
            entry_field_fingerprint=target_field.fingerprint,
            field_sequence=row.field_sequence,
            draw_seed=source_draw_input.draw_seed,
            main_seed_count=target_draw_input.main_seed_count,
            qualification_seed_count=target_draw_input.qualification_seed_count,
            wild_card_authority_fingerprint=(
                target_draw_input.wild_card_authority_fingerprint
            ),
        )
        target_draw_input_rows.append(
            TournamentDrawInputAuthorityModel(
                run_id=run_id,
                branch_id=target_branch_id,
                event_id=row.event_id,
                command_id=row.command_id,
                request_fingerprint=draw_input_request_fingerprint(request),
                authority_fingerprint=target_draw_input.fingerprint,
                ranking_authority_fingerprint=target_ranking_authority.fingerprint,
                entry_field_fingerprint=target_field.fingerprint,
                field_sequence=row.field_sequence,
                payload_json=target_draw_input.model_dump_json(),
            )
        )
        target_draw_input_by_event[row.event_id] = target_draw_input
        target_frozen_fingerprint_map[row.authority_fingerprint] = (
            target_draw_input.fingerprint
        )

    for row in source_draw_rows:
        source_draw = TournamentDrawAuthority.model_validate_json(row.payload_json)
        target_draw_input = target_draw_input_by_event.get(row.event_id)
        if target_draw_input is None:
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Draw authority has no mapped Draw Input dependency"
            )
        if (
            source_draw.draw_input_fingerprint != row.draw_input_fingerprint
            or source_draw.fingerprint != row.authority_fingerprint
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Saved Tournament Draw authority identity is corrupt"
            )
        target_draw = TournamentDrawAuthorityBuilder.build(
            draw_input=target_draw_input,
            command_id=row.command_id,
            algorithm_version=source_draw.algorithm_version,
        )
        request = TournamentDrawAuthorityStore._request(
            draw_input_fingerprint=target_draw_input.fingerprint
        )
        target_draw_rows.append(
            TournamentDrawAuthorityModel(
                run_id=run_id,
                branch_id=target_branch_id,
                event_id=row.event_id,
                command_id=row.command_id,
                request_fingerprint=draw_authority_request_fingerprint(request),
                authority_fingerprint=target_draw.fingerprint,
                draw_input_fingerprint=target_draw_input.fingerprint,
                payload_json=target_draw.model_dump_json(),
            )
        )
        source_draw_by_event[row.event_id] = source_draw
        target_draw_by_event[row.event_id] = target_draw
        target_draw_fingerprint_map[source_draw.fingerprint] = target_draw.fingerprint
        target_frozen_fingerprint_map[source_draw.fingerprint] = target_draw.fingerprint

    for row in source_draw_process_rows:
        source_process = TournamentDrawProcessAuthority.model_validate_json(
            row.payload_json
        )
        target_draw = target_draw_by_event.get(row.event_id)
        if target_draw is None:
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Draw process authority has no mapped Draw dependency"
            )
        if (
            source_process.draw_authority_fingerprint
            != row.draw_authority_fingerprint
            or source_process.fingerprint != row.authority_fingerprint
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Saved Tournament Draw process authority identity is corrupt"
            )
        target_process = TournamentDrawProcessAuthorityBuilder.build(
            draw=target_draw,
            command_id=row.command_id,
            main_process_window_count=source_process.main.process_window_count,
            qualification_process_window_count=(
                source_process.qualification.process_window_count
                if source_process.qualification is not None
                else None
            ),
        )
        request = TournamentDrawProcessAuthorityStore._request(
            draw_authority_fingerprint=target_draw.fingerprint,
            main_process_window_count=source_process.main.process_window_count,
            qualification_process_window_count=(
                source_process.qualification.process_window_count
                if source_process.qualification is not None
                else None
            ),
        )
        target_draw_process_rows.append(
            TournamentDrawProcessAuthorityModel(
                run_id=run_id,
                branch_id=target_branch_id,
                event_id=row.event_id,
                command_id=row.command_id,
                request_fingerprint=draw_process_request_fingerprint(request),
                authority_fingerprint=target_process.fingerprint,
                draw_authority_fingerprint=target_draw.fingerprint,
                payload_json=target_process.model_dump_json(),
            )
        )
        target_process_by_event[row.event_id] = target_process
        target_frozen_fingerprint_map[row.authority_fingerprint] = (
            target_process.fingerprint
        )

    source_schedules = [
        WeekSimulationScheduleModel(**value)
        for value in source_slot_component.get("schedules", [])
    ]
    target_schedules: list[WeekSimulationScheduleModel] = []
    schedule_fingerprint_map: dict[str, str] = {}
    for row in source_schedules:
        schedule = WeekSimulationSchedule.model_validate_json(row.payload_json)
        if (
            schedule.run_id,
            schedule.branch_id,
            schedule.week.ordinal,
            schedule.fingerprint,
        ) != (
            run_id,
            source_branch_id,
            row.week_ordinal,
            row.schedule_fingerprint,
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Saved Week Simulation Schedule identity is corrupt"
            )
        target_schedule = WeekSimulationSchedule.model_validate_json(
            schedule.model_copy(update={"branch_id": target_branch_id}).model_dump_json()
        )
        target_request_fingerprint = fingerprint(
            {
                "request_id": row.request_id,
                "schedule": target_schedule.canonical_payload(),
            }
        )
        target_schedules.append(
            WeekSimulationScheduleModel(
                run_id=run_id,
                branch_id=target_branch_id,
                week_ordinal=row.week_ordinal,
                request_id=row.request_id,
                request_fingerprint=target_request_fingerprint,
                schedule_fingerprint=target_schedule.fingerprint,
                payload_json=target_schedule.model_dump_json(),
            )
        )
        schedule_fingerprint_map[row.schedule_fingerprint] = target_schedule.fingerprint

    source_authorities = [
        AdoptedTournamentAuthorityModel(**value)
        for value in source_slot_component.get("authorities", [])
    ]
    target_authorities: list[AdoptedTournamentAuthorityModel] = []
    adopted_authority_fingerprint_map: dict[str, str] = {}

    source_states, source_contexts = source_bundle
    context_by_week = {
        context.completed_week.ordinal: context for context in source_contexts
    }
    slots_by_week: dict[int, list[SimulationSlotModel]] = {}
    groups_by_week: dict[int, list[SimulationEventGroupModel]] = {}
    for value in source_slot_component["slots"]:
        row = SimulationSlotModel(**value)
        slots_by_week.setdefault(row.week_ordinal, []).append(row)
    for value in source_slot_component["groups"]:
        row = SimulationEventGroupModel(**value)
        groups_by_week.setdefault(row.week_ordinal, []).append(row)

    target_states: list[PlayerSportingWeekState] = []
    target_contexts: list[CompletedWeekSportingContext] = []
    target_slot_components: list[dict] = []
    all_results: dict[str, str] = {}
    all_effects: dict[str, str] = {}
    all_terminals: dict[str, str] = {}
    all_slot_plans: dict[str, str] = {}
    all_group_commands: dict[str, str] = {}
    all_terminal_payloads: dict[str, str] = {}
    sporting_fingerprint_map: dict[str, str] = {}
    sporting_context_fingerprint_map: dict[str, str] = {}
    remapped_context_by_week: dict[int, CompletedWeekSportingContext] = {}

    previous_target: PlayerSportingWeekState | None = None
    for source_state in source_states:
        updates = {
            "branch_id": target_branch_id,
            "predecessor_fingerprint": (
                previous_target.fingerprint if previous_target is not None else None
            ),
        }
        if source_state.week.ordinal != 0:
            predecessor_context = remapped_context_by_week.get(
                source_state.week.ordinal - 1
            )
            if predecessor_context is None:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting state requires a prior completed context that has not been remapped"
                )
            updates["completed_context_fingerprint"] = predecessor_context.fingerprint

        target_state = PlayerSportingWeekState.model_validate_json(
            source_state.model_copy(update=updates).model_dump_json()
        )
        target_states.append(target_state)
        sporting_fingerprint_map[source_state.fingerprint] = target_state.fingerprint
        previous_target = target_state

        week_ordinal = source_state.week.ordinal
        week_slots = sorted(
            slots_by_week.get(week_ordinal, []),
            key=lambda row: row.slot_ordinal,
        )
        week_groups = sorted(
            groups_by_week.get(week_ordinal, []),
            key=lambda row: (row.slot_id, row.group_id),
        )
        week_remap: RemappedSimulationSlotCore | None = None
        if week_slots or week_groups:
            if not week_slots:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Saved Simulation Slot groups exist without their week slots"
                )
            source_week_component = simulation_component(
                week_slots,
                week_groups,
                include_commands=False,
                include_authorities=False,
                include_schedules=False,
                include_entry_fields=False,
                include_wild_card_authorities=False,
                include_draw_inputs=False,
                include_draw_authorities=False,
                include_draw_process_authorities=False,
                include_draw_revisions=False,
            )
            week_remap = remap_completed_simulation_slot_core(
                {"content": {SIMULATION_SLOT_COMPONENT_KEY: source_week_component}},
                run_id=run_id,
                source_branch_id=source_branch_id,
                target_branch_id=target_branch_id,
                opening_sporting_fingerprint_map={
                    source_state.fingerprint: target_state.fingerprint
                },
            )
            assert week_remap is not None
            target_slot_components.append(week_remap.component)
            all_results.update(week_remap.results)
            all_effects.update(week_remap.match_effects)
            all_terminals.update(week_remap.terminal_checkpoints)
            all_slot_plans.update(week_remap.slot_plans)
            all_group_commands.update(week_remap.group_commands)
            all_terminal_payloads.update(week_remap.terminal_checkpoint_payloads)

        source_context = context_by_week.get(week_ordinal)
        if source_context is None:
            continue

        if source_context.schema_version == "completed_week_sporting_context.v1":
            try:
                mapped_sources = tuple(
                    sorted(
                        v1_source_fingerprint_map[value]
                        for value in source_context.source_fingerprints
                    )
                )
            except KeyError as exc:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting v1 context references evidence without a target mapping"
                ) from exc
            context_updates = {
                "branch_id": target_branch_id,
                "source_fingerprints": mapped_sources,
            }
        else:
            if week_remap is None:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting v2 context requires a remapped Simulation Slot week"
                )
            if source_context.terminal_sporting_fingerprint is None:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting v2 context is missing terminal checkpoint evidence"
                )
            try:
                context_updates = {
                    "branch_id": target_branch_id,
                    "source_fingerprints": tuple(
                        sorted(
                            week_remap.results[value]
                            for value in source_context.source_fingerprints
                        )
                    ),
                    "terminal_sporting_fingerprint": week_remap.terminal_checkpoints[
                        source_context.terminal_sporting_fingerprint
                    ],
                    "match_effect_fingerprints": tuple(
                        sorted(
                            week_remap.match_effects[value]
                            for value in source_context.match_effect_fingerprints
                        )
                    ),
                }
            except KeyError as exc:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting v2 context references Slot evidence without a target mapping"
                ) from exc

        target_context = CompletedWeekSportingContext.model_validate_json(
            source_context.model_copy(update=context_updates).model_dump_json()
        )
        target_contexts.append(target_context)
        sporting_context_fingerprint_map[source_context.fingerprint] = (
            target_context.fingerprint
        )
        remapped_context_by_week[week_ordinal] = target_context

    if set(slots_by_week) - {state.week.ordinal for state in source_states}:
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation Slot history contains a week without a saved sporting opening state"
        )

    source_revisions_by_event: dict[str, list[TournamentDrawRevisionModel]] = {}
    for row in source_draw_revision_rows:
        source_revisions_by_event.setdefault(row.event_id, []).append(row)

    for event_id, rows in source_revisions_by_event.items():
        source_initial_draw = source_draw_by_event.get(event_id)
        target_predecessor = target_draw_by_event.get(event_id)
        target_process = target_process_by_event.get(event_id)
        target_ranking = target_ranking_by_event.get(event_id)
        target_initial_input = target_draw_input_by_event.get(event_id)
        target_fields = target_fields_by_event.get(event_id)
        target_apps = target_apps_by_event.get(event_id)
        if (
            source_initial_draw is None
            or target_predecessor is None
            or target_process is None
            or target_ranking is None
            or target_initial_input is None
            or not target_fields
            or target_apps is None
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Draw revision is missing a mapped frozen dependency"
            )

        source_predecessor = source_initial_draw
        source_predecessor_fingerprint = source_initial_draw.fingerprint
        target_previous_field = target_fields[-1]
        target_previous_input = target_initial_input
        for expected_sequence, row in enumerate(
            sorted(rows, key=lambda item: item.sequence),
            start=1,
        ):
            source_revision = TournamentDrawRevision.model_validate_json(row.payload_json)
            if (
                row.sequence != expected_sequence
                or source_revision.sequence != row.sequence
                or source_revision.command_id != row.command_id
                or source_revision.predecessor_draw_fingerprint
                != row.predecessor_draw_fingerprint
                or source_revision.successor_draw.fingerprint
                != row.successor_draw_fingerprint
                or source_revision.fingerprint != row.revision_fingerprint
            ):
                raise SimulationSlotForkRemapUnsupportedError(
                    "Saved Tournament Draw revision identity is corrupt"
                )
            if source_revision.predecessor_draw_fingerprint != source_predecessor_fingerprint:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Saved Tournament Draw revision predecessor chain is corrupt"
                )
            supported_kinds = {
                "full_redraw",
                "seed_cascade_phase",
                "draw_frozen_phase",
                "frozen_wild_card_repair",
                "lucky_loser_vacancy",
                "lucky_loser_fill",
                "frozen_ordinary_fallback",
                "source_bound_pre_q_promotion",
            }
            if source_revision.repair_kind not in supported_kinds:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Tournament Draw revision repair kind is unsupported: "
                    + source_revision.repair_kind
                )

            frozen_map = {
                **target_frozen_fingerprint_map,
                **target_draw_fingerprint_map,
                **all_results,
            }
            for source_bracket, target_bracket in zip(
                source_predecessor.qualification_brackets,
                target_predecessor.qualification_brackets,
                strict=True,
            ):
                frozen_map[source_bracket.fingerprint] = target_bracket.fingerprint

            if source_revision.repair_kind == "frozen_wild_card_repair":
                source_authority = source_revision.wild_card_repair_authority
                if source_authority is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Frozen WC revision lacks repair authority"
                    )
                target_authority = _retarget_frozen_evidence(
                    source_authority,
                    target_branch_id=target_branch_id,
                    fingerprint_map=frozen_map,
                )
                target_successor_input = (
                    TournamentDrawInputAuthorityBuilder.build_post_draw_wild_card_repair(
                        previous=target_previous_input,
                        command_id=row.command_id,
                        withdrawn_player_id=target_authority.withdrawn_player_id,
                        replacement_player_id=target_authority.replacement_player_id,
                        repair_authority_fingerprint=target_authority.fingerprint,
                        qualification_replacement_player_id=(
                            target_authority.replacement_player_id
                            if target_authority.replacement_source == "qualification"
                            else None
                        ),
                        qualification_backfill_player_id=(
                            target_authority.qualification_backfill_player_id
                            if target_authority.replacement_source == "qualification"
                            else None
                        ),
                        main_vacated_seed_number=(
                            target_authority.vacated_main_seed_number
                        ),
                        qualification_vacated_seed_number=(
                            target_authority.vacated_qualification_seed_number
                        ),
                        qualification_full_redraw_reseed=(
                            source_revision.qualification_repair_action
                            == "full_redraw"
                        ),
                    )
                )
                target_revision = TournamentDrawRevisionBuilder.build_frozen_wild_card_repair(
                    predecessor=target_predecessor,
                    successor_field=target_previous_field,
                    successor_draw_input=target_successor_input,
                    process_authority=target_process,
                    main_process_window_ordinal=(
                        source_revision.main_process_window_ordinal
                    ),
                    qualification_process_window_ordinal=(
                        source_revision.qualification_process_window_ordinal
                    ),
                    repair_draw_seed=source_revision.repair_draw_seed,
                    sequence=row.sequence,
                    command_id=row.command_id,
                    wild_card_repair_authority=target_authority,
                )
                request = {
                    "repair_kind": "frozen_wild_card_repair",
                    "predecessor_draw_fingerprint": target_predecessor.fingerprint,
                    "withdrawn_player_id": target_authority.withdrawn_player_id,
                    "main_process_window_ordinal": (
                        source_revision.main_process_window_ordinal
                    ),
                    "qualification_process_window_ordinal": (
                        source_revision.qualification_process_window_ordinal
                    ),
                    "repair_draw_seed": source_revision.repair_draw_seed,
                    "unavailable_reserve_player_ids": list(
                        target_authority.unavailable_player_ids
                    ),
                    "wild_card_repair_authority_fingerprint": (
                        target_authority.fingerprint
                    ),
                }
                target_frozen_fingerprint_map[source_authority.fingerprint] = (
                    target_authority.fingerprint
                )

            elif source_revision.repair_kind == "frozen_ordinary_fallback":
                source_authority = source_revision.replacement_source_authority
                if source_authority is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Frozen ordinary fallback lacks replacement-source authority"
                    )
                target_authority = _retarget_replacement_source_authority(
                    source_authority,
                    target_branch_id=target_branch_id,
                    fingerprint_map=frozen_map,
                )
                slot = target_predecessor.main.slots[
                    target_authority.physical_slot_index - 1
                ]
                q_winner = target_authority.qualification_winner_evidence
                target_successor_input = (
                    TournamentDrawInputAuthorityBuilder.build_frozen_ordinary_fallback(
                        previous=target_previous_input,
                        command_id=row.command_id,
                        withdrawn_player_id=target_authority.withdrawn_player_id,
                        replacement_source_authority_fingerprint=(
                            target_authority.fingerprint
                        ),
                        replacement_player_id=(
                            target_authority.selected_player_id
                            if target_authority.source == "external_reserve"
                            else None
                        ),
                        vacated_main_seed_number=slot.seed_number,
                        create_bye=target_authority.source == "bye",
                        vacated_qualifier_placeholder_id=(
                            q_winner.section_id if q_winner is not None else None
                        ),
                    )
                )
                target_revision = (
                    TournamentDrawRevisionBuilder.build_frozen_ordinary_fallback(
                        predecessor=target_predecessor,
                        successor_field=target_previous_field,
                        successor_draw_input=target_successor_input,
                        process_authority=target_process,
                        main_process_window_ordinal=(
                            source_revision.main_process_window_ordinal
                        ),
                        sequence=row.sequence,
                        command_id=row.command_id,
                        replacement_source_authority=target_authority,
                    )
                )
                request = {
                    "repair_kind": "frozen_ordinary_fallback",
                    "predecessor_draw_fingerprint": target_predecessor.fingerprint,
                    "replacement_source_authority_fingerprint": (
                        target_authority.fingerprint
                    ),
                    "main_process_window_ordinal": (
                        source_revision.main_process_window_ordinal
                    ),
                }
                target_frozen_fingerprint_map[source_authority.fingerprint] = (
                    target_authority.fingerprint
                )

            elif source_revision.repair_kind == "source_bound_pre_q_promotion":
                source_authority = source_revision.replacement_source_authority
                if source_authority is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Source-bound pre-Q revision lacks replacement-source authority"
                    )
                target_authority = _retarget_replacement_source_authority(
                    source_authority,
                    target_branch_id=target_branch_id,
                    fingerprint_map=frozen_map,
                )
                selected = target_authority.selected_player_id
                if selected is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Source-bound pre-Q authority lacks selected player"
                    )
                target_slot = target_predecessor.main.slots[
                    target_authority.physical_slot_index - 1
                ]
                q_slot = next(
                    (
                        slot
                        for bracket in target_predecessor.qualification_brackets
                        for slot in bracket.slots
                        if slot.player_id == selected
                    ),
                    None,
                )
                blocked = (
                    set(target_authority.unavailable_player_ids)
                    | set(target_previous_input.direct_main_player_ids)
                    | set(target_previous_input.wild_card_player_ids)
                    | set(target_previous_input.qualification_player_ids)
                    | set(target_previous_input.lucky_loser_player_ids)
                )
                q_backfill = None
                if selected in set(target_previous_input.qualification_player_ids):
                    q_backfill = next(
                        (
                            candidate
                            for candidate in target_authority.external_reserve_player_ids
                            if candidate not in blocked
                        ),
                        None,
                    )
                target_successor_input = (
                    TournamentDrawInputAuthorityBuilder.build_source_bound_pre_q_promotion(
                        previous=target_previous_input,
                        command_id=row.command_id,
                        withdrawn_player_id=target_authority.withdrawn_player_id,
                        promoted_player_id=selected,
                        replacement_source_authority_fingerprint=(
                            target_authority.fingerprint
                        ),
                        qualification_backfill_player_id=q_backfill,
                        main_vacated_seed_number=target_slot.seed_number,
                        qualification_vacated_seed_number=(
                            q_slot.seed_number if q_slot is not None else None
                        ),
                        qualification_full_redraw_reseed=(
                            source_revision.qualification_repair_action
                            == "full_redraw"
                        ),
                    )
                )
                target_revision = (
                    TournamentDrawRevisionBuilder.build_source_bound_pre_q_promotion(
                        predecessor=target_predecessor,
                        successor_field=target_previous_field,
                        successor_draw_input=target_successor_input,
                        process_authority=target_process,
                        main_process_window_ordinal=(
                            source_revision.main_process_window_ordinal
                        ),
                        qualification_process_window_ordinal=(
                            source_revision.qualification_process_window_ordinal
                        ),
                        sequence=row.sequence,
                        command_id=row.command_id,
                        repair_draw_seed=source_revision.repair_draw_seed,
                        replacement_source_authority=target_authority,
                    )
                )
                request = {
                    "repair_kind": "source_bound_pre_q_promotion",
                    "predecessor_draw_fingerprint": target_predecessor.fingerprint,
                    "replacement_source_authority_fingerprint": (
                        target_authority.fingerprint
                    ),
                    "main_process_window_ordinal": (
                        source_revision.main_process_window_ordinal
                    ),
                    "qualification_process_window_ordinal": (
                        source_revision.qualification_process_window_ordinal
                    ),
                    "repair_draw_seed": source_revision.repair_draw_seed,
                    "qualification_backfill_player_id": q_backfill,
                }
                target_frozen_fingerprint_map[source_authority.fingerprint] = (
                    target_authority.fingerprint
                )

            elif source_revision.repair_kind == "lucky_loser_vacancy":
                source_authority = source_revision.lucky_loser_vacancy_authority
                if source_authority is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Lucky Loser vacancy revision lacks vacancy authority"
                    )
                source_replacement = source_revision.replacement_source_authority
                target_replacement = (
                    _retarget_replacement_source_authority(
                        source_replacement,
                        target_branch_id=target_branch_id,
                        fingerprint_map=frozen_map,
                    )
                    if source_replacement is not None
                    else None
                )
                if source_replacement is not None and target_replacement is not None:
                    target_frozen_fingerprint_map[source_replacement.fingerprint] = (
                        target_replacement.fingerprint
                    )
                    frozen_map[source_replacement.fingerprint] = (
                        target_replacement.fingerprint
                    )
                target_authority = _retarget_lucky_loser_vacancy_authority(
                    source_authority,
                    target_branch_id=target_branch_id,
                    fingerprint_map=frozen_map,
                )
                target_successor_input = (
                    TournamentDrawInputAuthorityBuilder.build_lucky_loser_vacancy(
                        previous=target_previous_input,
                        command_id=row.command_id,
                        withdrawn_player_id=target_authority.withdrawn_player_id,
                        placeholder_id=target_authority.placeholder_id,
                        vacated_main_seed_number=(
                            target_authority.vacated_main_seed_number
                        ),
                        replacement_source_authority_fingerprint=(
                            target_replacement.fingerprint
                            if target_replacement is not None
                            else None
                        ),
                        vacated_qualifier_placeholder_id=(
                            target_authority.qualification_winner_evidence.section_id
                            if target_authority.qualification_winner_evidence
                            is not None
                            else None
                        ),
                    )
                )
                target_revision = (
                    TournamentDrawRevisionBuilder.build_frozen_lucky_loser_vacancy(
                        predecessor=target_predecessor,
                        successor_field=target_previous_field,
                        successor_draw_input=target_successor_input,
                        process_authority=target_process,
                        main_process_window_ordinal=(
                            source_revision.main_process_window_ordinal
                        ),
                        sequence=row.sequence,
                        command_id=row.command_id,
                        lucky_loser_vacancy_authority=target_authority,
                        replacement_source_authority=target_replacement,
                    )
                )
                request = {
                    "repair_kind": "lucky_loser_vacancy",
                    "predecessor_draw_fingerprint": target_predecessor.fingerprint,
                    "withdrawn_player_id": target_authority.withdrawn_player_id,
                    "main_process_window_ordinal": (
                        source_revision.main_process_window_ordinal
                    ),
                    "lucky_loser_ordinal": target_authority.lucky_loser_ordinal,
                    "qualification_start_fingerprint": (
                        target_authority.qualification_start_authority.fingerprint
                    ),
                    "replacement_source_authority_fingerprint": (
                        target_replacement.fingerprint
                        if target_replacement is not None
                        else None
                    ),
                    "qualification_winner_evidence": (
                        target_authority.qualification_winner_evidence.model_dump(
                            mode="json"
                        )
                        if target_authority.qualification_winner_evidence is not None
                        else None
                    ),
                }
                target_frozen_fingerprint_map[source_authority.fingerprint] = (
                    target_authority.fingerprint
                )

            elif source_revision.repair_kind == "lucky_loser_fill":
                source_authority = source_revision.lucky_loser_fill_authority
                if source_authority is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Lucky Loser fill revision lacks fill authority"
                    )
                target_authority = _retarget_lucky_loser_fill_authority(
                    source_authority,
                    target_branch_id=target_branch_id,
                    fingerprint_map=frozen_map,
                )
                target_successor_input = (
                    TournamentDrawInputAuthorityBuilder.build_lucky_loser_fill(
                        previous=target_previous_input,
                        command_id=row.command_id,
                        placeholder_id=target_authority.placeholder_id,
                        player_id=target_authority.selected_candidate.player_id,
                    )
                )
                target_revision = (
                    TournamentDrawRevisionBuilder.build_frozen_lucky_loser_fill(
                        predecessor=target_predecessor,
                        successor_field=target_previous_field,
                        successor_draw_input=target_successor_input,
                        process_authority=target_process,
                        main_process_window_ordinal=(
                            source_revision.main_process_window_ordinal
                        ),
                        sequence=row.sequence,
                        command_id=row.command_id,
                        lucky_loser_fill_authority=target_authority,
                    )
                )
                request = {
                    "repair_kind": "lucky_loser_fill",
                    "predecessor_draw_fingerprint": target_predecessor.fingerprint,
                    "main_process_window_ordinal": (
                        source_revision.main_process_window_ordinal
                    ),
                    "placeholder_id": target_authority.placeholder_id,
                    "selected_player_id": (
                        target_authority.selected_candidate.player_id
                    ),
                    "order_authority_fingerprint": (
                        target_authority.order_authority.fingerprint
                    ),
                    "unavailable_player_ids": list(
                        target_authority.unavailable_player_ids
                    ),
                }
                target_frozen_fingerprint_map[source_authority.fingerprint] = (
                    target_authority.fingerprint
                )

            if source_revision.repair_kind in {
                "frozen_wild_card_repair",
                "lucky_loser_vacancy",
                "lucky_loser_fill",
                "frozen_ordinary_fallback",
                "source_bound_pre_q_promotion",
            }:
                target_draw_revision_rows.append(
                    TournamentDrawRevisionModel(
                        run_id=run_id,
                        branch_id=target_branch_id,
                        event_id=event_id,
                        sequence=row.sequence,
                        command_id=row.command_id,
                        request_fingerprint=draw_revision_request_fingerprint(request),
                        revision_fingerprint=target_revision.fingerprint,
                        predecessor_draw_fingerprint=(
                            target_revision.predecessor_draw_fingerprint
                        ),
                        successor_draw_fingerprint=(
                            target_revision.successor_draw.fingerprint
                        ),
                        payload_json=target_revision.model_dump_json(),
                    )
                )
                target_draw_fingerprint_map[
                    source_revision.successor_draw.fingerprint
                ] = target_revision.successor_draw.fingerprint
                target_frozen_fingerprint_map[
                    source_revision.successor_draw.fingerprint
                ] = target_revision.successor_draw.fingerprint
                target_frozen_fingerprint_map[
                    source_revision.successor_draw_input.fingerprint
                ] = target_revision.successor_draw_input.fingerprint
                target_frozen_fingerprint_map[
                    source_revision.successor_field.fingerprint
                ] = target_revision.successor_field.fingerprint
                target_frozen_fingerprint_map[source_revision.fingerprint] = (
                    target_revision.fingerprint
                )
                source_predecessor = source_revision.successor_draw
                source_predecessor_fingerprint = (
                    source_revision.successor_draw.fingerprint
                )
                target_predecessor = target_revision.successor_draw
                target_previous_field = target_revision.successor_field
                target_previous_input = target_revision.successor_draw_input
                continue

            target_cutoffs = []
            for source_cutoff in source_revision.replacement_cutoff_authorities:
                target_evidence = []
                for evidence in source_cutoff.played_matches:
                    try:
                        mapped_result = all_results[evidence.result_fingerprint]
                    except KeyError as exc:
                        raise SimulationSlotForkRemapUnsupportedError(
                            "Tournament Draw revision cutoff references match evidence without a target mapping"
                        ) from exc
                    target_evidence.append(
                        evidence.model_copy(
                            update={"result_fingerprint": mapped_result}
                        )
                    )
                target_cutoff = TournamentPlayerReplacementCutoffAuthorityBuilder.build(
                    run_id=run_id,
                    branch_id=target_branch_id,
                    event_id=event_id,
                    player_id=source_cutoff.player_id,
                    played_matches=tuple(target_evidence),
                    draw_type=source_cutoff.draw_type,
                )
                if target_cutoff.status != source_cutoff.status:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Tournament Draw revision cutoff status changed during remap"
                    )
                target_cutoffs.append(target_cutoff)
            target_cutoffs = tuple(target_cutoffs)

            target_successor_field = TournamentEntryFieldResolver.repair_pre_draw(
                authority=target_ranking,
                applications=target_apps,
                previous=target_previous_field,
                withdrawn_player_ids=source_revision.withdrawn_player_ids,
            )
            target_successor_input = TournamentDrawInputAuthorityBuilder.build(
                authority=target_ranking,
                field=target_successor_field,
                field_sequence=target_initial_input.field_sequence + row.sequence,
                command_id=row.command_id,
                draw_seed=(
                    source_revision.repair_draw_seed
                    if source_revision.repair_kind == "full_redraw"
                    else target_previous_input.draw_seed
                ),
                main_seed_count=None,
                qualification_seed_count=None,
                schema_version="tournament_draw_input_authority.v2",
            )

            affected = []
            if (
                target_previous_input.direct_main_player_ids
                != target_successor_input.direct_main_player_ids
                or target_previous_input.wild_card_player_ids
                != target_successor_input.wild_card_player_ids
            ):
                affected.append("main")
            if (
                target_previous_input.qualification_player_ids
                != target_successor_input.qualification_player_ids
            ):
                affected.append("qualification")
            affected_draw_types = tuple(affected)
            if affected_draw_types != source_revision.affected_draw_types:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Tournament Draw revision affected components changed during remap"
                )

            common = dict(
                predecessor=target_predecessor,
                successor_field=target_successor_field,
                successor_draw_input=target_successor_input,
                process_authority=target_process,
                affected_draw_types=affected_draw_types,
                main_process_window_ordinal=source_revision.main_process_window_ordinal,
                qualification_process_window_ordinal=(
                    source_revision.qualification_process_window_ordinal
                ),
                withdrawn_player_ids=source_revision.withdrawn_player_ids,
                sequence=row.sequence,
                command_id=row.command_id,
                replacement_cutoff_authorities=target_cutoffs,
            )
            if source_revision.repair_kind == "full_redraw":
                if source_revision.repair_draw_seed is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Full-redraw revision is missing its repair Draw seed"
                    )
                target_revision = TournamentDrawRevisionBuilder.build_full_redraw(
                    **common,
                    repair_draw_seed=source_revision.repair_draw_seed,
                )
                request = {
                    "predecessor_draw_fingerprint": target_predecessor.fingerprint,
                    "process_authority_fingerprint": target_process.fingerprint,
                    "withdrawn_player_ids": list(source_revision.withdrawn_player_ids),
                    "repair_draw_seed": source_revision.repair_draw_seed,
                    "main_process_window_ordinal": source_revision.main_process_window_ordinal,
                    "qualification_process_window_ordinal": (
                        source_revision.qualification_process_window_ordinal
                    ),
                    "affected_draw_types": list(affected_draw_types),
                    "successor_field_fingerprint": target_successor_field.fingerprint,
                    "replacement_cutoff_authority_fingerprints": [
                        authority.fingerprint for authority in target_cutoffs
                    ],
                }
            elif source_revision.repair_kind == "seed_cascade_phase":
                target_revision = TournamentDrawRevisionBuilder.build_seed_cascade_phase(
                    **common,
                    repair_draw_seed=source_revision.repair_draw_seed,
                )
                request = {
                    "repair_kind": "seed_cascade_phase",
                    "predecessor_draw_fingerprint": target_predecessor.fingerprint,
                    "process_authority_fingerprint": target_process.fingerprint,
                    "withdrawn_player_ids": list(source_revision.withdrawn_player_ids),
                    "main_process_window_ordinal": source_revision.main_process_window_ordinal,
                    "qualification_process_window_ordinal": (
                        source_revision.qualification_process_window_ordinal
                    ),
                    "repair_draw_seed": source_revision.repair_draw_seed,
                    "affected_draw_types": list(affected_draw_types),
                    "successor_field_fingerprint": target_successor_field.fingerprint,
                    "replacement_cutoff_authority_fingerprints": [
                        authority.fingerprint for authority in target_cutoffs
                    ],
                }
            else:
                target_revision = TournamentDrawRevisionBuilder.build_draw_frozen_phase(
                    **common,
                    repair_draw_seed=source_revision.repair_draw_seed,
                )
                request = {
                    "repair_kind": "draw_frozen_phase",
                    "predecessor_draw_fingerprint": target_predecessor.fingerprint,
                    "process_authority_fingerprint": target_process.fingerprint,
                    "withdrawn_player_ids": list(source_revision.withdrawn_player_ids),
                    "main_process_window_ordinal": source_revision.main_process_window_ordinal,
                    "qualification_process_window_ordinal": (
                        source_revision.qualification_process_window_ordinal
                    ),
                    "repair_draw_seed": source_revision.repair_draw_seed,
                    "affected_draw_types": list(affected_draw_types),
                    "successor_field_fingerprint": target_successor_field.fingerprint,
                    "replacement_cutoff_authority_fingerprints": [
                        authority.fingerprint for authority in target_cutoffs
                    ],
                }

            target_draw_revision_rows.append(
                TournamentDrawRevisionModel(
                    run_id=run_id,
                    branch_id=target_branch_id,
                    event_id=event_id,
                    sequence=row.sequence,
                    command_id=row.command_id,
                    request_fingerprint=draw_revision_request_fingerprint(request),
                    revision_fingerprint=target_revision.fingerprint,
                    predecessor_draw_fingerprint=target_revision.predecessor_draw_fingerprint,
                    successor_draw_fingerprint=target_revision.successor_draw.fingerprint,
                    payload_json=target_revision.model_dump_json(),
                )
            )
            target_draw_fingerprint_map[
                source_revision.successor_draw.fingerprint
            ] = target_revision.successor_draw.fingerprint
            target_frozen_fingerprint_map[
                source_revision.successor_draw.fingerprint
            ] = target_revision.successor_draw.fingerprint
            target_frozen_fingerprint_map[
                source_revision.successor_draw_input.fingerprint
            ] = target_revision.successor_draw_input.fingerprint
            target_frozen_fingerprint_map[
                source_revision.successor_field.fingerprint
            ] = target_revision.successor_field.fingerprint
            target_frozen_fingerprint_map[source_revision.fingerprint] = (
                target_revision.fingerprint
            )
            source_predecessor = source_revision.successor_draw
            source_predecessor_fingerprint = source_revision.successor_draw.fingerprint
            target_predecessor = target_revision.successor_draw
            target_previous_field = target_revision.successor_field
            target_previous_input = target_revision.successor_draw_input

    if source_authorities:
        from beta_engine.application.authoritative_run_simulation_driver import (
            AuthoritativeRunSimulationDriver,
        )

        for row in source_authorities:
            items = AuthoritativeRunSimulationDriver._decode_adopted_authority(
                row.package_json
            )
            week = next(
                (
                    state.week
                    for state in source_bundle[0]
                    if state.week.ordinal == row.week_ordinal
                ),
                None,
            )
            if week is None:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Adopted Tournament authority week has no saved sporting state"
                )
            source_fingerprint = (
                AuthoritativeRunSimulationDriver._tournament_authority_fingerprint(
                    run_id,
                    source_branch_id,
                    week,
                    items,
                )
            )
            if source_fingerprint != row.authority_fingerprint:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Saved Adopted Tournament authority fingerprint is corrupt"
                )

            target_items = []
            for item in items:
                if item.draw_authority_fingerprint is None:
                    target_items.append(item)
                    continue
                mapped_draw_fingerprint = target_draw_fingerprint_map.get(
                    item.draw_authority_fingerprint
                )
                if mapped_draw_fingerprint is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Adopted Tournament authority references Draw evidence without a target mapping"
                    )
                target_items.append(
                    item.model_copy(
                        update={
                            "draw_authority_fingerprint": mapped_draw_fingerprint
                        }
                    )
                )
            target_items = tuple(target_items)
            target_fingerprint = (
                AuthoritativeRunSimulationDriver._tournament_authority_fingerprint(
                    run_id,
                    target_branch_id,
                    week,
                    target_items,
                )
            )
            target_authorities.append(
                AdoptedTournamentAuthorityModel(
                    run_id=run_id,
                    branch_id=target_branch_id,
                    week_ordinal=row.week_ordinal,
                    event_id=row.event_id,
                    authority_fingerprint=target_fingerprint,
                    package_json=AuthoritativeRunSimulationDriver._encode_adopted_authority(
                        target_items
                    ),
                )
            )
            adopted_authority_fingerprint_map[row.authority_fingerprint] = (
                target_fingerprint
            )

    target_slots = sorted(
        (
            SimulationSlotModel(**value)
            for component in target_slot_components
            for value in component["slots"]
        ),
        key=lambda row: (row.week_ordinal, row.slot_ordinal),
    )
    target_groups = sorted(
        (
            SimulationEventGroupModel(**value)
            for component in target_slot_components
            for value in component["groups"]
        ),
        key=lambda row: (
            row.week_ordinal,
            row.slot_id,
            row.group_id,
        ),
    )
    position_identity_graph = SimulationPositionForkIdentityGraph(
        run_id=run_id,
        source_branch_id=source_branch_id,
        target_branch_id=target_branch_id,
        target_base_revision_id=target_base_revision_id or "",
        schedule_fingerprints=schedule_fingerprint_map,
        slot_plan_fingerprints=all_slot_plans,
        group_command_fingerprints=all_group_commands,
        result_fingerprints=all_results,
        terminal_checkpoint_payloads=all_terminal_payloads,
        owned_tournament_fingerprints=dict(v1_source_fingerprint_map),
        week_tournament_lock_fingerprints=week_tournament_lock_fingerprint_map,
        tournament_authority_fingerprints=adopted_authority_fingerprint_map,
        sporting_fingerprints=sporting_fingerprint_map,
        lifecycle_fingerprints=lifecycle_fingerprint_map,
        transition_authority_fingerprints=transition_authority_fingerprint_map,
        ranking_snapshot_fingerprints=ranking_snapshot_fingerprint_map,
        terminal_checkpoint_fingerprints=all_terminals,
        sporting_context_fingerprints=sporting_context_fingerprint_map,
        entry_validation_fingerprints=entry_validation_fingerprint_map,
    )
    target_command_rows: list[AuthoritativeSimulationCommandModel] = [
        _retarget_simulation_command_receipt_as_historical(
            row,
            target_branch_id=target_branch_id,
            target_base_revision_id=target_base_revision_id or "",
            position_identity_graph=position_identity_graph,
        )
        for row in source_command_rows
    ]

    merged_simulation_component = simulation_component(
        target_slots,
        target_groups,
        commands=target_command_rows,
        authorities=target_authorities,
        include_commands="commands" in source_slot_component,
        include_authorities="authorities" in source_slot_component,
        schedules=target_schedules,
        include_schedules="schedules" in source_slot_component,
        entry_fields=target_entry_rows,
        include_entry_fields="entry_fields" in source_slot_component,
        wild_card_authorities=target_wc_rows,
        include_wild_card_authorities="wild_card_authorities" in source_slot_component,
        draw_inputs=target_draw_input_rows,
        include_draw_inputs="draw_inputs" in source_slot_component,
        draw_authorities=target_draw_rows,
        include_draw_authorities="draw_authorities" in source_slot_component,
        draw_process_authorities=target_draw_process_rows,
        include_draw_process_authorities=(
            "draw_process_authorities" in source_slot_component
        ),
        draw_revisions=target_draw_revision_rows,
        include_draw_revisions="draw_revisions" in source_slot_component,
        week_tournament_locks=target_week_lock_rows,
        include_week_tournament_locks="week_tournament_locks" in source_slot_component,
    )

    return CoupledPlayerSlotForkRemap(
        sporting_component=sporting_component(
            tuple(target_states),
            tuple(target_contexts),
        ),
        simulation_component=merged_simulation_component,
        result_fingerprints=all_results,
        match_effect_fingerprints=all_effects,
        terminal_checkpoint_fingerprints=all_terminals,
        sporting_fingerprints=sporting_fingerprint_map,
        schedule_fingerprints=schedule_fingerprint_map,
        slot_plan_fingerprints=all_slot_plans,
        group_command_fingerprints=all_group_commands,
        terminal_checkpoint_payloads=all_terminal_payloads,
        week_tournament_lock_fingerprints=week_tournament_lock_fingerprint_map,
        adopted_tournament_authority_fingerprints=(
            adopted_authority_fingerprint_map
        ),
        owned_tournament_fingerprints=dict(v1_source_fingerprint_map),
        sporting_context_fingerprints=sporting_context_fingerprint_map,
        entry_validation_fingerprints=entry_validation_fingerprint_map,
        frozen_fingerprints=dict(target_frozen_fingerprint_map),
    )
