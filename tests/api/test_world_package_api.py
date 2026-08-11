"""Country V1 adapter for the established World Package API regression suite.

The broad historical suite lives in ``world_package_api_contract_suite`` so its
coverage remains intact.  This module patches only the country create/edit
helpers to the canonical V1 HTTP contract and replaces the two assertions that
previously required persisted national ``style_dna``.
"""

from __future__ import annotations

from tests.api import world_package_api_contract_suite as _suite


_V1_RATING_FIELDS = (
    "squash_popularity",
    "squash_access",
    "development_quality",
    "competition_quality",
    "elite_support",
    "squash_tradition",
)


def _country_update_payload(detail: dict[str, object]) -> dict[str, object]:
    country = detail["country"]
    assert isinstance(country, dict)
    return {
        key: country[key]
        for key in (
            "name",
            "notes",
            "area_km2",
            "region",
            "travel_region",
            "timezone_area",
            "court_count",
            *_V1_RATING_FIELDS,
        )
    }


def _country_create_payload(fingerprint: str) -> dict[str, object]:
    return {
        "code": "ABC",
        "name": "Alphabetia",
        "notes": "New country",
        "area_km2": 12_345,
        "region": "EUROPE",
        "travel_region": "EUROPE",
        "court_count": 12,
        "squash_popularity": 2,
        "squash_access": 3,
        "development_quality": 4,
        "competition_quality": 2.5,
        "elite_support": 4,
        "squash_tradition": 1,
        "population_by_year": {"1995": 900_000, "2020": 1_200_000},
        "expected_package_fingerprint": fingerprint,
    }


# Existing test functions keep their original module globals. Replacing these
# two helpers therefore migrates every unchanged create/edit test without
# copying or weakening the regression suite.
_suite._country_update_payload = _country_update_payload
_suite._country_create_payload = _country_create_payload

for _name, _value in vars(_suite).items():
    if _name.startswith("test_"):
        globals()[_name] = _value


def _assert_canonical_v1_attribute_files(package_root, code: str) -> None:
    attributes = package_root / "countries" / code / "attributes"
    stems = {path.stem for path in attributes.glob("*.json")}
    assert stems == {
        "population",
        "area_km2",
        "region",
        "travel_region",
        "timezone_area",
        "court_count",
        *_V1_RATING_FIELDS,
    }
    assert not stems.intersection(
        {"wealth_support", "system_quality", "competition_density", "federation_quality", "style_dna"}
    )


def test_put_custom_country_persists_edit_and_preserves_population_and_index(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "overrides.json"
    _suite._write_fixture(countries_path, _suite.COUNTRIES_FIXTURE)
    _suite._write_fixture(overrides_path, _suite.OVERRIDES_FIXTURE)
    worlds_root = _suite._copy_worlds_root(tmp_path)

    with _suite.ApiServer(
        database_url=f"sqlite:///{tmp_path / 'edit-v1.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        clone_status, _ = _suite._request(
            "POST",
            f"{server.base_url}/world/packages/official_fax_world/clone",
            {"new_world_id": "editable", "name": "Editable", "dry_run": False},
        )
        assert clone_status == 200
        _, before = _suite._request("GET", f"{server.base_url}/world/packages/editable/countries/GER")
        payload = _country_update_payload(before)
        payload.update(
            {
                "name": "Germanica Prime",
                "squash_popularity": 4,
                "development_quality": 3.5,
                "elite_support": 4,
                "expected_package_fingerprint": before["package"]["fingerprint"],
            }
        )
        package_root = worlds_root / "custom" / "editable"
        population = (package_root / "countries/GER/attributes/population.json").read_bytes()
        index = (package_root / "countries/index.json").read_bytes()
        status, response = _suite._request(
            "PUT", f"{server.base_url}/world/packages/editable/countries/GER", payload
        )
        get_status, after = _suite._request(
            "GET", f"{server.base_url}/world/packages/editable/countries/GER"
        )

    assert status == 200 and get_status == 200
    assert response["package"]["fingerprint"] != before["package"]["fingerprint"]
    assert response["validation"]["status"] != "errors"
    assert response["validation"]["error_count"] == 0
    country = after["country"]
    assert country["code"] == "GER"
    assert country["name"] == "Germanica Prime"
    assert country["squash_popularity"] == 4
    assert country["development_quality"] == 3.5
    assert country["elite_support"] == 4
    assert all(1 <= country[field] <= 5 for field in _V1_RATING_FIELDS)
    assert "style_dna" not in country
    assert country["population_by_year"] == before["country"]["population_by_year"]
    assert (package_root / "countries/GER/attributes/population.json").read_bytes() == population
    assert (package_root / "countries/index.json").read_bytes() == index
    _assert_canonical_v1_attribute_files(package_root, "GER")


def test_country_create_http_roundtrips_authored_state_and_rejects_duplicate(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "overrides.json"
    _suite._write_fixture(countries_path, _suite.COUNTRIES_FIXTURE)
    _suite._write_fixture(overrides_path, _suite.OVERRIDES_FIXTURE)
    worlds_root = _suite._copy_worlds_root(tmp_path)

    with _suite.ApiServer(
        database_url=f"sqlite:///{tmp_path / 'create-country-v1.db'}",
        countries_config_path=str(countries_path),
        manual_overrides_config_path=str(overrides_path),
        worlds_root=str(worlds_root),
    ) as server:
        assert _suite._request(
            "POST",
            f"{server.base_url}/world/packages/official_fax_world/clone",
            {"new_world_id": "editable", "name": "Editable", "dry_run": False},
        )[0] == 200
        _, package = _suite._request("GET", f"{server.base_url}/world/packages/editable")
        before = package["fingerprint"]
        payload = _country_create_payload(before)
        status, response = _suite._request(
            "POST", f"{server.base_url}/world/packages/editable/countries", payload
        )
        get_status, detail = _suite._request(
            "GET", f"{server.base_url}/world/packages/editable/countries/ABC"
        )
        _, countries = _suite._request("GET", f"{server.base_url}/world/packages/editable/countries")
        duplicate_status, _ = _suite._request(
            "POST",
            f"{server.base_url}/world/packages/editable/countries",
            {**payload, "expected_package_fingerprint": response["package"]["fingerprint"]},
        )
        _, unchanged = _suite._request(
            "GET", f"{server.base_url}/world/packages/editable/countries/ABC"
        )

    assert status == 201 and get_status == 200
    assert response["country_detail"]["country"]["code"] == "ABC"
    country = detail["country"]
    assert country["name"] == "Alphabetia"
    assert country["notes"] == "New country"
    assert {field: country[field] for field in _V1_RATING_FIELDS} == {
        "squash_popularity": 2,
        "squash_access": 3,
        "development_quality": 4,
        "competition_quality": 2.5,
        "elite_support": 4,
        "squash_tradition": 1,
    }
    assert "style_dna" not in country
    assert country["population_by_year"] == {"1995": 900_000, "2020": 1_200_000}
    assert country["population"] == country["default_population"] == 1_200_000
    assert country["default_population_year"] == 2020
    assert [item["code"] for item in countries["countries"]].count("ABC") == 1
    assert response["package"]["fingerprint"] != before
    assert response["validation"]["error_count"] == 0
    assert duplicate_status == 409
    assert unchanged["country"] == country
    _assert_canonical_v1_attribute_files(worlds_root / "custom" / "editable", "ABC")


def test_timezone_area_registry_http_contract_and_controlled_errors(tmp_path) -> None:
    countries_path = tmp_path / "countries.json"
    overrides_path = tmp_path / "overrides.json"
    _suite._write_fixture(countries_path, _suite.COUNTRIES_FIXTURE)
    _suite._write_fixture(overrides_path, _suite.OVERRIDES_FIXTURE)
    worlds_root = _suite._copy_worlds_root(tmp_path)
    with _suite.ApiServer(database_url=f"sqlite:///{tmp_path/'timezone-api.db'}", countries_config_path=str(countries_path), manual_overrides_config_path=str(overrides_path), worlds_root=str(worlds_root)) as server:
        _, builtin = _suite._request("GET", f"{server.base_url}/world/packages/official_fax_world")
        readonly_status, _ = _suite._request("PUT", f"{server.base_url}/world/packages/official_fax_world/geography/timezone-areas", {"timezone_areas": [], "expected_package_fingerprint": builtin["fingerprint"]})
        assert readonly_status == 403
        assert _suite._request("POST", f"{server.base_url}/world/packages/official_fax_world/clone", {"new_world_id":"editable","name":"Editable","dry_run":False})[0] == 200
        _, package = _suite._request("GET", f"{server.base_url}/world/packages/editable")
        original = package["fingerprint"]
        areas = [{"code":"WEST","name":"West","position":0},{"code":"EAST","name":"East","position":1},{"code":"PAC","name":"Pacific","position":2}]
        status, geography = _suite._request("PUT", f"{server.base_url}/world/packages/editable/geography/timezone-areas", {"timezone_areas":areas,"expected_package_fingerprint":original})
        assert status == 200 and geography["timezone_areas"] == areas and geography["timezone_areas_authored"] is True
        _, changed = _suite._request("GET", f"{server.base_url}/world/packages/editable")
        assert changed["fingerprint"] != original
        assert _suite._request("PUT", f"{server.base_url}/world/packages/editable/geography/timezone-areas", {"timezone_areas":areas,"expected_package_fingerprint":original})[0] == 409
        for malformed in (
            [{"code":"WEST","name":"West","position":0},{"code":"WEST","name":"Duplicate","position":1}],
            [{"code":"WEST","name":"West","position":0},{"code":"EAST","name":"East","position":2}],
        ):
            code, body = _suite._request("PUT", f"{server.base_url}/world/packages/editable/geography/timezone-areas", {"timezone_areas":malformed,"expected_package_fingerprint":changed["fingerprint"]})
            assert code == 422 and "invalid Timezone Area registry" in str(body)
        _, detail = _suite._request("GET", f"{server.base_url}/world/packages/editable/countries/GER")
        update = {**_country_update_payload(detail), "timezone_area":"EAST", "expected_package_fingerprint":changed["fingerprint"]}
        assert _suite._request("PUT", f"{server.base_url}/world/packages/editable/countries/GER", update)[0] == 200
        _, assigned = _suite._request("GET", f"{server.base_url}/world/packages/editable/countries/GER")
        orphan_status, orphan_body = _suite._request("PUT", f"{server.base_url}/world/packages/editable/geography/timezone-areas", {"timezone_areas":[areas[0], {**areas[2],"position":1}], "expected_package_fingerprint":assigned["package"]["fingerprint"]})
        assert orphan_status == 422 and "orphan country assignments" in str(orphan_body)
