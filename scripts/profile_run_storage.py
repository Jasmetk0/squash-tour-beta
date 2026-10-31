#!/usr/bin/env python3
"""
Diagnostic command-line tool to profile SQLite Run storage.
"""

import argparse
import json
import platform
import sqlite3
import sys
import time
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = "1.0"

def get_file_size(path: Path) -> int | None:
    try:
        if path.exists() and path.is_file():
            return path.stat().st_size
        return None
    except OSError:
        return None

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile a Squash Engine SQLite database to report Run storage usage."
    )
    parser.add_argument("--database", required=True, type=str, help="Path to the SQLite database")
    parser.add_argument("--run-id", type=str, help="Optional specific Run ID to filter scoped tables")
    parser.add_argument("--label", type=str, help="Optional label to include in the output JSON")
    parser.add_argument("--output", type=str, help="Optional path to output the JSON report. Overwrites the file if it exists, but will fail if it targets the DB or its sidecars.")

    args = parser.parse_args()

    db_path = Path(args.database).resolve()
    if not db_path.exists() or not db_path.is_file():
        print(f"Error: Database file does not exist or is not a file: {db_path}", file=sys.stderr)
        return 1

    wal_path = db_path.with_name(db_path.name + "-wal")
    shm_path = db_path.with_name(db_path.name + "-shm")

    output_path = None
    if args.output:
        output_path = Path(args.output).resolve()
        if output_path in (db_path, wal_path, shm_path):
            print("Error: Output path cannot overwrite the database or its sidecar files.", file=sys.stderr)
            return 1
        if output_path.exists():
            print("Error: Output file already exists.", file=sys.stderr)
            return 1
            print("Error: Output path cannot overwrite the database or its sidecar files.", file=sys.stderr)
            return 1

    start_time = time.time()
    observation_start_utc = datetime.now(UTC).isoformat()

    # 1. Connect safely using mode=ro URI to prevent creation or mutation
    uri_path = urllib.parse.quote(db_path.as_posix())
    db_uri = f"file:{uri_path}?mode=ro"

    try:
        conn = sqlite3.connect(db_uri, uri=True, timeout=10.0)
    except sqlite3.Error as e:
        print(f"Error: Failed to connect to database: {e}", file=sys.stderr)
        return 1

    try:
        # Bounded lock timeout (10 seconds)
        conn.execute("PRAGMA busy_timeout = 10000;")
        conn.execute("PRAGMA query_only = ON;")

        # Start read transaction
        conn.execute("BEGIN DEFERRED;")

        cursor = conn.cursor()

        # 2. Gather DB metrics
        cursor.execute("PRAGMA page_size;")
        page_size = cursor.fetchone()[0]

        cursor.execute("PRAGMA page_count;")
        page_count = cursor.fetchone()[0]

        cursor.execute("PRAGMA freelist_count;")
        freelist_count = cursor.fetchone()[0]

        allocated_bytes = (page_count - freelist_count) * page_size
        free_bytes = freelist_count * page_size

        # Optional dbstat support
        dbstat_supported = False
        try:
            cursor.execute("SELECT 1 FROM dbstat LIMIT 1;")
            dbstat_supported = True
        except sqlite3.Error:
            pass


        # 3. Gather table stats using ONLY explicitly known ORM schema persistent tables
        explicit_known_tables = ["ranking_restore_checkpoints", "official_ranking_commands", "official_ranking_candidates", "season_closing_rankings", "official_ranking_result_versions", "official_ranking_zero_versions", "staged_calendar_ranking_result_versions", "staged_calendar_ranking_zero_versions", "owned_tournament_ranking_sources", "ranking_transition_authorities", "authoritative_world_states", "published_official_rankings", "tournament_ranking_snapshot_authorities", "tournament_wild_card_authorities", "tournament_group_rules_policies", "tournament_format_authorities", "tournament_topology_authorities", "tournament_group_match_schedule_authorities", "tournament_group_tie_resolution_authorities", "tournament_group_standings_authorities", "tournament_hybrid_knockout_entrants_authorities", "tournament_hybrid_knockout_bracket_authorities", "tournament_hybrid_ranking_policy_authorities", "tournament_pure_groups_ranking_policy_authorities", "tournament_draw_input_authorities", "tournament_draw_authorities", "tournament_draw_revisions", "tournament_draw_process_authorities", "authoritative_week_transition_receipts", "authoritative_world_events", "initial_world_states", "run_generation_proposals", "player_lifecycle_week_states", "player_tour_entry_triggers", "tournament_application_submission_authorities", "run_entry_decision_slot_authorities", "resolved_application_validation_slots", "week_tournament_lock_authorities", "definitive_wild_card_assignment_authorities", "player_health_week_states", "player_health_admin_edit_receipts", "player_sporting_week_states", "completed_week_sporting_contexts", "tournament_entry_field_versions", "match_lab_sessions", "player_lab_sessions", "player_lab_population_sessions", "tournament_lab_sessions", "run_tournament_lab_drafts", "run_tournament_lab_draft_application_receipts", "standalone_match_workspaces", "simulation_slots", "simulation_event_groups", "authoritative_live_matches", "live_match_working_states", "live_match_return_points", "live_match_alternative_paths", "live_match_completed_alternatives", "live_match_rally_commands", "authoritative_simulation_commands", "full_simulation_execution_leases", "adopted_tournament_authorities", "week_simulation_schedules", "simulation_runs", "runs", "run_calendar_extension_receipts", "legacy_simulation_run_mappings", "run_branches", "branch_saved_revisions", "run_package_states", "run_package_identity_allocators", "run_package_application_receipts", "branch_working_drafts", "branch_revision_audit_events", "branch_saved_revision_checkpoints", "branch_states", "branch_checkpoints", "saved_revision_branch_commands", "branch_fork_commands", "branch_simulation_commands", "official_branch_selection_commands", "season_state", "completed_events", "completed_event_metadata", "completed_tournament_inputs", "ranking_snapshots", "race_snapshots", "world_tour_finals_race_configurations", "world_tour_finals_race_snapshots", "world_tour_finals_participant_selection_configurations", "world_tour_finals_participant_selection_snapshots", "world_tour_finals_effective_participant_states", "world_tour_finals_replacement_authorities", "finals_qualification", "finals_results", "season_rollovers", "player_season_transitions", "next_season_players", "admin_actions", "run_talent_plans", "run_talent_country_allocations", "run_prospects", "run_generated_player_provenance", "full_simulation_tasks", "calendar_standalone_matches"]

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        db_tables = [row[0] for row in cursor.fetchall()]

        tables_report = {}

        for table in db_tables:
            if table not in explicit_known_tables:
                continue

            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]

            has_run_id_col = 'run_id' in columns

            if args.run_id and has_run_id_col:
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id = ?", (args.run_id,))
                count = cursor.fetchone()[0]
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]

            tables_report[table] = {"row_count": count}

            if dbstat_supported:
                # Get physical bytes used by this table from dbstat
                cursor.execute("SELECT SUM(pgsize) FROM dbstat WHERE name = ?", (table,))
                pg_sum = cursor.fetchone()[0]
                if pg_sum is not None:
                    tables_report[table]["physical_bytes"] = pg_sum

        # 4. Gather Branch Saved Revisions stats
        branch_stats = {}
        if "branch_saved_revisions" in db_tables:
            query = """
                SELECT
                    branch_id,
                    COUNT(*),
                    SUM(length(cast(payload_json AS BLOB))),
                    SUM(length(cast(change_summary_json AS BLOB))),
                    MAX(length(cast(payload_json AS BLOB))),
                    AVG(length(cast(payload_json AS BLOB)))
                FROM branch_saved_revisions
            """
            params = ()
            if args.run_id:
                query += " WHERE run_id = ? "
                params = (args.run_id,)

            query += " GROUP BY branch_id;"

            cursor.execute(query, params)
            for row in cursor.fetchall():
                b_id, count, p_sum, c_sum, p_max, p_avg = row
                branch_stats[b_id] = {
                    "count": count,
                    "payload_bytes_sum": p_sum or 0,
                    "change_summary_bytes_sum": c_sum or 0,
                    "payload_bytes_max": p_max or 0,
                    "payload_bytes_mean": p_avg or 0.0,
                    "head_payload_bytes": None
                }

            # Compute current HEAD payload bytes
            if "branch_working_drafts" in db_tables:
                # Find active saved revision based on draft
                head_query = """
                    SELECT d.branch_id, length(cast(r.payload_json AS BLOB))
                    FROM branch_working_drafts d
                    JOIN branch_saved_revisions r ON d.based_on_revision_id = r.revision_id
                """
                head_params = ()
                if args.run_id:
                    head_query += " WHERE d.run_id = ?"
                    head_params = (args.run_id,)

                cursor.execute(head_query, head_params)
                for row in cursor.fetchall():
                    b_id, payload_bytes = row
                    if b_id in branch_stats:
                        branch_stats[b_id]["head_payload_bytes"] = payload_bytes


        conn.commit()

    except sqlite3.Error as e:
        print(f"Error: Database read failed: {e}", file=sys.stderr)
        conn.rollback()
        return 1
    finally:
        conn.close()

    observation_end_utc = datetime.now(UTC).isoformat()
    elapsed_seconds = time.time() - start_time

    report = {
        "schema_version": SCHEMA_VERSION,
        "observation_start_utc": observation_start_utc,
        "observation_end_utc": observation_end_utc,
        "elapsed_seconds": round(elapsed_seconds, 4),
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
        "database_path": str(db_path),
        "label": args.label,
        "run_id_scope": args.run_id,
        "physical_sizes": {
            "db_bytes": get_file_size(db_path),
            "wal_bytes": get_file_size(wal_path),
            "shm_bytes": get_file_size(shm_path)
        },
        "page_metrics": {
            "page_size": page_size,
            "page_count": page_count,
            "freelist_count": freelist_count,
            "allocated_bytes": allocated_bytes,
            "free_bytes": free_bytes
        },
        "dbstat_supported": dbstat_supported,
        "tables": tables_report,
        "branch_saved_revisions": branch_stats
    }

    if args.output:
        try:
            with open(output_path, "x", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
        except OSError as e:
            print(f"Error writing to output file: {e}", file=sys.stderr)
            return 1
    else:
        print(json.dumps(report, indent=2))

    return 0

if __name__ == "__main__":
    sys.exit(main())
