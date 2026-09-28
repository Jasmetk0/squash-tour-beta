"""Saved Revision projection for authoritative slot/match/effect history."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import delete, select

from beta_engine.infrastructure.db.models import (
    AdoptedTournamentAuthorityModel,
    AuthoritativeSimulationCommandModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    WeekSimulationScheduleModel,
    TournamentDrawAuthorityModel,
    TournamentDrawInputAuthorityModel,
    TournamentDrawProcessAuthorityModel,
    TournamentDrawRevisionModel,
    TournamentEntryFieldVersionModel,
    TournamentFormatAuthorityModel,
    TournamentGroupRulesPolicyModel,
    TournamentTopologyAuthorityModel,
    TournamentWildCardAuthorityModel,
    WeekTournamentLockAuthorityModel,
    WorldTourFinalsRaceConfigurationModel,
    WorldTourFinalsRaceSnapshotModel,
    WorldTourFinalsParticipantSelectionConfigurationModel,
    WorldTourFinalsParticipantSelectionSnapshotModel,
)

COMPONENT_KEY = "simulation_slot_match_state"


def _validate_command_rows_shape(rows):
    for row in rows:
        try:
            payload = json.loads(row.result_json)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Saved simulation command receipt JSON is corrupt"
            ) from exc
        if isinstance(payload, dict) and payload.get("schema_version") in {
            "authoritative_simulation_historical_fork_receipt.v1",
            "authoritative_simulation_historical_fork_receipt.v2",
            "authoritative_simulation_historical_fork_receipt.v3",
            "authoritative_simulation_historical_fork_receipt.v4",
            "authoritative_simulation_historical_fork_receipt.v5",
        }:
            expected_retryable = (
                payload.get("schema_version")
                == "authoritative_simulation_historical_fork_receipt.v5"
            )
            if (
                row.status != "historical_fork"
                or payload.get("run_id") != row.run_id
                or payload.get("branch_id") != row.branch_id
                or payload.get("command_id") != row.command_id
                or payload.get("retryable") is not expected_retryable
            ):
                raise ValueError(
                    "Saved historical simulation fork receipt scope is corrupt"
                )
            source_branch_id = payload.get("source_branch_id")
            source_request_fingerprint = payload.get("source_request_fingerprint")
            if not isinstance(source_branch_id, str) or not isinstance(
                source_request_fingerprint, str
            ):
                raise ValueError(
                    "Saved historical simulation fork receipt source identity is corrupt"
                )

            source_result = payload.get("source_result")
            source_evidence_fingerprint = payload.get(
                "source_request_evidence_fingerprint"
            )
            if source_evidence_fingerprint is not None:
                if not isinstance(source_result, dict):
                    raise ValueError(
                        "Saved historical simulation fork receipt source result is corrupt"
                    )
                source_evidence = source_result.get("_request_evidence")
                if not isinstance(source_evidence, dict):
                    raise ValueError(
                        "Saved historical simulation fork receipt request evidence is missing"
                    )
                actual_evidence_fingerprint = hashlib.sha256(
                    json.dumps(
                        source_evidence,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
                if actual_evidence_fingerprint != source_evidence_fingerprint:
                    raise ValueError(
                        "Saved historical simulation fork receipt request evidence is corrupt"
                    )

            historical_schema = payload["schema_version"]
            if historical_schema in {
                "authoritative_simulation_historical_fork_receipt.v2",
                "authoritative_simulation_historical_fork_receipt.v3",
                "authoritative_simulation_historical_fork_receipt.v4",
                "authoritative_simulation_historical_fork_receipt.v5",
            }:
                target_base_revision_id = payload.get("target_base_revision_id")
                if (
                    not isinstance(target_base_revision_id, str)
                    or not target_base_revision_id.strip()
                ):
                    raise ValueError(
                        "Saved historical simulation fork receipt target revision is corrupt"
                    )
                expected_request = {
                    "schema_version": (
                        "authoritative_simulation_historical_fork_request.v5"
                        if historical_schema
                        == "authoritative_simulation_historical_fork_receipt.v5"
                        else (
                            "authoritative_simulation_historical_fork_request.v4"
                            if historical_schema
                            == "authoritative_simulation_historical_fork_receipt.v4"
                            else (
                                "authoritative_simulation_historical_fork_request.v3"
                                if historical_schema
                                == "authoritative_simulation_historical_fork_receipt.v3"
                                else "authoritative_simulation_historical_fork_request.v2"
                            )
                        )
                    ),
                    "run_id": row.run_id,
                    "branch_id": row.branch_id,
                    "command_id": row.command_id,
                    "target_base_revision_id": target_base_revision_id,
                    "source_branch_id": source_branch_id,
                    "source_request_fingerprint": source_request_fingerprint,
                    "source_request_evidence_fingerprint": source_evidence_fingerprint,
                }
                if historical_schema in {
                    "authoritative_simulation_historical_fork_receipt.v3",
                    "authoritative_simulation_historical_fork_receipt.v4",
                    "authoritative_simulation_historical_fork_receipt.v5",
                }:
                    target_evidence = payload.get("target_request_evidence")
                    target_evidence_fingerprint = payload.get(
                        "target_request_evidence_fingerprint"
                    )
                    target_request_fingerprint = payload.get(
                        "target_request_fingerprint"
                    )
                    if (
                        not isinstance(target_evidence, dict)
                        or not isinstance(target_evidence_fingerprint, str)
                        or not isinstance(target_request_fingerprint, str)
                    ):
                        raise ValueError(
                            "Saved historical simulation fork target request evidence is missing"
                        )
                    actual_target_evidence_fingerprint = hashlib.sha256(
                        json.dumps(
                            target_evidence,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest()
                    if (
                        actual_target_evidence_fingerprint
                        != target_evidence_fingerprint
                    ):
                        raise ValueError(
                            "Saved historical simulation fork target request evidence is corrupt"
                        )
                    target_mode = target_evidence.get("mode")
                    target_command = target_evidence.get("command")
                    target_basis = target_evidence.get("opening_position_basis")
                    if (
                        target_evidence.get("schema_version")
                        not in {
                            "authoritative_simulation_request_evidence.v2",
                            "authoritative_simulation_request_evidence.v3",
                        }
                        or target_mode not in {"match", "slot"}
                        or not isinstance(target_command, dict)
                        or not isinstance(target_basis, dict)
                        or target_command.get("run_id") != row.run_id
                        or target_command.get("branch_id") != row.branch_id
                        or target_command.get("command_id") != row.command_id
                        or target_command.get("expected_revision_id")
                        != target_base_revision_id
                    ):
                        raise ValueError(
                            "Saved historical simulation fork target request scope is corrupt"
                        )
                    target_scope = target_basis.get("scope")
                    target_draft = target_basis.get("draft")
                    if (
                        target_scope
                        != [
                            row.run_id,
                            row.branch_id,
                            target_scope[2]
                            if isinstance(target_scope, list)
                            and len(target_scope) == 3
                            and isinstance(target_scope[2], int)
                            else None,
                        ]
                        or target_basis.get("branch_head") != target_base_revision_id
                        or target_draft != [target_base_revision_id, "clean", 0]
                    ):
                        raise ValueError(
                            "Saved historical simulation fork target Position scope is corrupt"
                        )
                    actual_target_position_fingerprint = hashlib.sha256(
                        json.dumps(
                            target_basis,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest()
                    if (
                        target_command.get("expected_position_fingerprint")
                        != actual_target_position_fingerprint
                    ):
                        raise ValueError(
                            "Saved historical simulation fork target Position basis is corrupt"
                        )
                    actual_target_request_fingerprint = hashlib.sha256(
                        json.dumps(
                            {"mode": target_mode, "command": target_command},
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest()
                    if actual_target_request_fingerprint != target_request_fingerprint:
                        raise ValueError(
                            "Saved historical simulation fork target request fingerprint is corrupt"
                        )
                    expected_request.update(
                        {
                            "target_request_evidence_fingerprint": (
                                target_evidence_fingerprint
                            ),
                            "target_request_fingerprint": target_request_fingerprint,
                        }
                    )
                    if (
                        target_evidence.get("schema_version")
                        == "authoritative_simulation_request_evidence.v3"
                    ):
                        target_closing_basis = target_evidence.get(
                            "closing_position_basis"
                        )
                        if not isinstance(target_closing_basis, dict):
                            raise ValueError(
                                "Saved historical simulation fork target closing Position basis is missing"
                            )
                        target_closing_scope = target_closing_basis.get("scope")
                        if (
                            not isinstance(target_closing_scope, list)
                            or len(target_closing_scope) != 3
                            or target_closing_scope[0] != row.run_id
                            or target_closing_scope[1] != row.branch_id
                            or not isinstance(target_closing_scope[2], int)
                        ):
                            raise ValueError(
                                "Saved historical simulation fork target closing Position scope is corrupt"
                            )
                    if historical_schema in {
                        "authoritative_simulation_historical_fork_receipt.v4",
                        "authoritative_simulation_historical_fork_receipt.v5",
                    }:
                        target_result = payload.get("target_result")
                        target_result_fingerprint = payload.get(
                            "target_result_fingerprint"
                        )
                        if (
                            not isinstance(target_result, dict)
                            or not isinstance(target_result_fingerprint, str)
                            or target_evidence.get("schema_version")
                            != "authoritative_simulation_request_evidence.v3"
                        ):
                            raise ValueError(
                                "Saved historical simulation fork target result evidence is missing"
                            )
                        if (
                            target_result.get("run_id") != row.run_id
                            or target_result.get("branch_id") != row.branch_id
                            or target_result.get("position_fingerprint")
                            != hashlib.sha256(
                                json.dumps(
                                    target_evidence["closing_position_basis"],
                                    sort_keys=True,
                                    separators=(",", ":"),
                                ).encode()
                            ).hexdigest()
                        ):
                            raise ValueError(
                                "Saved historical simulation fork target result identity is corrupt"
                            )
                        actual_target_result_fingerprint = hashlib.sha256(
                            json.dumps(
                                target_result,
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode()
                        ).hexdigest()
                        if (
                            actual_target_result_fingerprint
                            != target_result_fingerprint
                        ):
                            raise ValueError(
                                "Saved historical simulation fork target result fingerprint is corrupt"
                            )
                        expected_request["target_result_fingerprint"] = (
                            target_result_fingerprint
                        )
            else:
                expected_request = {
                    "schema_version": "authoritative_simulation_historical_fork_request.v1",
                    "run_id": row.run_id,
                    "branch_id": row.branch_id,
                    "command_id": row.command_id,
                    "source_branch_id": source_branch_id,
                    "source_request_fingerprint": source_request_fingerprint,
                }
            expected = hashlib.sha256(
                json.dumps(
                    expected_request,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            if expected != row.request_fingerprint:
                raise ValueError(
                    "Saved historical simulation fork receipt fingerprint is corrupt"
                )
            continue

        evidence = (
            payload.get("_request_evidence") if isinstance(payload, dict) else None
        )
        if evidence is None:
            # Historical receipts predate self-describing request evidence.
            continue
        schema_version = evidence.get("schema_version")
        if schema_version not in {
            "authoritative_simulation_request_evidence.v1",
            "authoritative_simulation_request_evidence.v2",
            "authoritative_simulation_request_evidence.v3",
        }:
            raise ValueError(
                "Saved simulation command request evidence schema is invalid"
            )
        mode = evidence.get("mode")
        command = evidence.get("command")
        if mode not in {"match", "slot"} or not isinstance(command, dict):
            raise ValueError("Saved simulation command request evidence is invalid")
        if (
            command.get("run_id") != row.run_id
            or command.get("branch_id") != row.branch_id
            or command.get("command_id") != row.command_id
        ):
            raise ValueError(
                "Saved simulation command request evidence scope is corrupt"
            )
        expected = hashlib.sha256(
            json.dumps(
                {"mode": mode, "command": command},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        if expected != row.request_fingerprint:
            raise ValueError(
                "Saved simulation command request evidence fingerprint is corrupt"
            )
        if schema_version in {
            "authoritative_simulation_request_evidence.v2",
            "authoritative_simulation_request_evidence.v3",
        }:
            opening_position_basis = evidence.get("opening_position_basis")
            if not isinstance(opening_position_basis, dict):
                raise ValueError(
                    "Saved simulation command opening Position basis is missing"
                )
            expected_position_fingerprint = command.get("expected_position_fingerprint")
            if (
                not isinstance(expected_position_fingerprint, str)
                or hashlib.sha256(
                    json.dumps(
                        opening_position_basis,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode()
                ).hexdigest()
                != expected_position_fingerprint
            ):
                raise ValueError(
                    "Saved simulation command opening Position basis is corrupt"
                )
            if schema_version == "authoritative_simulation_request_evidence.v3":
                closing_position_basis = evidence.get("closing_position_basis")
                if not isinstance(closing_position_basis, dict):
                    raise ValueError(
                        "Saved simulation command closing Position basis is missing"
                    )
                if row.status != "complete":
                    raise ValueError(
                        "Saved simulation command closing Position evidence requires a complete receipt"
                    )
                result_position_fingerprint = payload.get("position_fingerprint")
                if (
                    not isinstance(result_position_fingerprint, str)
                    or hashlib.sha256(
                        json.dumps(
                            closing_position_basis,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    ).hexdigest()
                    != result_position_fingerprint
                ):
                    raise ValueError(
                        "Saved simulation command closing Position basis is corrupt"
                    )
                closing_scope = closing_position_basis.get("scope")
                if (
                    not isinstance(closing_scope, list)
                    or len(closing_scope) != 3
                    or closing_scope[0] != row.run_id
                    or closing_scope[1] != row.branch_id
                    or not isinstance(closing_scope[2], int)
                ):
                    raise ValueError(
                        "Saved simulation command closing Position scope is corrupt"
                    )


def _validate_entry_field_rows(rows):
    from beta_engine.infrastructure.db.tournament_entry_field import (
        TournamentEntryFieldStore,
    )

    by_event = {}
    for row in rows:
        by_event.setdefault(row.event_id, []).append(row)
    for event_rows in by_event.values():
        ordered = sorted(event_rows, key=lambda row: row.sequence)
        if [row.sequence for row in ordered] != list(range(1, len(ordered) + 1)):
            raise ValueError("Tournament Entry Field version sequence has a gap")
        previous = None
        for index, row in enumerate(ordered):
            field, _ = TournamentEntryFieldStore._load_row(row)
            if index == 0:
                if field.mode != "initial" or row.predecessor_fingerprint is not None:
                    raise ValueError(
                        "First Tournament Entry Field version must be initial"
                    )
            else:
                if field.mode != "pre_draw_repair" or previous is None:
                    raise ValueError(
                        "Later Tournament Entry Field versions must be pre-draw repairs"
                    )
                if row.predecessor_fingerprint != previous.fingerprint:
                    raise ValueError(
                        "Tournament Entry Field predecessor chain is corrupt"
                    )
            previous = field


def _validate_wild_card_rows_shape(rows):
    from beta_engine.domain.tournaments.wild_card_authority import (
        TournamentWildCardAuthority,
    )

    event_keys = [(row.run_id, row.branch_id, row.event_id) for row in rows]
    command_keys = [(row.run_id, row.branch_id, row.command_id) for row in rows]
    if len(event_keys) != len(set(event_keys)):
        raise ValueError(
            "Saved Tournament WC authority contains duplicate event authority"
        )
    if len(command_keys) != len(set(command_keys)):
        raise ValueError(
            "Saved Tournament WC authority contains duplicate command identity"
        )
    for row in rows:
        authority = TournamentWildCardAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.resolved_by_command_id,
            authority.entry_field_fingerprint,
            authority.field_sequence,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.entry_field_fingerprint,
            row.field_sequence,
            row.authority_fingerprint,
        ):
            raise ValueError("Saved Tournament WC authority row is corrupt")


def _validate_draw_input_rows_shape(rows):
    from beta_engine.domain.tournaments.draw_input_authority import (
        TournamentDrawInputAuthority,
    )

    event_keys = [(row.run_id, row.branch_id, row.event_id) for row in rows]
    command_keys = [(row.run_id, row.branch_id, row.command_id) for row in rows]
    if len(event_keys) != len(set(event_keys)):
        raise ValueError(
            "Saved Tournament Draw Input contains duplicate event authority"
        )
    if len(command_keys) != len(set(command_keys)):
        raise ValueError(
            "Saved Tournament Draw Input contains duplicate command identity"
        )
    for row in rows:
        committed = TournamentDrawInputAuthority.model_validate_json(row.payload_json)
        if (
            committed.run_id,
            committed.branch_id,
            committed.event_id,
            committed.committed_by_command_id,
            committed.field_sequence,
            committed.entry_field_fingerprint,
            committed.tournament_ranking_authority_fingerprint,
            committed.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.field_sequence,
            row.entry_field_fingerprint,
            row.ranking_authority_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Saved Tournament Draw Input authority row is corrupt")


def _validate_draw_authority_rows_shape(rows):
    from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority

    event_keys = [(row.run_id, row.branch_id, row.event_id) for row in rows]
    command_keys = [(row.run_id, row.branch_id, row.command_id) for row in rows]
    if len(event_keys) != len(set(event_keys)):
        raise ValueError("Saved Tournament Draw contains duplicate event authority")
    if len(command_keys) != len(set(command_keys)):
        raise ValueError("Saved Tournament Draw contains duplicate command identity")
    for row in rows:
        authority = TournamentDrawAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.generated_by_command_id,
            authority.draw_input_fingerprint,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.draw_input_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Saved Tournament Draw authority row is corrupt")


def _validate_draw_revision_rows_shape(rows):
    from beta_engine.domain.tournaments.draw_revision_authority import (
        TournamentDrawRevision,
    )

    by_event = {}
    for row in rows:
        by_event.setdefault((row.run_id, row.branch_id, row.event_id), []).append(row)
    for event_rows in by_event.values():
        ordered = sorted(event_rows, key=lambda row: row.sequence)
        if [row.sequence for row in ordered] != list(range(1, len(ordered) + 1)):
            raise ValueError("Saved Tournament Draw revision sequence has a gap")
        for row in ordered:
            revision = TournamentDrawRevision.model_validate_json(row.payload_json)
            if (
                revision.run_id,
                revision.branch_id,
                revision.event_id,
                revision.sequence,
                revision.command_id,
                revision.predecessor_draw_fingerprint,
                revision.successor_draw.fingerprint,
                revision.fingerprint,
            ) != (
                row.run_id,
                row.branch_id,
                row.event_id,
                row.sequence,
                row.command_id,
                row.predecessor_draw_fingerprint,
                row.successor_draw_fingerprint,
                row.revision_fingerprint,
            ):
                raise ValueError("Saved Tournament Draw revision row is corrupt")


def _validate_saved_viewer_tournament_chains(component):
    """Validate cross-row tournament identities without consulting live state."""

    draw_inputs = {
        (row["run_id"], row["branch_id"], row["event_id"]): row
        for row in component.get("draw_inputs", ())
    }
    draws = {
        (row["run_id"], row["branch_id"], row["event_id"]): row
        for row in component.get("draw_authorities", ())
    }
    fields_by_key = {}
    for row in component.get("entry_fields", ()):
        fields_by_key[
            (row["run_id"], row["branch_id"], row["event_id"], row["sequence"])
        ] = row
    for key, draw_input in draw_inputs.items():
        field = fields_by_key.get((*key, draw_input["field_sequence"]))
        if (
            field is None
            or field["field_fingerprint"] != draw_input["entry_field_fingerprint"]
        ):
            raise ValueError(
                "Saved Tournament Draw Input references a missing Entry Field"
            )
    for key, draw in draws.items():
        draw_input = draw_inputs.get(key)
        if (
            draw_input is None
            or draw_input["authority_fingerprint"] != draw["draw_input_fingerprint"]
        ):
            raise ValueError("Saved Tournament Draw references a missing Draw Input")
    revisions_by_key = {}
    for row in component.get("draw_revisions", ()):
        revisions_by_key.setdefault(
            (row["run_id"], row["branch_id"], row["event_id"]), []
        ).append(row)
    for key, rows in revisions_by_key.items():
        initial = draws.get(key)
        if initial is None:
            raise ValueError("Saved Tournament Draw revision has no initial Draw")
        predecessor = initial["authority_fingerprint"]
        for row in sorted(rows, key=lambda item: item["sequence"]):
            if row["predecessor_draw_fingerprint"] != predecessor:
                raise ValueError(
                    "Saved Tournament Draw revision predecessor chain is corrupt"
                )
            predecessor = row["successor_draw_fingerprint"]


def _validate_draw_process_rows_shape(rows):
    from beta_engine.domain.tournaments.draw_process_authority import (
        TournamentDrawProcessAuthority,
    )

    event_keys = [(row.run_id, row.branch_id, row.event_id) for row in rows]
    command_keys = [(row.run_id, row.branch_id, row.command_id) for row in rows]
    if len(event_keys) != len(set(event_keys)):
        raise ValueError(
            "Saved Tournament Draw process contains duplicate event authority"
        )
    if len(command_keys) != len(set(command_keys)):
        raise ValueError(
            "Saved Tournament Draw process contains duplicate command identity"
        )
    for row in rows:
        authority = TournamentDrawProcessAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.event_id,
            authority.configured_by_command_id,
            authority.draw_authority_fingerprint,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.event_id,
            row.command_id,
            row.draw_authority_fingerprint,
            row.authority_fingerprint,
        ):
            raise ValueError("Saved Tournament Draw process authority row is corrupt")


def _validate_week_tournament_lock_rows_shape(rows):
    from beta_engine.domain.tournaments.week_tournament_lock import (
        WeekTournamentLockAuthority,
    )

    keys = [(row.run_id, row.branch_id, row.week_ordinal) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Saved Week Tournament Lock contains duplicate week authority")
    for row in rows:
        authority = WeekTournamentLockAuthority.model_validate_json(row.payload_json)
        if (
            authority.run_id,
            authority.branch_id,
            authority.week.ordinal,
            authority.resolved_by_command_id,
            authority.fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.week_ordinal,
            row.command_id,
            row.authority_fingerprint,
        ):
            raise ValueError("Saved Week Tournament Lock authority row is corrupt")


def _validate_finals_authority_rows_shape(
    race_configurations,
    race_snapshots,
    participant_configurations,
    participant_snapshots,
):
    """Validate self-contained immutable Finals authority chains in Saved Revision."""

    from beta_engine.domain.finals import (
        WorldTourFinalsParticipantSelectionConfiguration,
        WorldTourFinalsParticipantSelectionSnapshot,
        WorldTourFinalsRaceConfiguration,
        WorldTourFinalsRaceSnapshot,
    )
    from beta_engine.infrastructure.db.finals_race_authority import (
        WorldTourFinalsRaceAuthorityStore,
    )

    race_configs = {}
    for row in race_configurations:
        key = (row.run_id, row.branch_id, row.target_season_index)
        if key in race_configs:
            raise ValueError("Saved Finals Race configuration identity is duplicated")
        value = WorldTourFinalsRaceConfiguration.model_validate_json(row.payload_json)
        if (
            value.run_id,
            value.branch_id,
            value.target_season_index,
            value.fingerprint,
            value.adopted_by_command_id,
        ) != (
            row.run_id,
            row.branch_id,
            row.target_season_index,
            row.configuration_fingerprint,
            row.adopted_by_command_id,
        ):
            raise ValueError("Saved Finals Race configuration row is corrupt")
        race_configs[key] = value

    races = {}
    for row in race_snapshots:
        key = (row.run_id, row.branch_id, row.target_season_index)
        if key in races:
            raise ValueError("Saved Finals Race snapshot identity is duplicated")
        value = WorldTourFinalsRaceSnapshot.model_validate_json(row.payload_json)
        config = race_configs.get(key)
        if config is None:
            raise ValueError("Saved Finals Race snapshot has no saved configuration")
        if (
            value.run_id,
            value.branch_id,
            value.target_season_index,
            value.fingerprint,
            value.input_fingerprint,
            value.cutoff_week.ordinal,
            row.configuration_fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.target_season_index,
            row.snapshot_fingerprint,
            row.input_fingerprint,
            row.cutoff_week_ordinal,
            config.fingerprint,
        ):
            raise ValueError("Saved Finals Race snapshot row is corrupt")
        WorldTourFinalsRaceAuthorityStore._validate_snapshot_configuration(
            config,
            value,
        )
        races[key] = value

    participant_configs = {}
    for row in participant_configurations:
        key = (row.run_id, row.branch_id, row.target_season_index)
        if key in participant_configs:
            raise ValueError(
                "Saved Finals participant configuration identity is duplicated"
            )
        value = WorldTourFinalsParticipantSelectionConfiguration.model_validate_json(
            row.payload_json
        )
        race = races.get(key)
        if race is None:
            raise ValueError(
                "Saved Finals participant configuration has no saved Race snapshot"
            )
        if (
            value.run_id,
            value.branch_id,
            value.target_season_index,
            value.fingerprint,
            value.race_snapshot_fingerprint,
            value.adopted_by_command_id,
        ) != (
            row.run_id,
            row.branch_id,
            row.target_season_index,
            row.configuration_fingerprint,
            row.race_snapshot_fingerprint,
            row.adopted_by_command_id,
        ):
            raise ValueError("Saved Finals participant configuration row is corrupt")
        if value.race_snapshot_fingerprint != race.fingerprint:
            raise ValueError(
                "Saved Finals participant configuration Race fingerprint is stale"
            )
        participant_configs[key] = value

    participants = {}
    for row in participant_snapshots:
        key = (row.run_id, row.branch_id, row.target_season_index)
        if key in participants:
            raise ValueError("Saved Finals participant snapshot identity is duplicated")
        value = WorldTourFinalsParticipantSelectionSnapshot.model_validate_json(
            row.payload_json
        )
        config = participant_configs.get(key)
        race = races.get(key)
        if config is None or race is None:
            raise ValueError(
                "Saved Finals participant snapshot lacks saved dependency authority"
            )
        if (
            value.run_id,
            value.branch_id,
            value.target_season_index,
            value.fingerprint,
            value.configuration_fingerprint,
            value.race_snapshot_fingerprint,
        ) != (
            row.run_id,
            row.branch_id,
            row.target_season_index,
            row.snapshot_fingerprint,
            row.configuration_fingerprint,
            row.race_snapshot_fingerprint,
        ):
            raise ValueError("Saved Finals participant snapshot row is corrupt")
        if (
            value.configuration_fingerprint != config.fingerprint
            or value.race_snapshot_fingerprint != race.fingerprint
            or value.finals_event_id != config.finals_event_id
            or value.participant_capacity != config.participant_capacity
        ):
            raise ValueError("Saved Finals participant snapshot binding is corrupt")
        participants[key] = value


def _validate_semantics(slots, groups):
    from beta_engine.application.authoritative_slot_matches import (
        AuthoritativeSlotMatchExecutor,
    )

    slot_keys = [(row.week_ordinal, row.slot_id) for row in slots]
    ordinal_keys = [(row.week_ordinal, row.slot_ordinal) for row in slots]
    if len(slot_keys) != len(set(slot_keys)) or len(ordinal_keys) != len(
        set(ordinal_keys)
    ):
        raise ValueError("Simulation slots require unique IDs and global ordinals")
    by_week = {}
    for row in slots:
        by_week.setdefault(row.week_ordinal, []).append(row)
    for week_slots in by_week.values():
        ordered = sorted(week_slots, key=lambda item: item.slot_ordinal)
        ordinals = [item.slot_ordinal for item in ordered]
        if any(ordinal < 1 for ordinal in ordinals) or len(ordinals) != len(
            set(ordinals)
        ):
            raise ValueError(
                "Match Simulation Slot ordinals must be unique positive global ordinals"
            )
        predecessor = None
        for row in ordered:
            plan = AuthoritativeSlotMatchExecutor._load_plan(row)
            start = AuthoritativeSlotMatchExecutor._load_slot_start(row)
            terminal = AuthoritativeSlotMatchExecutor._load_checkpoint(row)
            if (
                plan.run_id,
                plan.branch_id,
                plan.week.ordinal,
                plan.slot_id,
                plan.ordinal,
            ) != (
                row.run_id,
                row.branch_id,
                row.week_ordinal,
                row.slot_id,
                row.slot_ordinal,
            ):
                raise ValueError("Simulation Slot plan scope is corrupt")
            if start.predecessor_checkpoint_fingerprint != predecessor:
                raise ValueError(
                    "Simulation Slot predecessor checkpoint chain is corrupt"
                )
            slot_groups = sorted(
                (
                    group
                    for group in groups
                    if (group.week_ordinal, group.slot_id)
                    == (row.week_ordinal, row.slot_id)
                ),
                key=lambda item: item.group_id,
            )
            group_ids = {group.group_id for group in slot_groups}
            if not group_ids <= set(plan.group_ids) or (
                row.status == "complete" and group_ids != set(plan.group_ids)
            ):
                raise ValueError(
                    "Simulation Slot status and planned group universe differ"
                )
            effects = []
            for group in slot_groups:
                loaded = AuthoritativeSlotMatchExecutor._load_group(group)
                effects.extend(loaded.effects)
            players = {player.player_id: player for player in start.players}
            for effect in sorted(
                effects, key=lambda item: (item.player_id, item.group_id)
            ):
                player = players[effect.player_id]
                if (
                    player.current_form,
                    player.match_sharpness,
                    player.long_term_fatigue,
                ) != (
                    effect.form_before,
                    effect.sharpness_before,
                    effect.fatigue_before,
                ):
                    raise ValueError(
                        "Simulation Slot effects do not rebuild from frozen input"
                    )
                players[effect.player_id] = player.model_copy(
                    update={
                        "current_form": effect.form_after,
                        "match_sharpness": effect.sharpness_after,
                        "long_term_fatigue": effect.fatigue_after,
                    }
                )
            rebuilt = start.model_copy(
                update={
                    "applied_effect_fingerprints": tuple(
                        sorted(effect.fingerprint for effect in effects)
                    ),
                    "players": tuple(
                        players[player_id] for player_id in sorted(players)
                    ),
                }
            )
            if rebuilt != terminal:
                raise ValueError(
                    "Simulation Slot terminal checkpoint is not rebuildable"
                )
            predecessor = terminal.fingerprint
    known = set(slot_keys)
    if any((group.week_ordinal, group.slot_id) not in known for group in groups):
        raise ValueError("Simulation event group has no planned slot")


def _component(
    slots,
    groups,
    commands=(),
    authorities=(),
    *,
    include_commands=True,
    include_authorities=True,
    schedules=(),
    include_schedules=True,
    entry_fields=(),
    include_entry_fields=True,
    group_rules_policies=(),
    include_group_rules_policies=False,
    format_authorities=(),
    include_format_authorities=False,
    topology_authorities=(),
    include_topology_authorities=False,
    finals_race_configurations=(),
    include_finals_race_configurations=False,
    finals_race_snapshots=(),
    include_finals_race_snapshots=False,
    finals_participant_configurations=(),
    include_finals_participant_configurations=False,
    finals_participant_snapshots=(),
    include_finals_participant_snapshots=False,
    wild_card_authorities=(),
    include_wild_card_authorities=False,
    draw_inputs=(),
    include_draw_inputs=True,
    draw_authorities=(),
    include_draw_authorities=True,
    draw_process_authorities=(),
    include_draw_process_authorities=False,
    draw_revisions=(),
    include_draw_revisions=False,
    week_tournament_locks=(),
    include_week_tournament_locks=False,
):
    _validate_semantics(slots, groups)
    _validate_command_rows_shape(commands)
    _validate_entry_field_rows(entry_fields)
    _validate_finals_authority_rows_shape(
        finals_race_configurations,
        finals_race_snapshots,
        finals_participant_configurations,
        finals_participant_snapshots,
    )
    _validate_wild_card_rows_shape(wild_card_authorities)
    _validate_draw_input_rows_shape(draw_inputs)
    _validate_draw_authority_rows_shape(draw_authorities)
    _validate_draw_process_rows_shape(draw_process_authorities)
    _validate_draw_revision_rows_shape(draw_revisions)
    _validate_week_tournament_lock_rows_shape(week_tournament_locks)
    body = {
        "slots": [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "week_ordinal": row.week_ordinal,
                "slot_id": row.slot_id,
                "slot_ordinal": row.slot_ordinal,
                "plan_fingerprint": row.plan_fingerprint,
                "slot_start_fingerprint": row.slot_start_fingerprint,
                "status": row.status,
                "payload_json": row.payload_json,
                "slot_start_checkpoint_json": row.slot_start_checkpoint_json,
                "terminal_checkpoint_json": row.terminal_checkpoint_json,
            }
            for row in slots
        ],
        "groups": [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "week_ordinal": row.week_ordinal,
                "slot_id": row.slot_id,
                "group_id": row.group_id,
                "command_fingerprint": row.command_fingerprint,
                "match_id": row.match_id,
                "match_input_fingerprint": row.match_input_fingerprint,
                "result_fingerprint": row.result_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in groups
        ],
    }
    if include_commands:
        body["commands"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "status": row.status,
                "result_json": row.result_json,
            }
            for row in commands
        ]
    if include_authorities:
        body["authorities"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "week_ordinal": row.week_ordinal,
                "event_id": row.event_id,
                "authority_fingerprint": row.authority_fingerprint,
                "package_json": row.package_json,
            }
            for row in authorities
        ]
    if include_entry_fields:
        body["entry_fields"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "event_id": row.event_id,
                "sequence": row.sequence,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "field_fingerprint": row.field_fingerprint,
                "predecessor_fingerprint": row.predecessor_fingerprint,
                "ranking_authority_fingerprint": row.ranking_authority_fingerprint,
                "applications_fingerprint": row.applications_fingerprint,
                "applications_json": row.applications_json,
                "payload_json": row.payload_json,
            }
            for row in entry_fields
        ]
    if include_group_rules_policies:
        body["group_rules_policies"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "effective_from_season_index": row.effective_from_season_index,
                "command_id": row.command_id,
                "authority_fingerprint": row.authority_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in group_rules_policies
        ]
    if include_format_authorities:
        body["format_authorities"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "event_id": row.event_id,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "authority_fingerprint": row.authority_fingerprint,
                "entry_field_fingerprint": row.entry_field_fingerprint,
                "group_rules_policy_fingerprint": row.group_rules_policy_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in format_authorities
        ]
    if include_topology_authorities:
        body["topology_authorities"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "event_id": row.event_id,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "authority_fingerprint": row.authority_fingerprint,
                "format_authority_fingerprint": row.format_authority_fingerprint,
                "entry_field_fingerprint": row.entry_field_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in topology_authorities
        ]
    if include_finals_race_configurations:
        body["finals_race_configurations"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "target_season_index": row.target_season_index,
                "configuration_fingerprint": row.configuration_fingerprint,
                "adopted_by_command_id": row.adopted_by_command_id,
                "payload_json": row.payload_json,
            }
            for row in finals_race_configurations
        ]
    if include_finals_race_snapshots:
        body["finals_race_snapshots"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "target_season_index": row.target_season_index,
                "snapshot_fingerprint": row.snapshot_fingerprint,
                "configuration_fingerprint": row.configuration_fingerprint,
                "input_fingerprint": row.input_fingerprint,
                "cutoff_week_ordinal": row.cutoff_week_ordinal,
                "payload_json": row.payload_json,
            }
            for row in finals_race_snapshots
        ]
    if include_finals_participant_configurations:
        body["finals_participant_configurations"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "target_season_index": row.target_season_index,
                "configuration_fingerprint": row.configuration_fingerprint,
                "race_snapshot_fingerprint": row.race_snapshot_fingerprint,
                "adopted_by_command_id": row.adopted_by_command_id,
                "payload_json": row.payload_json,
            }
            for row in finals_participant_configurations
        ]
    if include_finals_participant_snapshots:
        body["finals_participant_snapshots"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "target_season_index": row.target_season_index,
                "snapshot_fingerprint": row.snapshot_fingerprint,
                "configuration_fingerprint": row.configuration_fingerprint,
                "race_snapshot_fingerprint": row.race_snapshot_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in finals_participant_snapshots
        ]
    if include_wild_card_authorities:
        body["wild_card_authorities"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "event_id": row.event_id,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "authority_fingerprint": row.authority_fingerprint,
                "entry_field_fingerprint": row.entry_field_fingerprint,
                "field_sequence": row.field_sequence,
                "payload_json": row.payload_json,
            }
            for row in wild_card_authorities
        ]
    if include_draw_inputs:
        body["draw_inputs"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "event_id": row.event_id,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "authority_fingerprint": row.authority_fingerprint,
                "ranking_authority_fingerprint": row.ranking_authority_fingerprint,
                "entry_field_fingerprint": row.entry_field_fingerprint,
                "field_sequence": row.field_sequence,
                "payload_json": row.payload_json,
            }
            for row in draw_inputs
        ]
    if include_draw_authorities:
        body["draw_authorities"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "event_id": row.event_id,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "authority_fingerprint": row.authority_fingerprint,
                "draw_input_fingerprint": row.draw_input_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in draw_authorities
        ]
    if include_draw_revisions:
        body["draw_revisions"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "event_id": row.event_id,
                "sequence": row.sequence,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "revision_fingerprint": row.revision_fingerprint,
                "predecessor_draw_fingerprint": row.predecessor_draw_fingerprint,
                "successor_draw_fingerprint": row.successor_draw_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in draw_revisions
        ]
    if include_draw_process_authorities:
        body["draw_process_authorities"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "event_id": row.event_id,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "authority_fingerprint": row.authority_fingerprint,
                "draw_authority_fingerprint": row.draw_authority_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in draw_process_authorities
        ]
    if include_week_tournament_locks:
        body["week_tournament_locks"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "week_ordinal": row.week_ordinal,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "authority_fingerprint": row.authority_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in week_tournament_locks
        ]
    if include_schedules:
        body["schedules"] = [
            {
                "run_id": r.run_id,
                "branch_id": r.branch_id,
                "week_ordinal": r.week_ordinal,
                "request_id": r.request_id,
                "request_fingerprint": r.request_fingerprint,
                "schedule_fingerprint": r.schedule_fingerprint,
                "payload_json": r.payload_json,
            }
            for r in schedules
        ]
    return {
        "fingerprint": hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        **body,
    }


def capture_saved_simulation_slots(session, payload, *, run_id, branch_id):
    slots = session.scalars(
        select(SimulationSlotModel)
        .where(
            SimulationSlotModel.run_id == run_id,
            SimulationSlotModel.branch_id == branch_id,
        )
        .order_by(SimulationSlotModel.week_ordinal, SimulationSlotModel.slot_ordinal)
    ).all()
    groups = session.scalars(
        select(SimulationEventGroupModel)
        .where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
        )
        .order_by(
            SimulationEventGroupModel.week_ordinal,
            SimulationEventGroupModel.slot_id,
            SimulationEventGroupModel.group_id,
        )
    ).all()
    commands = session.scalars(
        select(AuthoritativeSimulationCommandModel)
        .where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.branch_id == branch_id,
        )
        .order_by(AuthoritativeSimulationCommandModel.command_id)
    ).all()
    authorities = session.scalars(
        select(AdoptedTournamentAuthorityModel)
        .where(
            AdoptedTournamentAuthorityModel.run_id == run_id,
            AdoptedTournamentAuthorityModel.branch_id == branch_id,
        )
        .order_by(AdoptedTournamentAuthorityModel.week_ordinal)
    ).all()
    schedules = session.scalars(
        select(WeekSimulationScheduleModel)
        .where(
            WeekSimulationScheduleModel.run_id == run_id,
            WeekSimulationScheduleModel.branch_id == branch_id,
        )
        .order_by(WeekSimulationScheduleModel.week_ordinal)
    ).all()
    finals_race_configurations = session.scalars(
        select(WorldTourFinalsRaceConfigurationModel)
        .where(
            WorldTourFinalsRaceConfigurationModel.run_id == run_id,
            WorldTourFinalsRaceConfigurationModel.branch_id == branch_id,
        )
        .order_by(WorldTourFinalsRaceConfigurationModel.target_season_index)
    ).all()
    finals_race_snapshots = session.scalars(
        select(WorldTourFinalsRaceSnapshotModel)
        .where(
            WorldTourFinalsRaceSnapshotModel.run_id == run_id,
            WorldTourFinalsRaceSnapshotModel.branch_id == branch_id,
        )
        .order_by(WorldTourFinalsRaceSnapshotModel.target_season_index)
    ).all()
    finals_participant_configurations = session.scalars(
        select(WorldTourFinalsParticipantSelectionConfigurationModel)
        .where(
            WorldTourFinalsParticipantSelectionConfigurationModel.run_id == run_id,
            WorldTourFinalsParticipantSelectionConfigurationModel.branch_id == branch_id,
        )
        .order_by(
            WorldTourFinalsParticipantSelectionConfigurationModel.target_season_index
        )
    ).all()
    finals_participant_snapshots = session.scalars(
        select(WorldTourFinalsParticipantSelectionSnapshotModel)
        .where(
            WorldTourFinalsParticipantSelectionSnapshotModel.run_id == run_id,
            WorldTourFinalsParticipantSelectionSnapshotModel.branch_id == branch_id,
        )
        .order_by(
            WorldTourFinalsParticipantSelectionSnapshotModel.target_season_index
        )
    ).all()
    entry_fields = session.scalars(
        select(TournamentEntryFieldVersionModel)
        .where(
            TournamentEntryFieldVersionModel.run_id == run_id,
            TournamentEntryFieldVersionModel.branch_id == branch_id,
        )
        .order_by(
            TournamentEntryFieldVersionModel.event_id,
            TournamentEntryFieldVersionModel.sequence,
        )
    ).all()
    if entry_fields:
        from beta_engine.infrastructure.db.tournament_entry_field import (
            TournamentEntryFieldStore,
        )

        store = TournamentEntryFieldStore(session)
        for event_id in sorted({row.event_id for row in entry_fields}):
            store.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
    group_rules_policies = session.scalars(
        select(TournamentGroupRulesPolicyModel)
        .where(
            TournamentGroupRulesPolicyModel.run_id == run_id,
            TournamentGroupRulesPolicyModel.branch_id == branch_id,
        )
        .order_by(TournamentGroupRulesPolicyModel.effective_from_season_index)
    ).all()
    if group_rules_policies:
        from beta_engine.infrastructure.db.tournament_group_rules_policy import (
            TournamentGroupRulesPolicyStore,
        )

        TournamentGroupRulesPolicyStore(session).list_versions(
            run_id=run_id,
            branch_id=branch_id,
        )
    format_authorities = session.scalars(
        select(TournamentFormatAuthorityModel)
        .where(
            TournamentFormatAuthorityModel.run_id == run_id,
            TournamentFormatAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentFormatAuthorityModel.event_id)
    ).all()
    if format_authorities:
        from beta_engine.infrastructure.db.tournament_format_authority import (
            TournamentFormatAuthorityStore,
        )

        format_store = TournamentFormatAuthorityStore(session)
        for event_id in sorted({row.event_id for row in format_authorities}):
            format_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    topology_authorities = session.scalars(
        select(TournamentTopologyAuthorityModel)
        .where(
            TournamentTopologyAuthorityModel.run_id == run_id,
            TournamentTopologyAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentTopologyAuthorityModel.event_id)
    ).all()
    if topology_authorities:
        from beta_engine.infrastructure.db.tournament_topology_authority import (
            TournamentTopologyAuthorityStore,
        )

        topology_store = TournamentTopologyAuthorityStore(session)
        for event_id in sorted({row.event_id for row in topology_authorities}):
            topology_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    wild_card_authorities = session.scalars(
        select(TournamentWildCardAuthorityModel)
        .where(
            TournamentWildCardAuthorityModel.run_id == run_id,
            TournamentWildCardAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentWildCardAuthorityModel.event_id)
    ).all()
    if wild_card_authorities:
        from beta_engine.infrastructure.db.tournament_wild_card_authority import (
            TournamentWildCardAuthorityStore,
        )

        wc_store = TournamentWildCardAuthorityStore(session)
        for event_id in sorted({row.event_id for row in wild_card_authorities}):
            wc_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    draw_inputs = session.scalars(
        select(TournamentDrawInputAuthorityModel)
        .where(
            TournamentDrawInputAuthorityModel.run_id == run_id,
            TournamentDrawInputAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentDrawInputAuthorityModel.event_id)
    ).all()
    if draw_inputs:
        from beta_engine.infrastructure.db.tournament_draw_input_authority import (
            TournamentDrawInputAuthorityStore,
        )

        draw_store = TournamentDrawInputAuthorityStore(session)
        for event_id in sorted({row.event_id for row in draw_inputs}):
            draw_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    draw_authorities = session.scalars(
        select(TournamentDrawAuthorityModel)
        .where(
            TournamentDrawAuthorityModel.run_id == run_id,
            TournamentDrawAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentDrawAuthorityModel.event_id)
    ).all()
    if draw_authorities:
        from beta_engine.infrastructure.db.tournament_draw_authority import (
            TournamentDrawAuthorityStore,
        )

        draw_store = TournamentDrawAuthorityStore(session)
        for event_id in sorted({row.event_id for row in draw_authorities}):
            draw_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    draw_revisions = session.scalars(
        select(TournamentDrawRevisionModel)
        .where(
            TournamentDrawRevisionModel.run_id == run_id,
            TournamentDrawRevisionModel.branch_id == branch_id,
        )
        .order_by(
            TournamentDrawRevisionModel.event_id, TournamentDrawRevisionModel.sequence
        )
    ).all()
    if draw_revisions:
        from beta_engine.infrastructure.db.tournament_draw_revision import (
            TournamentDrawRevisionStore,
        )

        revision_store = TournamentDrawRevisionStore(session)
        for event_id in sorted({row.event_id for row in draw_revisions}):
            revision_store.history(
                run_id=run_id, branch_id=branch_id, event_id=event_id
            )
    week_tournament_locks = session.scalars(
        select(WeekTournamentLockAuthorityModel)
        .where(
            WeekTournamentLockAuthorityModel.run_id == run_id,
            WeekTournamentLockAuthorityModel.branch_id == branch_id,
        )
        .order_by(WeekTournamentLockAuthorityModel.week_ordinal)
    ).all()
    if week_tournament_locks:
        from beta_engine.infrastructure.db.week_tournament_lock import (
            WeekTournamentLockStore,
        )

        lock_store = WeekTournamentLockStore(session)
        for row in week_tournament_locks:
            lock_store.get(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=row.week_ordinal,
            )
    draw_process_authorities = session.scalars(
        select(TournamentDrawProcessAuthorityModel)
        .where(
            TournamentDrawProcessAuthorityModel.run_id == run_id,
            TournamentDrawProcessAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentDrawProcessAuthorityModel.event_id)
    ).all()
    if draw_process_authorities:
        from beta_engine.infrastructure.db.tournament_draw_process_authority import (
            TournamentDrawProcessAuthorityStore,
        )

        process_store = TournamentDrawProcessAuthorityStore(session)
        for event_id in sorted({row.event_id for row in draw_process_authorities}):
            process_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    if (
        slots
        or groups
        or commands
        or authorities
        or schedules
        or finals_race_configurations
        or finals_race_snapshots
        or finals_participant_configurations
        or finals_participant_snapshots
        or entry_fields
        or group_rules_policies
        or format_authorities
        or topology_authorities
        or wild_card_authorities
        or draw_inputs
        or draw_authorities
        or draw_process_authorities
        or draw_revisions
        or week_tournament_locks
    ):
        payload["content"][COMPONENT_KEY] = _component(
            slots,
            groups,
            commands,
            authorities,
            schedules=schedules,
            finals_race_configurations=finals_race_configurations,
            include_finals_race_configurations=bool(finals_race_configurations),
            finals_race_snapshots=finals_race_snapshots,
            include_finals_race_snapshots=bool(finals_race_snapshots),
            finals_participant_configurations=finals_participant_configurations,
            include_finals_participant_configurations=bool(
                finals_participant_configurations
            ),
            finals_participant_snapshots=finals_participant_snapshots,
            include_finals_participant_snapshots=bool(finals_participant_snapshots),
            entry_fields=entry_fields,
            include_entry_fields=bool(entry_fields),
            group_rules_policies=group_rules_policies,
            include_group_rules_policies=bool(group_rules_policies),
            format_authorities=format_authorities,
            include_format_authorities=bool(format_authorities),
            topology_authorities=topology_authorities,
            include_topology_authorities=bool(topology_authorities),
            wild_card_authorities=wild_card_authorities,
            include_wild_card_authorities=bool(wild_card_authorities),
            draw_inputs=draw_inputs,
            include_draw_inputs=bool(draw_inputs),
            draw_authorities=draw_authorities,
            include_draw_authorities=bool(draw_authorities),
            draw_process_authorities=draw_process_authorities,
            include_draw_process_authorities=bool(draw_process_authorities),
            draw_revisions=draw_revisions,
            include_draw_revisions=bool(draw_revisions),
            week_tournament_locks=week_tournament_locks,
            include_week_tournament_locks=bool(week_tournament_locks),
        )


def _load(payload, *, run_id, branch_id):
    component = payload.get("content", {}).get(COMPONENT_KEY)
    if component is None:
        return None
    required = {"fingerprint", "slots", "groups"}
    optional = {
        "commands",
        "authorities",
        "schedules",
        "entry_fields",
        "group_rules_policies",
        "format_authorities",
        "topology_authorities",
        "finals_race_configurations",
        "finals_race_snapshots",
        "finals_participant_configurations",
        "finals_participant_snapshots",
        "wild_card_authorities",
        "draw_inputs",
        "draw_authorities",
        "draw_process_authorities",
        "draw_revisions",
        "week_tournament_locks",
    }
    if not required <= set(component) or set(component) - required - optional:
        raise ValueError("Invalid Saved Revision simulation-slot component")
    calculated = _component(
        [SimulationSlotModel(**value) for value in component["slots"]],
        [SimulationEventGroupModel(**value) for value in component["groups"]],
        [
            AuthoritativeSimulationCommandModel(**value)
            for value in component.get("commands", [])
        ],
        [
            AdoptedTournamentAuthorityModel(**value)
            for value in component.get("authorities", [])
        ],
        include_commands="commands" in component,
        include_authorities="authorities" in component,
        schedules=[
            WeekSimulationScheduleModel(**value)
            for value in component.get("schedules", [])
        ],
        include_schedules="schedules" in component,
        entry_fields=[
            TournamentEntryFieldVersionModel(**value)
            for value in component.get("entry_fields", [])
        ],
        include_entry_fields="entry_fields" in component,
        group_rules_policies=[
            TournamentGroupRulesPolicyModel(**value)
            for value in component.get("group_rules_policies", [])
        ],
        include_group_rules_policies="group_rules_policies" in component,
        format_authorities=[
            TournamentFormatAuthorityModel(**value)
            for value in component.get("format_authorities", [])
        ],
        include_format_authorities="format_authorities" in component,
        topology_authorities=[
            TournamentTopologyAuthorityModel(**value)
            for value in component.get("topology_authorities", [])
        ],
        include_topology_authorities="topology_authorities" in component,
        finals_race_configurations=[
            WorldTourFinalsRaceConfigurationModel(**value)
            for value in component.get("finals_race_configurations", [])
        ],
        include_finals_race_configurations="finals_race_configurations" in component,
        finals_race_snapshots=[
            WorldTourFinalsRaceSnapshotModel(**value)
            for value in component.get("finals_race_snapshots", [])
        ],
        include_finals_race_snapshots="finals_race_snapshots" in component,
        finals_participant_configurations=[
            WorldTourFinalsParticipantSelectionConfigurationModel(**value)
            for value in component.get("finals_participant_configurations", [])
        ],
        include_finals_participant_configurations=(
            "finals_participant_configurations" in component
        ),
        finals_participant_snapshots=[
            WorldTourFinalsParticipantSelectionSnapshotModel(**value)
            for value in component.get("finals_participant_snapshots", [])
        ],
        include_finals_participant_snapshots=(
            "finals_participant_snapshots" in component
        ),
        wild_card_authorities=[
            TournamentWildCardAuthorityModel(**value)
            for value in component.get("wild_card_authorities", [])
        ],
        include_wild_card_authorities="wild_card_authorities" in component,
        draw_inputs=[
            TournamentDrawInputAuthorityModel(**value)
            for value in component.get("draw_inputs", [])
        ],
        include_draw_inputs="draw_inputs" in component,
        draw_authorities=[
            TournamentDrawAuthorityModel(**value)
            for value in component.get("draw_authorities", [])
        ],
        include_draw_authorities="draw_authorities" in component,
        draw_process_authorities=[
            TournamentDrawProcessAuthorityModel(**value)
            for value in component.get("draw_process_authorities", [])
        ],
        include_draw_process_authorities="draw_process_authorities" in component,
        draw_revisions=[
            TournamentDrawRevisionModel(**value)
            for value in component.get("draw_revisions", [])
        ],
        include_draw_revisions="draw_revisions" in component,
        week_tournament_locks=[
            WeekTournamentLockAuthorityModel(**value)
            for value in component.get("week_tournament_locks", [])
        ],
        include_week_tournament_locks="week_tournament_locks" in component,
    )
    if calculated["fingerprint"] != component["fingerprint"]:
        raise ValueError("Saved simulation-slot component fingerprint mismatch")
    _validate_saved_viewer_tournament_chains(component)
    if any(
        (value["run_id"], value["branch_id"]) != (run_id, branch_id)
        for kind in (
            set(component)
            & {
                "slots",
                "groups",
                "commands",
                "authorities",
                "schedules",
                "entry_fields",
                "group_rules_policies",
                "format_authorities",
                "topology_authorities",
                "finals_race_configurations",
                "finals_race_snapshots",
                "finals_participant_configurations",
                "finals_participant_snapshots",
                "wild_card_authorities",
                "draw_inputs",
                "draw_authorities",
                "draw_process_authorities",
                "draw_revisions",
                "week_tournament_locks",
            }
        )
        for value in component[kind]
    ):
        raise ValueError("Saved simulation-slot component scope mismatch")
    return component


def load_saved_simulation_slot_component(payload, *, run_id: str, branch_id: str):
    """Expose restore-grade validation to immutable read projections."""

    return _load(payload, run_id=run_id, branch_id=branch_id)


def _validate_saved_entry_fields_against_live_ranking_authority(
    session, component, *, run_id: str, branch_id: str
) -> None:
    """Validate Entry Fields against their actual saved/live upstream authority."""

    values = (component or {}).get("entry_fields", [])
    if not values:
        return

    from beta_engine.domain.finals import (
        WorldTourFinalsParticipantSelectionSnapshot,
    )
    from beta_engine.domain.tournaments.entry_field import TournamentEntryField
    from beta_engine.infrastructure.db.tournament_entry_field import (
        TournamentEntryFieldStore,
    )
    from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
        TournamentRankingSnapshotAuthorityStore,
    )

    participant_snapshots = {
        value["target_season_index"]:
        WorldTourFinalsParticipantSelectionSnapshot.model_validate_json(
            value["payload_json"]
        )
        for value in (component or {}).get("finals_participant_snapshots", [])
    }

    rows = [TournamentEntryFieldVersionModel(**value) for value in values]
    by_event: dict[str, list[TournamentEntryFieldVersionModel]] = {}
    for row in rows:
        by_event.setdefault(row.event_id, []).append(row)

    ranking_store = TournamentRankingSnapshotAuthorityStore(session)
    for event_id, event_rows in sorted(by_event.items()):
        ordered = sorted(event_rows, key=lambda row: row.sequence)
        first = TournamentEntryField.model_validate_json(ordered[0].payload_json)
        if first.source_kind == "finals_participant_selection":
            if first.finals_target_season_index is None:
                raise ValueError(
                    "Saved Finals Entry Field has no target season identity"
                )
            selection = participant_snapshots.get(first.finals_target_season_index)
            if selection is None:
                raise ValueError(
                    "Saved Finals Entry Field references missing saved participant-selection snapshot"
                )
            TournamentEntryFieldStore.validate_rows(
                event_rows,
                finals_selection=selection,
            )
            continue

        authority = ranking_store.get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if authority is None:
            raise ValueError(
                "Saved Tournament Entry Field references missing Tournament "
                "Ranking Snapshot authority"
            )
        TournamentEntryFieldStore.validate_rows(
            event_rows,
            authority=authority,
        )


def _validate_saved_draw_inputs_against_live_dependencies(
    session, component, *, run_id: str, branch_id: str
) -> None:
    draw_values = (component or {}).get("draw_inputs", [])
    if not draw_values:
        return

    entry_values = (component or {}).get("entry_fields", [])
    if not entry_values:
        raise ValueError(
            "Saved Tournament Draw Input requires saved Tournament Entry Field history"
        )

    from beta_engine.infrastructure.db.tournament_draw_input_authority import (
        TournamentDrawInputAuthorityStore,
    )
    from beta_engine.infrastructure.db.tournament_entry_field import (
        TournamentEntryFieldStore,
    )
    from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
        TournamentRankingSnapshotAuthorityStore,
    )

    entry_rows = [TournamentEntryFieldVersionModel(**value) for value in entry_values]
    entry_by_event: dict[str, list[TournamentEntryFieldVersionModel]] = {}
    for row in entry_rows:
        entry_by_event.setdefault(row.event_id, []).append(row)

    from beta_engine.domain.tournaments.wild_card_authority import (
        TournamentWildCardAuthority,
    )

    saved_wc_by_event = {
        value["event_id"]: TournamentWildCardAuthority.model_validate_json(
            value["payload_json"]
        )
        for value in (component or {}).get("wild_card_authorities", [])
    }

    ranking_store = TournamentRankingSnapshotAuthorityStore(session)
    for value in draw_values:
        row = TournamentDrawInputAuthorityModel(**value)
        event_rows = sorted(
            entry_by_event.get(row.event_id, []),
            key=lambda item: item.sequence,
        )
        if not event_rows:
            raise ValueError(
                "Saved Tournament Draw Input references missing Entry Field history"
            )
        authority = ranking_store.get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=row.event_id,
        )
        if authority is None:
            raise ValueError(
                "Saved Tournament Draw Input references missing ranking authority"
            )
        fields = TournamentEntryFieldStore.validate_rows(
            event_rows,
            authority=authority,
        )
        TournamentDrawInputAuthorityStore.validate_row(
            row,
            ranking_authority=authority,
            field=fields[-1],
            field_sequence=len(fields),
            wild_card_authority=saved_wc_by_event.get(row.event_id),
        )


def _validate_saved_draw_authorities_against_target_inputs(
    component,
) -> None:
    draw_values = (component or {}).get("draw_authorities", [])
    if not draw_values:
        return

    input_values = (component or {}).get("draw_inputs", [])
    if not input_values:
        raise ValueError(
            "Saved Tournament Draw authority requires saved Draw Input authority"
        )

    from beta_engine.domain.tournaments.draw_input_authority import (
        TournamentDrawInputAuthority,
    )
    from beta_engine.infrastructure.db.tournament_draw_authority import (
        TournamentDrawAuthorityStore,
    )

    inputs_by_event = {
        value["event_id"]: TournamentDrawInputAuthority.model_validate_json(
            value["payload_json"]
        )
        for value in input_values
    }
    for value in draw_values:
        row = TournamentDrawAuthorityModel(**value)
        draw_input = inputs_by_event.get(row.event_id)
        if draw_input is None:
            raise ValueError(
                "Saved Tournament Draw authority references missing Draw Input"
            )
        TournamentDrawAuthorityStore.validate_row(
            row,
            draw_input=draw_input,
        )


def _validate_saved_draw_revisions_against_target_draw(component) -> None:
    revision_values = (component or {}).get("draw_revisions", [])
    if not revision_values:
        return

    draw_values = (component or {}).get("draw_authorities", [])
    if not draw_values:
        raise ValueError("Saved Draw revisions require saved initial Draw authority")

    from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
    from beta_engine.domain.tournaments.draw_revision_authority import (
        TournamentDrawRevision,
    )

    initial_by_event = {
        value["event_id"]: TournamentDrawAuthority.model_validate_json(
            value["payload_json"]
        )
        for value in draw_values
    }
    by_event = {}
    for value in revision_values:
        by_event.setdefault(value["event_id"], []).append(value)

    for event_id, values in by_event.items():
        predecessor = initial_by_event.get(event_id)
        if predecessor is None:
            raise ValueError("Saved Draw revision references missing initial Draw")
        for expected, value in enumerate(
            sorted(values, key=lambda item: item["sequence"]),
            start=1,
        ):
            revision = TournamentDrawRevision.model_validate_json(value["payload_json"])
            if revision.sequence != expected:
                raise ValueError("Saved Draw revision sequence has a gap")
            if revision.predecessor_draw_fingerprint != predecessor.fingerprint:
                raise ValueError("Saved Draw revision predecessor chain is corrupt")
            predecessor = revision.successor_draw


def _validate_saved_draw_process_against_target_draw(
    component,
) -> None:
    process_values = (component or {}).get("draw_process_authorities", [])
    if not process_values:
        return

    draw_values = (component or {}).get("draw_authorities", [])
    if not draw_values:
        raise ValueError(
            "Saved Tournament Draw process authority requires saved Draw authority"
        )

    from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
    from beta_engine.infrastructure.db.tournament_draw_process_authority import (
        TournamentDrawProcessAuthorityStore,
    )

    draws_by_event = {
        value["event_id"]: TournamentDrawAuthority.model_validate_json(
            value["payload_json"]
        )
        for value in draw_values
    }
    for value in process_values:
        row = TournamentDrawProcessAuthorityModel(**value)
        draw = draws_by_event.get(row.event_id)
        if draw is None:
            raise ValueError(
                "Saved Tournament Draw process authority references missing Draw"
            )
        TournamentDrawProcessAuthorityStore.validate_row(row, draw=draw)


def _live_component_with_saved_shape(
    session,
    *,
    run_id: str,
    branch_id: str,
    shape_hint,
):
    slots = session.scalars(
        select(SimulationSlotModel)
        .where(
            SimulationSlotModel.run_id == run_id,
            SimulationSlotModel.branch_id == branch_id,
        )
        .order_by(SimulationSlotModel.week_ordinal, SimulationSlotModel.slot_ordinal)
    ).all()
    groups = session.scalars(
        select(SimulationEventGroupModel)
        .where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
        )
        .order_by(
            SimulationEventGroupModel.week_ordinal,
            SimulationEventGroupModel.slot_id,
            SimulationEventGroupModel.group_id,
        )
    ).all()
    commands = session.scalars(
        select(AuthoritativeSimulationCommandModel)
        .where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.branch_id == branch_id,
        )
        .order_by(AuthoritativeSimulationCommandModel.command_id)
    ).all()
    authorities = session.scalars(
        select(AdoptedTournamentAuthorityModel)
        .where(
            AdoptedTournamentAuthorityModel.run_id == run_id,
            AdoptedTournamentAuthorityModel.branch_id == branch_id,
        )
        .order_by(AdoptedTournamentAuthorityModel.week_ordinal)
    ).all()
    schedules = session.scalars(
        select(WeekSimulationScheduleModel)
        .where(
            WeekSimulationScheduleModel.run_id == run_id,
            WeekSimulationScheduleModel.branch_id == branch_id,
        )
        .order_by(WeekSimulationScheduleModel.week_ordinal)
    ).all()
    finals_race_configurations = session.scalars(
        select(WorldTourFinalsRaceConfigurationModel)
        .where(
            WorldTourFinalsRaceConfigurationModel.run_id == run_id,
            WorldTourFinalsRaceConfigurationModel.branch_id == branch_id,
        )
        .order_by(WorldTourFinalsRaceConfigurationModel.target_season_index)
    ).all()
    finals_race_snapshots = session.scalars(
        select(WorldTourFinalsRaceSnapshotModel)
        .where(
            WorldTourFinalsRaceSnapshotModel.run_id == run_id,
            WorldTourFinalsRaceSnapshotModel.branch_id == branch_id,
        )
        .order_by(WorldTourFinalsRaceSnapshotModel.target_season_index)
    ).all()
    finals_participant_configurations = session.scalars(
        select(WorldTourFinalsParticipantSelectionConfigurationModel)
        .where(
            WorldTourFinalsParticipantSelectionConfigurationModel.run_id == run_id,
            WorldTourFinalsParticipantSelectionConfigurationModel.branch_id == branch_id,
        )
        .order_by(
            WorldTourFinalsParticipantSelectionConfigurationModel.target_season_index
        )
    ).all()
    finals_participant_snapshots = session.scalars(
        select(WorldTourFinalsParticipantSelectionSnapshotModel)
        .where(
            WorldTourFinalsParticipantSelectionSnapshotModel.run_id == run_id,
            WorldTourFinalsParticipantSelectionSnapshotModel.branch_id == branch_id,
        )
        .order_by(
            WorldTourFinalsParticipantSelectionSnapshotModel.target_season_index
        )
    ).all()
    week_tournament_locks = session.scalars(
        select(WeekTournamentLockAuthorityModel)
        .where(
            WeekTournamentLockAuthorityModel.run_id == run_id,
            WeekTournamentLockAuthorityModel.branch_id == branch_id,
        )
        .order_by(WeekTournamentLockAuthorityModel.week_ordinal)
    ).all()
    entry_fields = session.scalars(
        select(TournamentEntryFieldVersionModel)
        .where(
            TournamentEntryFieldVersionModel.run_id == run_id,
            TournamentEntryFieldVersionModel.branch_id == branch_id,
        )
        .order_by(
            TournamentEntryFieldVersionModel.event_id,
            TournamentEntryFieldVersionModel.sequence,
        )
    ).all()
    group_rules_policies = session.scalars(
        select(TournamentGroupRulesPolicyModel)
        .where(
            TournamentGroupRulesPolicyModel.run_id == run_id,
            TournamentGroupRulesPolicyModel.branch_id == branch_id,
        )
        .order_by(TournamentGroupRulesPolicyModel.effective_from_season_index)
    ).all()
    format_authorities = session.scalars(
        select(TournamentFormatAuthorityModel)
        .where(
            TournamentFormatAuthorityModel.run_id == run_id,
            TournamentFormatAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentFormatAuthorityModel.event_id)
    ).all()
    topology_authorities = session.scalars(
        select(TournamentTopologyAuthorityModel)
        .where(
            TournamentTopologyAuthorityModel.run_id == run_id,
            TournamentTopologyAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentTopologyAuthorityModel.event_id)
    ).all()
    wild_cards = session.scalars(
        select(TournamentWildCardAuthorityModel)
        .where(
            TournamentWildCardAuthorityModel.run_id == run_id,
            TournamentWildCardAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentWildCardAuthorityModel.event_id)
    ).all()
    draw_inputs = session.scalars(
        select(TournamentDrawInputAuthorityModel)
        .where(
            TournamentDrawInputAuthorityModel.run_id == run_id,
            TournamentDrawInputAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentDrawInputAuthorityModel.event_id)
    ).all()
    draws = session.scalars(
        select(TournamentDrawAuthorityModel)
        .where(
            TournamentDrawAuthorityModel.run_id == run_id,
            TournamentDrawAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentDrawAuthorityModel.event_id)
    ).all()
    processes = session.scalars(
        select(TournamentDrawProcessAuthorityModel)
        .where(
            TournamentDrawProcessAuthorityModel.run_id == run_id,
            TournamentDrawProcessAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentDrawProcessAuthorityModel.event_id)
    ).all()
    revisions = session.scalars(
        select(TournamentDrawRevisionModel)
        .where(
            TournamentDrawRevisionModel.run_id == run_id,
            TournamentDrawRevisionModel.branch_id == branch_id,
        )
        .order_by(
            TournamentDrawRevisionModel.event_id,
            TournamentDrawRevisionModel.sequence,
        )
    ).all()

    any_live = any(
        (
            slots,
            groups,
            commands,
            authorities,
            schedules,
            finals_race_configurations,
            finals_race_snapshots,
            finals_participant_configurations,
            finals_participant_snapshots,
            week_tournament_locks,
            entry_fields,
            group_rules_policies,
            format_authorities,
            topology_authorities,
            wild_cards,
            draw_inputs,
            draws,
            processes,
            revisions,
        )
    )
    if shape_hint is None and not any_live:
        return None
    shape_hint = shape_hint or {}
    return _component(
        slots,
        groups,
        commands,
        authorities,
        include_commands="commands" in shape_hint,
        include_authorities="authorities" in shape_hint,
        schedules=schedules,
        include_schedules="schedules" in shape_hint,
        finals_race_configurations=finals_race_configurations,
        include_finals_race_configurations="finals_race_configurations" in shape_hint,
        finals_race_snapshots=finals_race_snapshots,
        include_finals_race_snapshots="finals_race_snapshots" in shape_hint,
        finals_participant_configurations=finals_participant_configurations,
        include_finals_participant_configurations=(
            "finals_participant_configurations" in shape_hint
        ),
        finals_participant_snapshots=finals_participant_snapshots,
        include_finals_participant_snapshots=(
            "finals_participant_snapshots" in shape_hint
        ),
        week_tournament_locks=week_tournament_locks,
        include_week_tournament_locks="week_tournament_locks" in shape_hint,
        entry_fields=entry_fields,
        include_entry_fields="entry_fields" in shape_hint,
        group_rules_policies=group_rules_policies,
        include_group_rules_policies="group_rules_policies" in shape_hint,
        format_authorities=format_authorities,
        include_format_authorities="format_authorities" in shape_hint,
        topology_authorities=topology_authorities,
        include_topology_authorities="topology_authorities" in shape_hint,
        wild_card_authorities=wild_cards,
        include_wild_card_authorities="wild_card_authorities" in shape_hint,
        draw_inputs=draw_inputs,
        include_draw_inputs="draw_inputs" in shape_hint,
        draw_authorities=draws,
        include_draw_authorities="draw_authorities" in shape_hint,
        draw_process_authorities=processes,
        include_draw_process_authorities="draw_process_authorities" in shape_hint,
        draw_revisions=revisions,
        include_draw_revisions="draw_revisions" in shape_hint,
    )


def restore_saved_simulation_slots(
    session, *, current_payload, target_payload, run_id, branch_id
):
    expected = _load(current_payload, run_id=run_id, branch_id=branch_id)
    target = _load(target_payload, run_id=run_id, branch_id=branch_id)
    _validate_saved_entry_fields_against_live_ranking_authority(
        session,
        target,
        run_id=run_id,
        branch_id=branch_id,
    )
    _validate_saved_draw_inputs_against_live_dependencies(
        session,
        target,
        run_id=run_id,
        branch_id=branch_id,
    )
    _validate_saved_draw_authorities_against_target_inputs(target)
    _validate_saved_draw_revisions_against_target_draw(target)
    _validate_saved_draw_process_against_target_draw(target)
    live_slots = session.scalars(
        select(SimulationSlotModel)
        .where(
            SimulationSlotModel.run_id == run_id,
            SimulationSlotModel.branch_id == branch_id,
        )
        .order_by(SimulationSlotModel.week_ordinal, SimulationSlotModel.slot_ordinal)
    ).all()
    live_groups = session.scalars(
        select(SimulationEventGroupModel)
        .where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
        )
        .order_by(
            SimulationEventGroupModel.week_ordinal,
            SimulationEventGroupModel.slot_id,
            SimulationEventGroupModel.group_id,
        )
    ).all()
    live_commands = session.scalars(
        select(AuthoritativeSimulationCommandModel)
        .where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.branch_id == branch_id,
        )
        .order_by(AuthoritativeSimulationCommandModel.command_id)
    ).all()
    live_authorities = session.scalars(
        select(AdoptedTournamentAuthorityModel)
        .where(
            AdoptedTournamentAuthorityModel.run_id == run_id,
            AdoptedTournamentAuthorityModel.branch_id == branch_id,
        )
        .order_by(AdoptedTournamentAuthorityModel.week_ordinal)
    ).all()
    live_schedules = session.scalars(
        select(WeekSimulationScheduleModel)
        .where(
            WeekSimulationScheduleModel.run_id == run_id,
            WeekSimulationScheduleModel.branch_id == branch_id,
        )
        .order_by(WeekSimulationScheduleModel.week_ordinal)
    ).all()
    live_finals_race_configurations = session.scalars(
        select(WorldTourFinalsRaceConfigurationModel)
        .where(
            WorldTourFinalsRaceConfigurationModel.run_id == run_id,
            WorldTourFinalsRaceConfigurationModel.branch_id == branch_id,
        )
        .order_by(WorldTourFinalsRaceConfigurationModel.target_season_index)
    ).all()
    live_finals_race_snapshots = session.scalars(
        select(WorldTourFinalsRaceSnapshotModel)
        .where(
            WorldTourFinalsRaceSnapshotModel.run_id == run_id,
            WorldTourFinalsRaceSnapshotModel.branch_id == branch_id,
        )
        .order_by(WorldTourFinalsRaceSnapshotModel.target_season_index)
    ).all()
    live_finals_participant_configurations = session.scalars(
        select(WorldTourFinalsParticipantSelectionConfigurationModel)
        .where(
            WorldTourFinalsParticipantSelectionConfigurationModel.run_id == run_id,
            WorldTourFinalsParticipantSelectionConfigurationModel.branch_id == branch_id,
        )
        .order_by(
            WorldTourFinalsParticipantSelectionConfigurationModel.target_season_index
        )
    ).all()
    live_finals_participant_snapshots = session.scalars(
        select(WorldTourFinalsParticipantSelectionSnapshotModel)
        .where(
            WorldTourFinalsParticipantSelectionSnapshotModel.run_id == run_id,
            WorldTourFinalsParticipantSelectionSnapshotModel.branch_id == branch_id,
        )
        .order_by(
            WorldTourFinalsParticipantSelectionSnapshotModel.target_season_index
        )
    ).all()
    live_week_tournament_locks = session.scalars(
        select(WeekTournamentLockAuthorityModel)
        .where(
            WeekTournamentLockAuthorityModel.run_id == run_id,
            WeekTournamentLockAuthorityModel.branch_id == branch_id,
        )
        .order_by(WeekTournamentLockAuthorityModel.week_ordinal)
    ).all()
    if live_week_tournament_locks:
        from beta_engine.infrastructure.db.week_tournament_lock import (
            WeekTournamentLockStore,
        )

        lock_store = WeekTournamentLockStore(session)
        for row in live_week_tournament_locks:
            lock_store.get(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=row.week_ordinal,
            )
    live_entry_fields = session.scalars(
        select(TournamentEntryFieldVersionModel)
        .where(
            TournamentEntryFieldVersionModel.run_id == run_id,
            TournamentEntryFieldVersionModel.branch_id == branch_id,
        )
        .order_by(
            TournamentEntryFieldVersionModel.event_id,
            TournamentEntryFieldVersionModel.sequence,
        )
    ).all()
    if live_entry_fields:
        from beta_engine.infrastructure.db.tournament_entry_field import (
            TournamentEntryFieldStore,
        )

        store = TournamentEntryFieldStore(session)
        for event_id in sorted({row.event_id for row in live_entry_fields}):
            store.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
    live_group_rules_policies = session.scalars(
        select(TournamentGroupRulesPolicyModel)
        .where(
            TournamentGroupRulesPolicyModel.run_id == run_id,
            TournamentGroupRulesPolicyModel.branch_id == branch_id,
        )
        .order_by(TournamentGroupRulesPolicyModel.effective_from_season_index)
    ).all()
    if live_group_rules_policies:
        from beta_engine.infrastructure.db.tournament_group_rules_policy import (
            TournamentGroupRulesPolicyStore,
        )

        TournamentGroupRulesPolicyStore(session).list_versions(
            run_id=run_id,
            branch_id=branch_id,
        )
    live_format_authorities = session.scalars(
        select(TournamentFormatAuthorityModel)
        .where(
            TournamentFormatAuthorityModel.run_id == run_id,
            TournamentFormatAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentFormatAuthorityModel.event_id)
    ).all()
    if live_format_authorities:
        from beta_engine.infrastructure.db.tournament_format_authority import (
            TournamentFormatAuthorityStore,
        )

        format_store = TournamentFormatAuthorityStore(session)
        for event_id in sorted({row.event_id for row in live_format_authorities}):
            format_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    live_topology_authorities = session.scalars(
        select(TournamentTopologyAuthorityModel)
        .where(
            TournamentTopologyAuthorityModel.run_id == run_id,
            TournamentTopologyAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentTopologyAuthorityModel.event_id)
    ).all()
    if live_topology_authorities:
        from beta_engine.infrastructure.db.tournament_topology_authority import (
            TournamentTopologyAuthorityStore,
        )

        topology_store = TournamentTopologyAuthorityStore(session)
        for event_id in sorted({row.event_id for row in live_topology_authorities}):
            topology_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    live_wild_card_authorities = session.scalars(
        select(TournamentWildCardAuthorityModel)
        .where(
            TournamentWildCardAuthorityModel.run_id == run_id,
            TournamentWildCardAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentWildCardAuthorityModel.event_id)
    ).all()
    if live_wild_card_authorities:
        from beta_engine.infrastructure.db.tournament_wild_card_authority import (
            TournamentWildCardAuthorityStore,
        )

        wc_store = TournamentWildCardAuthorityStore(session)
        for event_id in sorted({row.event_id for row in live_wild_card_authorities}):
            wc_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    live_draw_inputs = session.scalars(
        select(TournamentDrawInputAuthorityModel)
        .where(
            TournamentDrawInputAuthorityModel.run_id == run_id,
            TournamentDrawInputAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentDrawInputAuthorityModel.event_id)
    ).all()
    if live_draw_inputs:
        from beta_engine.infrastructure.db.tournament_draw_input_authority import (
            TournamentDrawInputAuthorityStore,
        )

        draw_store = TournamentDrawInputAuthorityStore(session)
        for event_id in sorted({row.event_id for row in live_draw_inputs}):
            draw_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    live_draw_authorities = session.scalars(
        select(TournamentDrawAuthorityModel)
        .where(
            TournamentDrawAuthorityModel.run_id == run_id,
            TournamentDrawAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentDrawAuthorityModel.event_id)
    ).all()
    if live_draw_authorities:
        from beta_engine.infrastructure.db.tournament_draw_authority import (
            TournamentDrawAuthorityStore,
        )

        draw_store = TournamentDrawAuthorityStore(session)
        for event_id in sorted({row.event_id for row in live_draw_authorities}):
            draw_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    live_draw_revisions = session.scalars(
        select(TournamentDrawRevisionModel)
        .where(
            TournamentDrawRevisionModel.run_id == run_id,
            TournamentDrawRevisionModel.branch_id == branch_id,
        )
        .order_by(
            TournamentDrawRevisionModel.event_id, TournamentDrawRevisionModel.sequence
        )
    ).all()
    if live_draw_revisions:
        from beta_engine.infrastructure.db.tournament_draw_revision import (
            TournamentDrawRevisionStore,
        )

        revision_store = TournamentDrawRevisionStore(session)
        for event_id in sorted({row.event_id for row in live_draw_revisions}):
            revision_store.history(
                run_id=run_id, branch_id=branch_id, event_id=event_id
            )
    live_draw_process_authorities = session.scalars(
        select(TournamentDrawProcessAuthorityModel)
        .where(
            TournamentDrawProcessAuthorityModel.run_id == run_id,
            TournamentDrawProcessAuthorityModel.branch_id == branch_id,
        )
        .order_by(TournamentDrawProcessAuthorityModel.event_id)
    ).all()
    if live_draw_process_authorities:
        from beta_engine.infrastructure.db.tournament_draw_process_authority import (
            TournamentDrawProcessAuthorityStore,
        )

        process_store = TournamentDrawProcessAuthorityStore(session)
        for event_id in sorted({row.event_id for row in live_draw_process_authorities}):
            process_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    live = (
        _component(
            live_slots,
            live_groups,
            live_commands,
            live_authorities,
            include_commands=(
                bool(live_commands)
                or bool(expected is not None and "commands" in expected)
            ),
            include_authorities=(
                bool(live_authorities)
                or bool(expected is not None and "authorities" in expected)
            ),
            schedules=live_schedules,
            include_schedules=(
                bool(live_schedules)
                or bool(expected is not None and "schedules" in expected)
            ),
            finals_race_configurations=live_finals_race_configurations,
            include_finals_race_configurations=(
                bool(live_finals_race_configurations)
                or bool(expected is not None and "finals_race_configurations" in expected)
            ),
            finals_race_snapshots=live_finals_race_snapshots,
            include_finals_race_snapshots=(
                bool(live_finals_race_snapshots)
                or bool(expected is not None and "finals_race_snapshots" in expected)
            ),
            finals_participant_configurations=live_finals_participant_configurations,
            include_finals_participant_configurations=(
                bool(live_finals_participant_configurations)
                or bool(
                    expected is not None
                    and "finals_participant_configurations" in expected
                )
            ),
            finals_participant_snapshots=live_finals_participant_snapshots,
            include_finals_participant_snapshots=(
                bool(live_finals_participant_snapshots)
                or bool(expected is not None and "finals_participant_snapshots" in expected)
            ),
            week_tournament_locks=live_week_tournament_locks,
            include_week_tournament_locks=(
                bool(live_week_tournament_locks)
                or bool(expected is not None and "week_tournament_locks" in expected)
            ),
            entry_fields=live_entry_fields,
            include_entry_fields=(
                bool(live_entry_fields)
                or bool(expected is not None and "entry_fields" in expected)
            ),
            group_rules_policies=live_group_rules_policies,
            include_group_rules_policies=(
                bool(live_group_rules_policies)
                or bool(expected is not None and "group_rules_policies" in expected)
            ),
            format_authorities=live_format_authorities,
            include_format_authorities=(
                bool(live_format_authorities)
                or bool(expected is not None and "format_authorities" in expected)
            ),
            topology_authorities=live_topology_authorities,
            include_topology_authorities=(
                bool(live_topology_authorities)
                or bool(expected is not None and "topology_authorities" in expected)
            ),
            wild_card_authorities=live_wild_card_authorities,
            include_wild_card_authorities=(
                bool(live_wild_card_authorities)
                or bool(expected is not None and "wild_card_authorities" in expected)
            ),
            draw_inputs=live_draw_inputs,
            include_draw_inputs=(
                bool(live_draw_inputs)
                or bool(expected is not None and "draw_inputs" in expected)
            ),
            draw_authorities=live_draw_authorities,
            include_draw_authorities=(
                bool(live_draw_authorities)
                or bool(expected is not None and "draw_authorities" in expected)
            ),
            draw_process_authorities=live_draw_process_authorities,
            include_draw_process_authorities=(
                bool(live_draw_process_authorities)
                or bool(expected is not None and "draw_process_authorities" in expected)
            ),
            draw_revisions=live_draw_revisions,
            include_draw_revisions=(
                bool(live_draw_revisions)
                or bool(expected is not None and "draw_revisions" in expected)
            ),
        )
        if live_slots
        or live_groups
        or live_commands
        or live_authorities
        or live_schedules
        or live_finals_race_configurations
        or live_finals_race_snapshots
        or live_finals_participant_configurations
        or live_finals_participant_snapshots
        or live_week_tournament_locks
        or live_entry_fields
        or live_group_rules_policies
        or live_format_authorities
        or live_topology_authorities
        or live_wild_card_authorities
        or live_draw_inputs
        or live_draw_authorities
        or live_draw_process_authorities
        or live_draw_revisions
        else None
    )
    if (live or {}).get("fingerprint") != (expected or {}).get("fingerprint"):
        raise ValueError("Live simulation-slot state differs from saved head")
    session.execute(
        delete(TournamentTopologyAuthorityModel).where(
            TournamentTopologyAuthorityModel.run_id == run_id,
            TournamentTopologyAuthorityModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(TournamentFormatAuthorityModel).where(
            TournamentFormatAuthorityModel.run_id == run_id,
            TournamentFormatAuthorityModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(TournamentDrawRevisionModel).where(
            TournamentDrawRevisionModel.run_id == run_id,
            TournamentDrawRevisionModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(TournamentDrawProcessAuthorityModel).where(
            TournamentDrawProcessAuthorityModel.run_id == run_id,
            TournamentDrawProcessAuthorityModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(TournamentDrawAuthorityModel).where(
            TournamentDrawAuthorityModel.run_id == run_id,
            TournamentDrawAuthorityModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(TournamentWildCardAuthorityModel).where(
            TournamentWildCardAuthorityModel.run_id == run_id,
            TournamentWildCardAuthorityModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(TournamentDrawInputAuthorityModel).where(
            TournamentDrawInputAuthorityModel.run_id == run_id,
            TournamentDrawInputAuthorityModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(TournamentEntryFieldVersionModel).where(
            TournamentEntryFieldVersionModel.run_id == run_id,
            TournamentEntryFieldVersionModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(TournamentGroupRulesPolicyModel).where(
            TournamentGroupRulesPolicyModel.run_id == run_id,
            TournamentGroupRulesPolicyModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(WorldTourFinalsParticipantSelectionSnapshotModel).where(
            WorldTourFinalsParticipantSelectionSnapshotModel.run_id == run_id,
            WorldTourFinalsParticipantSelectionSnapshotModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(WorldTourFinalsParticipantSelectionConfigurationModel).where(
            WorldTourFinalsParticipantSelectionConfigurationModel.run_id == run_id,
            WorldTourFinalsParticipantSelectionConfigurationModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(WorldTourFinalsRaceSnapshotModel).where(
            WorldTourFinalsRaceSnapshotModel.run_id == run_id,
            WorldTourFinalsRaceSnapshotModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(WorldTourFinalsRaceConfigurationModel).where(
            WorldTourFinalsRaceConfigurationModel.run_id == run_id,
            WorldTourFinalsRaceConfigurationModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(WeekTournamentLockAuthorityModel).where(
            WeekTournamentLockAuthorityModel.run_id == run_id,
            WeekTournamentLockAuthorityModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(WeekSimulationScheduleModel).where(
            WeekSimulationScheduleModel.run_id == run_id,
            WeekSimulationScheduleModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(AdoptedTournamentAuthorityModel).where(
            AdoptedTournamentAuthorityModel.run_id == run_id,
            AdoptedTournamentAuthorityModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(AuthoritativeSimulationCommandModel).where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(SimulationEventGroupModel).where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(SimulationSlotModel).where(
            SimulationSlotModel.run_id == run_id,
            SimulationSlotModel.branch_id == branch_id,
        )
    )
    for value in (target or {}).get("slots", []):
        session.add(SimulationSlotModel(**value))
    for value in (target or {}).get("groups", []):
        session.add(SimulationEventGroupModel(**value))
    for value in (target or {}).get("commands", []):
        session.add(AuthoritativeSimulationCommandModel(**value))
    for value in (target or {}).get("authorities", []):
        session.add(AdoptedTournamentAuthorityModel(**value))
    for value in (target or {}).get("schedules", []):
        session.add(WeekSimulationScheduleModel(**value))
    for value in (target or {}).get("week_tournament_locks", []):
        session.add(WeekTournamentLockAuthorityModel(**value))
    for value in (target or {}).get("finals_race_configurations", []):
        session.add(WorldTourFinalsRaceConfigurationModel(**value))
    for value in (target or {}).get("finals_race_snapshots", []):
        session.add(WorldTourFinalsRaceSnapshotModel(**value))
    for value in (target or {}).get("finals_participant_configurations", []):
        session.add(WorldTourFinalsParticipantSelectionConfigurationModel(**value))
    for value in (target or {}).get("finals_participant_snapshots", []):
        session.add(WorldTourFinalsParticipantSelectionSnapshotModel(**value))
    for value in (target or {}).get("group_rules_policies", []):
        session.add(TournamentGroupRulesPolicyModel(**value))
    for value in (target or {}).get("entry_fields", []):
        session.add(TournamentEntryFieldVersionModel(**value))
    for value in (target or {}).get("format_authorities", []):
        session.add(TournamentFormatAuthorityModel(**value))
    for value in (target or {}).get("topology_authorities", []):
        session.add(TournamentTopologyAuthorityModel(**value))
    for value in (target or {}).get("wild_card_authorities", []):
        session.add(TournamentWildCardAuthorityModel(**value))
    for value in (target or {}).get("draw_inputs", []):
        session.add(TournamentDrawInputAuthorityModel(**value))
    for value in (target or {}).get("draw_authorities", []):
        session.add(TournamentDrawAuthorityModel(**value))
    for value in (target or {}).get("draw_process_authorities", []):
        session.add(TournamentDrawProcessAuthorityModel(**value))
    for value in (target or {}).get("draw_revisions", []):
        session.add(TournamentDrawRevisionModel(**value))
    session.flush()
    target_week_locks = (target or {}).get("week_tournament_locks", [])
    if target_week_locks:
        from beta_engine.infrastructure.db.week_tournament_lock import (
            WeekTournamentLockStore,
        )

        lock_store = WeekTournamentLockStore(session)
        for value in target_week_locks:
            lock_store.get(
                run_id=run_id,
                branch_id=branch_id,
                week_ordinal=value["week_ordinal"],
            )
    target_entry_fields = (target or {}).get("entry_fields", [])
    if target_entry_fields:
        from beta_engine.infrastructure.db.tournament_entry_field import (
            TournamentEntryFieldStore,
        )

        store = TournamentEntryFieldStore(session)
        for event_id in sorted({value["event_id"] for value in target_entry_fields}):
            store.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
    target_group_rules = (target or {}).get("group_rules_policies", [])
    if target_group_rules:
        from beta_engine.infrastructure.db.tournament_group_rules_policy import (
            TournamentGroupRulesPolicyStore,
        )

        TournamentGroupRulesPolicyStore(session).list_versions(
            run_id=run_id,
            branch_id=branch_id,
        )
    target_formats = (target or {}).get("format_authorities", [])
    if target_formats:
        from beta_engine.infrastructure.db.tournament_format_authority import (
            TournamentFormatAuthorityStore,
        )

        format_store = TournamentFormatAuthorityStore(session)
        for event_id in sorted({value["event_id"] for value in target_formats}):
            format_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    target_topologies = (target or {}).get("topology_authorities", [])
    if target_topologies:
        from beta_engine.infrastructure.db.tournament_topology_authority import (
            TournamentTopologyAuthorityStore,
        )

        topology_store = TournamentTopologyAuthorityStore(session)
        for event_id in sorted({value["event_id"] for value in target_topologies}):
            topology_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    target_wild_cards = (target or {}).get("wild_card_authorities", [])
    if target_wild_cards:
        from beta_engine.infrastructure.db.tournament_wild_card_authority import (
            TournamentWildCardAuthorityStore,
        )

        wc_store = TournamentWildCardAuthorityStore(session)
        for event_id in sorted({value["event_id"] for value in target_wild_cards}):
            wc_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    target_draw_inputs = (target or {}).get("draw_inputs", [])
    if target_draw_inputs:
        from beta_engine.infrastructure.db.tournament_draw_input_authority import (
            TournamentDrawInputAuthorityStore,
        )

        input_store = TournamentDrawInputAuthorityStore(session)
        for event_id in sorted({value["event_id"] for value in target_draw_inputs}):
            input_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    target_draw_authorities = (target or {}).get("draw_authorities", [])
    if target_draw_authorities:
        from beta_engine.infrastructure.db.tournament_draw_authority import (
            TournamentDrawAuthorityStore,
        )

        draw_store = TournamentDrawAuthorityStore(session)
        for event_id in sorted(
            {value["event_id"] for value in target_draw_authorities}
        ):
            draw_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    target_draw_process = (target or {}).get("draw_process_authorities", [])
    if target_draw_process:
        from beta_engine.infrastructure.db.tournament_draw_process_authority import (
            TournamentDrawProcessAuthorityStore,
        )

        process_store = TournamentDrawProcessAuthorityStore(session)
        for event_id in sorted({value["event_id"] for value in target_draw_process}):
            process_store.get(run_id=run_id, branch_id=branch_id, event_id=event_id)
    target_draw_revisions = (target or {}).get("draw_revisions", [])
    if target_draw_revisions:
        from beta_engine.infrastructure.db.tournament_draw_revision import (
            TournamentDrawRevisionStore,
        )

        revision_store = TournamentDrawRevisionStore(session)
        for event_id in sorted({value["event_id"] for value in target_draw_revisions}):
            revision_store.history(
                run_id=run_id, branch_id=branch_id, event_id=event_id
            )

    installed_component = _live_component_with_saved_shape(
        session,
        run_id=run_id,
        branch_id=branch_id,
        shape_hint=target,
    )
    if (installed_component or {}).get("fingerprint") != (target or {}).get(
        "fingerprint"
    ):
        raise ValueError(
            "Installed simulation-slot state differs from Saved Revision target"
        )
