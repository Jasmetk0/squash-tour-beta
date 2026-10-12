"""Focused regression for the dedicated Add Selected browser acceptance wiring.

The real end-to-end acceptance runs in its own expensive Chromium workflow.
These cheap checks keep its entrypoint, scope and evidence contract discoverable
to Fast CI when a PR only changes scripts/workflows.
"""
import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.pr_critical

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "admin_selected_append_browser.py"
WORKFLOW = ROOT / ".github" / "workflows" / "prealpha-selected-append-browser.yml"


def test_selected_append_browser_script_is_valid_and_has_dedicated_acceptance():
    code = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(code, filename=str(SCRIPT))
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"database_snapshot", "validate_week_one", "acceptance"}.issubset(functions)
    assert 'if __name__ == "__main__"' in code
    assert "SELECT revision_id, sequence, payload_json, content_hash" in code
    assert "original_revisions" in code and "saved_after_backend_restart" in code
    assert "player_sporting_week_states" in code and "player_health_week_states" in code
    assert "selected-append/preview" in code and "selected-append" in code


def test_browser_workflow_is_path_scoped_and_retains_failure_evidence():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request:" in workflow and "workflow_dispatch:" in workflow
    assert "scripts/admin_selected_append_browser.py" in workflow
    assert "python scripts/admin_selected_append_browser.py" in workflow
    assert "retention-days: 14" in workflow
    assert "if: always()" in workflow
    assert "Full Test Suite" not in workflow
