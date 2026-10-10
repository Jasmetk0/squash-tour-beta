"""Optional actual Chromium smoke, never collected by Fast CI.

Requires an installed Playwright Python package and Chromium. All Lab writes use UI.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from earth_initial_population_experiment import source_tree_hash


def wait_http(url, process):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server exited before {url}; see saved logs")
        try:
            with urlopen(url, timeout=2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Server did not become available: {url}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path("work/earth-population/production")
    )
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    parser.add_argument("--api-port", type=int, default=8001)
    parser.add_argument("--web-port", type=int, default=5173)
    args = parser.parse_args()
    from playwright.sync_api import expect, sync_playwright

    root = args.root.resolve()
    artifacts = root / "browser"
    artifacts.mkdir(parents=True, exist_ok=True)
    sources = Path("config/world_packages")
    before = {
        world: source_tree_hash(sources / world)
        for world in ("fifa_earth", "atp_earth")
    }
    api_url, web_url = (
        f"http://127.0.0.1:{args.api_port}",
        f"http://127.0.0.1:{args.web_port}",
    )
    backend_log = (artifacts / "backend.log").open("w")
    web_log = (artifacts / "frontend.log").open("w")
    command = [
        sys.executable,
        "scripts/earth_initial_population_experiment.py",
        "--serve",
        "--root",
        str(root),
        "--port",
        str(args.api_port),
    ]
    backend = subprocess.Popen(command, stdout=backend_log, stderr=subprocess.STDOUT)
    frontend = subprocess.Popen(
        [
            "npm",
            "--prefix",
            "web",
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            str(args.web_port),
            "--strictPort",
        ],
        env={**os.environ, "VITE_API_BASE_URL": api_url},
        stdout=web_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    observations = []
    try:
        wait_http(api_url + "/health", backend)
        wait_http(web_url, frontend)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=args.chromium,
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000}, accept_downloads=True
            )
            page = context.new_page()
            page.set_default_timeout(60000)
            page.on(
                "pageerror",
                lambda error: observations.append({"page_error": str(error)}),
            )
            page.goto(web_url + "/admin/labs/player")
            expect(
                page.get_by_role(
                    "heading", name="Initial population comparison", exact=True
                )
            ).to_be_visible()
            page.get_by_label("Players per population", exact=True).fill("32")
            page.get_by_label("Initial population seeds", exact=True).fill("909")
            with page.expect_response(
                lambda response: (
                    response.request.method == "POST"
                    and response.url.endswith("/population-comparisons")
                ),
                timeout=120000,
            ) as generated:
                page.get_by_role(
                    "button", name="Generate and save population comparison", exact=True
                ).click()
            result = generated.value.json()
            assert generated.value.status == 201, result
            expect(
                page.get_by_text("Saved initial population results", exact=True)
            ).to_be_visible()
            session_url = page.url
            observations.append(
                {
                    "browser_generated_session": result["session_id"],
                    "fingerprint": result["fingerprint"],
                    "cached": result["cached"],
                    "request": result["request"],
                }
            )
            print(
                "BROWSER: generated and saved two real Earth populations, 32 players, seed 909",
                flush=True,
            )
            for label, kind in (
                ("Export complete population JSON", "json"),
                ("Export players CSV", "csv"),
            ):
                with page.expect_download() as downloaded:
                    page.get_by_role("link", name=label, exact=True).click()
                downloaded.value.save_as(str(artifacts / f"smoke-export.{kind}"))
            data = json.loads((artifacts / "smoke-export.json").read_text())
            rows = list(
                csv.DictReader(
                    io.StringIO((artifacts / "smoke-export.csv").read_text())
                )
            )
            assert len(rows) == 64
            assert data["fingerprint"] == result["fingerprint"]
            for index, run in enumerate(data["runs"]):
                page.get_by_label(
                    "Inspect generated population", exact=True
                ).select_option(str(index))
                expected_first = run["players"][0]
                table = page.get_by_role(
                    "table", name="Actual generated population players", exact=True
                )
                expect(
                    table.get_by_text(
                        expected_first["name"] + " · " + expected_first["player_id"],
                        exact=True,
                    )
                ).to_be_visible()
                expect(
                    page.get_by_text(
                        f"Stored population: 32 players; fingerprint {run['gameplay_fingerprint']}.",
                        exact=True,
                    )
                ).to_be_visible()
                counts = page.get_by_role(
                    "table", name="Selected population country counts", exact=True
                )
                dom_counts = [
                    int(row.inner_text())
                    for row in counts.locator("tbody tr td:nth-child(2)").all()
                ]
                assert sum(dom_counts) == 32 and len(dom_counts) == 250
                assert any(value == 0 for value in dom_counts)
                ui_potential = (
                    page.get_by_role(
                        "table", name="Selected population metrics", exact=True
                    )
                    .locator("tbody tr")
                    .filter(has=page.get_by_text("potential_ability", exact=True))
                )
                assert float(ui_potential.locator("td").nth(10).inner_text()) == round(
                    run["summary"]["metrics"]["potential_ability"]["mean"], 2
                )
            page.get_by_role(
                "table", name="Actual generated population players", exact=True
            ).scroll_into_view_if_needed()
            page.screenshot(path=str(artifacts / "01-real-players.png"))
            print(
                "BROWSER: switched FIFA/ATP; country sums, raw players and JSON/CSV match displayed values",
                flush=True,
            )
            assert sum(int(row["potential_ability"]) for row in rows) == sum(
                p["potential_ability"] for run in data["runs"] for p in run["players"]
            )
            context.close()
            backend.terminate()
            backend.wait(timeout=15)
            backend = subprocess.Popen(
                command, stdout=backend_log, stderr=subprocess.STDOUT
            )
            wait_http(api_url + "/health", backend)
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000}, accept_downloads=True
            )
            page = context.new_page()
            page.set_default_timeout(60000)
            posts = []
            page.on(
                "request",
                lambda request: (
                    posts.append(request.url) if request.method == "POST" else None
                ),
            )
            page.goto(session_url)
            expect(
                page.get_by_text("Saved initial population results", exact=True)
            ).to_be_visible()
            expect(
                page.get_by_text(
                    f"Stored population: 32 players; fingerprint {data['runs'][0]['gameplay_fingerprint']}.",
                    exact=True,
                )
            ).to_be_visible()
            page.get_by_text(
                "Generation provenance, effective configuration and historical fallbacks",
                exact=True,
            ).click()
            expect(
                page.get_by_text(
                    "Session: "
                    + data["session_id"]
                    + "; saved payload fingerprint "
                    + data["fingerprint"]
                    + ".",
                    exact=True,
                )
            ).to_be_visible()
            assert not posts, posts
            observations.append(
                {
                    "reopened_after_backend_restart": data["session_id"],
                    "post_requests": len(posts),
                }
            )
            print(
                "BROWSER: fresh context and backend restart reopened the same saved result; zero POSTs",
                flush=True,
            )
            # Inspect the main measured session if present, without rerunning it.
            summary_path = root / "measured-summary.json"
            if summary_path.exists():
                main_session = json.loads(summary_path.read_text())
                page.goto(
                    web_url
                    + "/admin/labs/player?population_session="
                    + main_session["session_id"]
                )
                expect(
                    page.get_by_text("Saved initial population results", exact=True)
                ).to_be_visible()
                expect(
                    page.get_by_label("Inspect generated population").locator("option")
                ).to_have_count(10)
                page.get_by_role(
                    "table", name="Pooled population metrics", exact=True
                ).scroll_into_view_if_needed()
                page.screenshot(path=str(artifacts / "02-main-pooled-results.png"))
                page.get_by_role(
                    "table", name="Earth population country comparison", exact=True
                ).scroll_into_view_if_needed()
                page.screenshot(path=str(artifacts / "03-main-countries.png"))
                observations.append(
                    {
                        "main_saved_session_opened": main_session["session_id"],
                        "post_requests": len(posts),
                    }
                )
                assert not posts
                print(
                    "BROWSER: opened main 2 × 5 × 1000 measured session without regeneration",
                    flush=True,
                )
            browser.close()
        assert before == {world: source_tree_hash(sources / world) for world in before}
        assert not any("page_error" in item for item in observations)
        (artifacts / "browser-evidence.json").write_text(
            json.dumps(
                {"observations": observations, "source_hashes_unchanged": before},
                indent=2,
            )
        )
    finally:
        backend.terminate()
        backend.wait(timeout=15)
        import signal

        os.killpg(frontend.pid, signal.SIGTERM)
        frontend.wait(timeout=15)
        backend_log.close()
        web_log.close()


if __name__ == "__main__":
    main()
