"""Reusable, genuinely produced SQLite input for global-slot acceptance."""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def prepared_slots(tmp_path_factory):
    from tests.api.test_calendar_global_slots import ready
    from tests.api.test_saved_revision_history_api import ApiServer

    supplied = os.environ.get("GLOBAL_SLOT_PREPARED_DATABASE")
    if supplied:
        path = Path(supplied)
        assert path.is_file()
        return path
    path = tmp_path_factory.mktemp("real-global-slot-source") / "prepared.db"
    with ApiServer(database_url=f"sqlite:///{path}") as server:
        ready(server, int(os.environ.get("GLOBAL_SLOT_CALENDAR", "52")))
    return path


@pytest.fixture(scope="session")
def prepared_slots_v2(tmp_path_factory):
    """The same genuinely produced global-slot Run, explicitly stored as Saved v2.

    ``ready``, then every global slot of week 4 (real MatchEngine matches),
    both result confirmations and two Week Transitions, each followed by its
    explicit Tour Save, so the cold lineage has many growing native revisions.
    Only the opt-in storage variable differs.
    """
    from beta_engine.infrastructure.db.saved_v2_hooks import ENVIRONMENT_VARIABLE
    from tests.api.test_calendar_global_slots import ready
    from tests.api.test_calendar_tour_flow import command, execute, inspect, save_tour
    from tests.api.test_saved_revision_history_api import ApiServer

    supplied = os.environ.get("GLOBAL_SLOT_PREPARED_V2_DATABASE")
    if supplied:
        path = Path(supplied)
        assert path.is_file()
        return path
    path = tmp_path_factory.mktemp("real-global-slot-source-v2") / "prepared-v2.db"
    previous = os.environ.get(ENVIRONMENT_VARIABLE)
    os.environ[ENVIRONMENT_VARIABLE] = "saved_v2"
    try:
        with ApiServer(database_url=f"sqlite:///{path}") as server:
            ready(server, 52)
            for number in range(1, 17):
                view = inspect(server)
                if view["next_slot"] is None:
                    break
                execute(server, command(view, "next-slot", name=f"v2-slot-{number}"))
                save_tour(server)
            for edition_id in ("parallel-a", "parallel-b"):
                execute(server, command(inspect(server), "confirm-result",
                                        name=f"{edition_id}:confirm", edition_id=edition_id))
                save_tour(server)
            for target in (5, 6):
                execute(server, command(inspect(server), "transition", name=f"v2-week-{target}"))
                save_tour(server)
    finally:
        if previous is None:
            os.environ.pop(ENVIRONMENT_VARIABLE, None)
        else:
            os.environ[ENVIRONMENT_VARIABLE] = previous
    return path
