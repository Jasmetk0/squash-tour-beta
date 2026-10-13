"""Fast structure guard for the genuine browser-owned group authority acceptance.

The actual FastAPI/SQLite/Chromium sporting proof lives in the dedicated
browser workflow. These tests prevent accidentally replacing its required
button clicks with direct API authority writes.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "admin_saved_group_browser_smoke.py"
COMPLETION = Path(__file__).resolve().parents[2] / "scripts" / "saved_completed_group_browser_checks.py"
REQUIRED_CLICKS = {
    "Choose pure round-robin groups",
    "Adopt season Group Rules",
    "Configure pure-groups Format",
    "Generate group Topology",
    "Generate group Match Schedule",
}
AUTHORITY_WRITE_PATHS = (
    "/tournament-group-rules/versions",
    "/format/configure",
    "/format/topology/generate",
    "/format/group-match-schedule/generate",
)


def test_browser_setup_authorities_are_confirmed_by_admin_controls():
    syntax = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    clicked = {
        node.args[1].value
        for node in ast.walk(syntax)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "browser_click"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    }
    assert REQUIRED_CLICKS <= clicked


def test_group_setup_authorities_have_no_direct_http_post_bypass():
    syntax = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    for node in ast.walk(syntax):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "request":
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        if node.args[0].value != "POST":
            continue
        path = ast.unparse(node.args[1]) if len(node.args) > 1 else ""
        assert not any(endpoint in path for endpoint in AUTHORITY_WRITE_PATHS), path


def test_real_group_browser_reads_the_frozen_table_in_admin_after_sporting_save():
    """The dedicated Chromium check must re-open the real saved group context."""
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    names = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "Canonical group 1 standings" in names
    assert "Generate canonical group standings" in names
    assert "Canonical completed group standings" in names

def test_group_match_days_final_table_and_save_are_exercised_through_real_ui():
    """All three previously API-only user actions must be real browser clicks."""
    tree = ast.parse(COMPLETION.read_text(encoding="utf-8"))
    names = {
        node.args[1].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "browser_click"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    }
    assert {
        "Review authoritative Next Match Day",
        "Simulate reviewed authoritative Match Day",
        "Commit audited group tie decision",
    } <= names
    # These authority writes are still genuine production button clicks.
    # The result itself, not global network idle, confirms their completion.
    direct_click_names = {
        node.func.value.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "click"
        and isinstance(node.func.value, ast.Name)
    }
    assert {"button", "save_button", "final_save_button"} <= direct_click_names
    labels = {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "Generate canonical group standings" in labels
    assert "Save authoritative simulation" in labels

    forbidden = (
        "/simulate-next-match-day",
        "/group-standings/generate",
        "/group-standings/tie-resolution",
        "/save",
    )
    for node in ast.walk(tree):
        if (not isinstance(node, ast.Call)
            or not isinstance(node.func, ast.Name)
            or node.func.id != "request"
            or len(node.args) < 2
            or not isinstance(node.args[0], ast.Constant)
            or node.args[0].value != "POST"):
            continue
        source = ast.unparse(node.args[1])
        assert not any(endpoint in source for endpoint in forbidden), source


def test_real_completed_group_browser_saves_and_restarts_before_final_table():
    """A completed group must survive a *real* intermediate Save and restart.

    The fast guard supplements, but does not replace, production Chromium
    against a file-backed SQLite run.
    """
    tree = ast.parse(COMPLETION.read_text(encoding="utf-8"))
    clicks = sorted(
        (node.lineno, node.args[1].value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "browser_click"
        and len(node.args) >= 2
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    )
    # The first Save waits for the actual enabled control and confirmed
    # revision; it must not rely on an unrelated global AJAX-idle heuristic.
    direct_save_clicks = [
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "click"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id in {"save_button", "final_save_button"}
    ]
    save_lines = sorted(
        [line for line, label in clicks
         if label == "Save authoritative simulation"] + direct_save_clicks
    )
    publish_lines = [
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "click"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "button"
    ]
    restarts = [
        node.lineno for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "restart_backend"
    ]
    assert len(save_lines) == 2, "One Save before and one after final table"
    assert len(publish_lines) == 1
    assert len(restarts) == 1
    assert save_lines[0] < restarts[0] < publish_lines[0] < save_lines[1]

    constants = {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "Saved pending group tie decisions" in constants
    assert "Saved group standings" in constants
    assert "04-reopened-intermediate-no-final-table.png" in constants
