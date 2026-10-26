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
