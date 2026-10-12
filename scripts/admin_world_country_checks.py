"""Positive canonical Run World + country Saved roster checks on real Chromium/SQLite.

Invoked from the existing 1000-player browser acceptance, not a separate CI job.
Never modifies source Package, persisted Run, working draft or Saved Revision.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from playwright.sync_api import expect


def package_source_digest(root: Path) -> str:
    assert root.is_dir(), f"Missing built-in package source: {root}"
    digest = hashlib.sha256()
    files = sorted(path for path in root.rglob("*") if path.is_file())
    assert files, "Built-in package source is empty"
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def verify_positive_world_country(
    page, *, run_url: str, api_url: str, country_code: str,
    expected_fingerprint: str | None,
    expected_player_ids: list[str] | None,
) -> tuple[str, list[str], str]:
    """Prove a saved Run-owned World read and, if requested, canonical 25-row paging."""
    run_id = run_url.split("/admin/runs/", 1)[1].split("/", 1)[0].split("?", 1)[0]
    assert run_id, run_url
    page.goto(run_url)
    branch_id = page.get_by_role("combobox", name="Admin active Branch").input_value()
    assert branch_id

    def get_saved_head() -> str:
        response = page.request.get(api_url + "/run-branches", params={"run_id": run_id})
        assert response.ok, response.text()
        match = [branch for branch in response.json()["run_branches"]
                 if branch["branch_id"] == branch_id]
        assert len(match) == 1 and match[0]["saved_head_revision_id"], match
        return match[0]["saved_head_revision_id"]

    def get_world() -> dict:
        response = page.request.get(
            api_url + f"/admin/runs/{run_id}/branches/{branch_id}/packages"
        )
        assert response.ok, response.text()
        snapshot = response.json()
        assert snapshot["state"]["run_id"] == run_id
        assert snapshot["state"]["branch_id"] == branch_id
        assert snapshot["fingerprint"]
        worlds = [
            item for item in snapshot["state"]["package_versions"]
            if item["package_type"] == "World"
        ]
        assert len(worlds) == 1 and worlds[0]["package_id"] == "official_fax_world"
        return snapshot

    saved_head = get_saved_head()
    snapshot = get_world()
    fingerprint = snapshot["fingerprint"]
    if expected_fingerprint is not None:
        assert fingerprint == expected_fingerprint, "World copy changed without World edit"
    raw_countries = [
        entity for entity in snapshot["state"]["entities"]
        if entity["entity_kind"] == "world.country.v1"
        and entity["source_package_id"] == "official_fax_world"
    ]
    assert len(raw_countries) > 1, "Positive country route requires copied World countries"
    country = next((item for item in raw_countries
                    if item["source_entity_id"] == country_code), None)
    assert country and country["payload"]["code"] == country_code

    # Read the World and country detail from the actual persisted World copy,
    # not a mocked source response or the global Package Library.
    page.goto(run_url + f"/world?year=2000&q={country_code}")
    expect(page.get_by_role("heading", name="Run World")).to_be_visible()
    overview = page.get_by_role("table", name="Run World countries")
    expect(overview.locator("tbody tr")).to_have_count(1)
    overview.locator(f'a[href*="/world/countries/{country_code}"]').click()
    expect(page.get_by_role("region", name="Run World country detail")).to_be_visible()
    assert country_code in page.url and "q=" + country_code in page.url
    page.get_by_role("combobox", name="World data year").select_option("2010")
    assert "year=2010" in page.url and "q=" + country_code in page.url
    navigation = page.get_by_role("navigation", name="Country detail sections")
    navigation.get_by_role("link", name="Population").click()
    expect(page.get_by_role("region", name="Country population history")).to_be_visible()
    navigation.get_by_role("link", name="Country Attributes").click()
    expect(page.get_by_role("region", name="Country rating history")).to_be_visible()
    rating_table = page.get_by_role("table", name="Country rating snapshot")
    expect(rating_table.locator("tbody tr")).to_have_count(6)
    assert rating_table.get_by_text("legacy scalar", exact=False).count() > 0 or (
        rating_table.get_by_text("historical", exact=False).count() > 0
    ), "Country rating source provenance was not explained"
    page.get_by_role("link", name="Back to countries").click()
    assert "q=" + country_code in page.url and "year=2010" in page.url
    expect(page.get_by_role("table", name="Run World countries").locator("tbody tr")).to_have_count(1)

    roster_ids: list[str] = []
    if expected_player_ids is not None:
        page.goto(
            run_url + f"/world/countries/{country_code}?year=2020&q={country_code}&tab=players"
        )
        expect(page.get_by_role("region", name="Run World canonical country players")).to_be_visible()
        checkbox = page.get_by_role("checkbox", name=(
            "Explicitly include saved prepared prospects (may contain future identities)"
        ))
        assert not checkbox.is_checked(), "Prepared future players visible by default"
        total = len(expected_player_ids)
        assert total > 25, "Test needs 25-row country roster pagination"
        for offset in range(0, total, 25):
            params = {
                "search": "", "country_code": country_code, "status_filter": "",
                "include_prepared": "false", "offset": offset, "limit": 25,
            }
            response = page.request.get(
                api_url + f"/admin/runs/{run_id}/branches/{branch_id}/saved-players",
                params=params,
            )
            assert response.ok, response.text()
            data = response.json()
            assert data["saved_revision_id"] == saved_head
            assert data["run_id"] == run_id and data["branch_id"] == branch_id
            assert data["country_code"] == country_code
            assert data["source"] == "selected_branch_saved_revision"
            assert data["time_context"] == "present"
            assert data["include_prepared"] is False
            assert data["offset"] == offset and data["limit"] == 25
            assert data["total"] == total
            assert data["has_more"] == (offset + 25 < total)
            page_ids = [p["player_id"] for p in data["players"]]
            assert len(page_ids) == min(25, total - offset)
            assert all(p["country_code"] == country_code for p in data["players"])
            assert all(p["identity_source"] != "run_prospect" for p in data["players"])
            expect(page.get_by_role("table", name="Saved country roster").locator("tbody tr")).to_have_count(len(page_ids))
            for player_id in page_ids:
                expect(page.get_by_role("table", name="Saved country roster")
                       .locator(f'a[href$="/people/{player_id}"]')).to_have_count(1)
            roster_ids.extend(page_ids)
            if offset + 25 < total:
                page.get_by_role("button", name="Next →").click()
                expect(page.get_by_text(
                    f"Page {offset // 25 + 2} /", exact=False
                )).to_be_visible()
        assert len(roster_ids) == len(set(roster_ids)) == total
        assert sorted(roster_ids) == expected_player_ids, "Saved API vs generated IDs mismatch"
        profile_id = roster_ids[-1]
        page.get_by_role("table", name="Saved country roster").locator(
            f'a[href$="/people/{profile_id}"]').click()
        assert page.url.split("?")[0].endswith("/people/" + profile_id)
        assert not page.get_by_text(
            "No verified player identity in this Saved Revision", exact=False
        ).count(), "Country roster linked to an unavailable profile"

    # Crucial read-only invariant: all navigation, years, tabs, page reads and
    # profiles have not changed the owning Saved Revision or World fingerprint.
    assert get_saved_head() == saved_head, "Country read mutated Saved HEAD"
    assert get_world()["fingerprint"] == fingerprint, "Country read mutated Run World"
    return fingerprint, sorted(roster_ids), saved_head
