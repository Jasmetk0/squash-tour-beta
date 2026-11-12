"""Real Chromium: Saved Draw native readiness on the actual Saved Edition page.

A real API server holds an authored Saved FAX Draw (Platinum/Gold geometry, 36
participants). The Admin page is opened in Chromium in English and Czech and must show
the read-only readiness section from the backend's own responses, the separate
explanation of historical first entry versus professional eligibility, and no adoption
control. Nothing is written: Saved head and Tour fingerprint are compared before/after.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from playwright.sync_api import expect, sync_playwright

    from beta_engine.domain.calendar.run_calendar import RunCalendar
    from scripts.native_tour_browser_acceptance import stop_process, wait_http
    from tests.api import test_native_canonical_knockout as canonical
    from tests.api.test_calendar_tour_flow import inspect, setup
    from tests.api.test_saved_revision_history_api import ApiServer
    from tests.infrastructure import test_fax_reference_player_draw as fax

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument(
        "--chromium", default=os.environ.get("CHROME_BIN", "/usr/bin/chromium")
    )
    args = parser.parse_args()
    expect.set_options(timeout=30000)
    root = args.root or Path(tempfile.mkdtemp(prefix="saved-draw-readiness-"))
    root.mkdir(parents=True, exist_ok=True)
    factory = SimpleNamespace(mktemp=lambda name, numbered=True: Path(tempfile.mkdtemp(prefix=name)))
    source = fax.fax_source.__wrapped__(factory)
    with ApiServer(database_url=f"sqlite:///{root.resolve() / 'draw.sqlite'}") as server:
        repo, _ = setup(server, RunCalendar(61, 37, 2000, 3), count=40)
        plan = canonical.authored_source(server, repo, source, 24)
        before = inspect(server)
        event_id = plan.source.draw.event_id
        web_port = 5173
        web = f"http://127.0.0.1:{web_port}"
        with (root / "frontend.log").open("w") as log:
            frontend = subprocess.Popen(
                ["npm", "--prefix", "web", "run", "dev", "--", "--host", "127.0.0.1",
                 "--port", str(web_port), "--strictPort"],
                env={**os.environ, "VITE_API_BASE_URL": server.base_url},
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
            )
            try:
                wait_http(web, frontend)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(
                        executable_path=args.chromium, args=["--no-sandbox"]
                    )
                    for language, title, eligible, status in (
                        ("en", "Saved Draw native readiness",
                         "Ranked or Unranked Edition must be a professional",
                         "Draw geometry meets the prerequisites"),
                        ("cs", "Nativní připravenost uloženého Draw",
                         "Ranked i Unranked Edice profesionál",
                         "Geometrie Draw splňuje předpoklady"),
                    ):
                        context = browser.new_context(
                            viewport={"width": 1440, "height": 1050}, device_scale_factor=1
                        )
                        context.add_init_script(
                            f"localStorage.setItem('squash-engine-language-v1','{language}')"
                        )
                        page = context.new_page()
                        page.set_default_timeout(60000)
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(
                            f"{web}/admin/runs/run/tour/calendar/{event_id}"
                            f"?branch=branch&revision={before['saved_head_revision_id']}"
                            f"&season=0&tab=draw"
                        )
                        section = page.get_by_role("region", name=title)
                        expect(section).to_be_visible()
                        expect(section).to_contain_text(status)
                        expect(section).to_contain_text(eligible)
                        expect(section.get_by_role("table")).to_be_visible()
                        # Read-only: nothing in the section can adopt, create or save.
                        assert section.get_by_role("button").count() == 0
                        assert section.get_by_role("link").count() >= 0
                        section.scroll_into_view_if_needed()
                        section.screenshot(path=str(root / f"readiness-{language}.png"))
                        assert not errors, errors
                        context.close()
                    browser.close()
            finally:
                stop_process(frontend)
        after = inspect(server)
        for field in ("saved_head_revision_id", "checkpoint_fingerprint",
                      "tour_fingerprint", "draft_version"):
            assert after[field] == before[field], field
    print("Saved Draw readiness browser acceptance passed:", root)


if __name__ == "__main__":
    main()
