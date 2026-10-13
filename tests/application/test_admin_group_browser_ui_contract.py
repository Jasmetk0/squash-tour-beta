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
