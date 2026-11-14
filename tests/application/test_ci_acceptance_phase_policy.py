"""Draft feedback must stay fast without losing review or manual acceptance."""

from pathlib import Path
from fnmatch import fnmatchcase

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
    types = set(events["pull_request"].get("types", ["opened", "synchronize", "reopened"]))
    assert {"opened", "synchronize", "reopened"} <= types
    assert "workflow_dispatch" in events
    assert events["pull_request"]["paths"], "Keep the existing change-impact filters"
    assert workflow["jobs"]
    for job in workflow["jobs"].values():
        # Cheap read-only audits also run on Drafts. An unconditional job is
        # stronger coverage than the Ready/manual gate, not a missing check.
        assert job.get("if") in (None, GATE)
        if job.get("if") == GATE:
            assert "ready_for_review" in types
        assert job["steps"], "The full acceptance must remain available at review"


def test_fast_feedback_is_not_disabled_for_draft_pull_requests():
    workflow = yaml.load(
        (ROOT / ".github/workflows/ci.yml").read_text(), Loader=yaml.BaseLoader
    )
    for job in workflow["jobs"].values():
        assert "draft" not in job.get("if", "")
    config_command = next(
        step['run'] for step in workflow["jobs"]["backend-tests"]["steps"]
        if step.get('name') == 'Run tournament configuration security regression'
    )
    assert 'tests/domain/test_tournament_config.py' in config_command
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


@pytest.mark.parametrize('script', ['player_career', 'season_archive', 'follow_alerts'])
def test_native_reader_scripts_keep_their_real_gate_without_general_backend_selection(script):
    workflows = ROOT / '.github/workflows'
    fast = yaml.load((workflows / 'ci.yml').read_text(), Loader=yaml.BaseLoader)
    detector = next(step['with'] for step in fast['jobs']['changes']['steps'] if step.get('id') == 'filter')
    assert detector['predicate-quantifier'] == 'some-with-excludes'
    filters = yaml.load(detector['filters'], Loader=yaml.BaseLoader)
    path = f'scripts/{script}_browser_acceptance.py'
    for area in ['backend', 'backend_core']:
        assert '!' + path in filters[area]
        # Unknown scripts and actual application/test changes must still select
        # the backend; do not replace a precise exception with a broad glob.
        exclusions = [p[1:] for p in filters[area] if p.startswith('!')]
        for protected in ['scripts/new_native_browser_acceptance.py',
                          'src/beta_engine/application/calendar_tour.py',
                          'tests/api/test_new_native_reader.py']:
            assert any(fnmatchcase(protected, p) for p in filters[area] if not p.startswith('!'))
            assert not any(fnmatchcase(protected, p) for p in exclusions)
    native = yaml.load((workflows / 'claude-native-readers-acceptance.yml').read_text(), Loader=yaml.BaseLoader)
    assert any(fnmatchcase(path, pattern) for pattern in native['on']['pull_request']['paths'])
    assert set(native['on']['pull_request']['types']) == {'opened', 'synchronize', 'reopened', 'ready_for_review'}
    assert 'workflow_dispatch' in native['on']
    assert len(native['jobs']['api']['strategy']['matrix']['case']) == 13
    for job in native['jobs'].values():
        assert job['if'] == GATE
    browser = native['jobs']['browser']
    assert script in browser['strategy']['matrix']['script']
    assert set(browser['strategy']['matrix']['script']) == {
        'saved_draw_readiness', 'player_career', 'season_archive', 'follow_alerts'
    }
    assert any('python "scripts/${SCRIPT}_browser_acceptance.py"' in step.get('run', '')
               for step in browser['steps'])


def test_native_reader_shared_url_and_guard_changes_trigger_actual_acceptance():
    workflow = yaml.load((ROOT / '.github/workflows/claude-native-readers-acceptance.yml').read_text(), Loader=yaml.BaseLoader)
    paths = workflow['on']['pull_request']['paths']
    assert 'web/src/components/readerUrlState.ts' in paths
    assert 'web/src/navigation/AdminTransitionBlocker.tsx' in paths
