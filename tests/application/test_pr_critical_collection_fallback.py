"""PR collection falls back to actual critical checks, never an empty green run."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import tests.conftest as collection

pytestmark = pytest.mark.pr_critical


def item(path, critical=False):
    return SimpleNamespace(path=collection.ROOT / path,
                           get_closest_marker=lambda name: critical if name == 'pr_critical' else None)


def config(expr):
    return SimpleNamespace(option=SimpleNamespace(markexpr=expr), hook=SimpleNamespace(pytest_deselected=Mock()))


@pytest.mark.parametrize('changed', [set(), {'tests/api/test_smoke.py'}])
def test_no_changed_critical_test_keeps_the_real_baseline(monkeypatch, changed):
    monkeypatch.setattr(collection, '_pull_request_changed_test_paths', lambda: changed)
    checks = [item('tests/domain/test_protected.py', True), item('tests/api/test_smoke.py')]
    original = list(checks)
    cfg = config('pr_critical')
    collection.pytest_collection_modifyitems(cfg, checks)
    assert checks == original
    cfg.hook.pytest_deselected.assert_not_called()


def test_changed_critical_tests_remain_scoped(monkeypatch):
    monkeypatch.setattr(collection, '_pull_request_changed_test_paths', lambda: {'tests/domain/test_changed.py'})
    changed = item('tests/domain/test_changed.py', True)
    other = item('tests/domain/test_protected.py', True)
    checks = [changed, other]
    cfg = config('pr_critical')
    collection.pytest_collection_modifyitems(cfg, checks)
    assert checks == [changed]
    cfg.hook.pytest_deselected.assert_called_once_with(items=[other])


def test_ordinary_changed_test_selection_keeps_its_existing_contract(monkeypatch):
    monkeypatch.setattr(collection, '_pull_request_changed_test_paths', lambda: {'tests/api/test_smoke.py'})
    smoke = item('tests/api/test_smoke.py')
    other = item('tests/domain/test_protected.py', True)
    checks = [smoke, other]
    cfg = config('')
    collection.pytest_collection_modifyitems(cfg, checks)
    assert checks == [smoke]
