"""Draft feedback must stay fast without losing review or manual acceptance."""

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.pr_critical
ROOT = Path(__file__).resolve().parents[2]
GATE = "github.event_name != 'pull_request' || github.event.pull_request.draft == false"


def acceptance_paths():
    workflows = ROOT / ".github/workflows"
    return sorted(workflows.glob("prealpha-*.yml")) + [
        workflows / "earth-full-stack-acceptance.yml",
        workflows / "saved-revision-branch-review.yml",
    ]


@pytest.mark.parametrize("path", acceptance_paths(), ids=lambda p: p.stem)
def test_review_and_manual_acceptance_are_not_lost_when_drafts_skip_heavy_jobs(path):
    workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
    events = workflow["on"]
    assert set(events["pull_request"]["types"]) == {
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
    }
    assert "workflow_dispatch" in events
    assert events["pull_request"]["paths"], "Keep the existing change-impact filters"
    assert workflow["jobs"]
    for job in workflow["jobs"].values():
        assert job["if"] == GATE
        assert job["steps"], "The full acceptance must remain available at review"


def test_fast_feedback_is_not_disabled_for_draft_pull_requests():
    workflow = yaml.load(
        (ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader
    )
    for job in workflow["jobs"].values():
        assert "draft" not in job.get("if", "")
    commands = [
        step.get("run", "") for step in workflow["jobs"]["backend-tests"]["steps"]
    ]
    config_command = next(
        command
        for command in commands
        if "tests/domain/test_tournament_config.py" in command
    )
    assert "GITHUB_EVENT_NAME=tournament_config_acceptance" in config_command


def test_python312_security_command_always_executes_its_explicit_test_file():
    workflow = yaml.load(
        (ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader
    )
    commands = [
        step.get("run", "")
        for step in workflow["jobs"]["python312-world-package-security"]["steps"]
    ]
    security_command = next(
        command
        for command in commands
        if "tests/application/test_codeql_security_boundaries.py" in command
    )
    assert "GITHUB_EVENT_NAME=world_package_security_acceptance" in security_command


def test_small_shell_does_not_replace_the_required_large_population_gates():
    workflows = ROOT / ".github/workflows"
    native = yaml.load(
        (workflows / "prealpha-native-tour-browser.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    cases = native["jobs"]["browser"]["strategy"]["matrix"]["include"]
    assert any(case["width"] == "80" and case["players"] == "1000" for case in cases)
    large = (ROOT / "scripts/admin_large_cohort_browser.py").read_text()
    assert "len(set(ids)) == 1000" in large
    shell = (ROOT / "web/acceptance/prealpha_shell_browser_smoke.py").read_text()
    assert "choices=(64, 1000)" in shell
    assert "population_size = args.population_size" in shell


@pytest.mark.parametrize('filename', [
    'prealpha-native-global-slots.yml', 'prealpha-native-groups-global-slots.yml',
])
def test_native_slot_acceptance_sets_collection_override_inside_shell(filename):
    workflow = yaml.load((ROOT / '.github/workflows' / filename).read_text(), Loader=yaml.BaseLoader)
    checked = 0
    for job in workflow['jobs'].values():
        for step in job['steps']:
            command = step.get('run', '')
            if 'python -m pytest tests/' in command:
                # GitHub reserves GITHUB_* defaults; a step env entry cannot
                # override them. The shell must set this for the pytest process.
                assert 'GITHUB_EVENT_NAME=' in command
                assert 'GITHUB_EVENT_NAME' not in step.get('env', {})
                checked += 1
    assert checked > 0
