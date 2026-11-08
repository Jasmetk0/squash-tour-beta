"""Adversarial structural checks using disposable data; never mutate Earth packages."""
import json
import subprocess
import sys

import pytest

from tools.audit_earth_packages import ATTRIBUTES, YEARS, audit_package

pytestmark = pytest.mark.pr_critical


def fixture(tmp_path):
    root = tmp_path / 'earth'
    files = {
        'countries/index.json': {'schema_version': 'world_package_countries_index.v1', 'country_codes': ['CZE']},
        'generation/country_histories/CZE.json': {'schema_version': 'country_rating_history.v2', 'years': {
            str(y): {'ratings': {a: {'value': 5.5} for a in ATTRIBUTES}} for y in YEARS}},
        'countries/CZE/attributes/population.json': {'schema_version': 'country_population.v1',
                                                   'values_by_year': {str(y): 100 for y in YEARS}},
    }
    for path, value in files.items():
        output = root / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(value), encoding='utf-8')
    return root


def change(root, path, edit):
    target = root / path
    value = json.loads(target.read_text())
    edit(value)
    target.write_text(json.dumps(value), encoding='utf-8')


def test_complete_fixture_is_read_only(tmp_path):
    root = fixture(tmp_path)
    before = {str(p): p.read_bytes() for p in root.rglob('*.json')}
    result = audit_package(root)
    assert result.structurally_complete_codes == ['CZE']
    assert not any(result.issues().values())
    assert {str(p): p.read_bytes() for p in root.rglob('*.json')} == before


@pytest.mark.parametrize('value', [True, -1, 1.5, '100', None])
def test_population_value_must_be_nonnegative_integer(tmp_path, value):
    root = fixture(tmp_path)
    change(root, 'countries/CZE/attributes/population.json',
           lambda p: p['values_by_year'].update({'2000': value}))
    result = audit_package(root)
    assert result.missing_population
    assert result.structurally_complete_codes == []


def test_missing_population_year_map_never_counts_as_complete(tmp_path):
    root = fixture(tmp_path)
    change(root, 'countries/CZE/attributes/population.json', lambda p: p.pop('values_by_year'))
    assert audit_package(root).structurally_complete_codes == []


@pytest.mark.parametrize('value', [True, 0, 11, 5.55, float('nan'), float('inf')])
def test_invalid_rating_or_nonfinite_json_is_rejected(tmp_path, value):
    root = fixture(tmp_path)
    change(root, 'generation/country_histories/CZE.json',
           lambda p: p['years']['2000']['ratings'][ATTRIBUTES[0]].update(value=value))
    result = audit_package(root)
    assert result.invalid_ranges or result.load_errors
    assert result.structurally_complete_codes == []


def test_missing_index_and_wrong_shape_are_explicit_errors(tmp_path):
    root = tmp_path / 'absent'
    assert audit_package(root).load_errors
    root = fixture(tmp_path)
    change(root, 'countries/index.json', lambda p: p.update(country_codes='CZE'))
    assert audit_package(root).load_errors


def test_duplicate_ids_invalid_path_missing_history_and_years(tmp_path):
    root = fixture(tmp_path)
    change(root, 'countries/index.json', lambda p: p.update(country_codes=['CZE', 'CZE', '../outside']))
    change(root, 'generation/country_histories/CZE.json', lambda p: p['years'].pop('1955'))
    result = audit_package(root)
    assert result.duplicates == ['CZE']
    assert result.invalid_ids and result.missing_years
    assert result.structurally_complete_codes == []
    (root / 'generation/country_histories/CZE.json').unlink()
    assert audit_package(root).missing_histories == ['CZE']


def test_duplicate_json_year_keys_are_rejected(tmp_path):
    root = fixture(tmp_path)
    (root / 'countries/CZE/attributes/population.json').write_text(
        '{"schema_version":"country_population.v1","values_by_year":{"2000":1,"2000":2}}')
    assert audit_package(root).missing_population


def test_cli_executes_with_current_python():
    result = subprocess.run([sys.executable, 'tools/audit_earth_packages.py'],
                            check=False, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert 'Audit fifa_earth' in result.stdout and 'Audit atp_earth' in result.stdout
    assert 'NOT scientific validity' in result.stdout
    assert 'Fully valid countries' not in result.stdout
