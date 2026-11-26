"""Research helper: extract dated ATP Tour format evidence from English Wikipedia.

This is a secondary-source tool, not a runtime or CI dependency. It reads the
season article ``<year> ATP Tour``, then the per-event article and the men's
singles article of every ATP Tour 250/500/Masters 1000, Next Gen and Finals
event.  For each page it records the revision id (``wgRevisionId``), the
retrieval date and the SHA-256 of the exact bytes received.  Nothing is
inferred: a field that the pages do not state is left ``null`` and listed in
``open_evidence``.

Usage (needs network access to en.wikipedia.org)::

    python -I -m scripts.build_atp_wikipedia_season_evidence 2019 --raw RAW_DIR --out OUT.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"], 1)}
TIER_RE = r"ATP (?:World )?Tour (?:250|500|Masters)|ATP (?:World Tour )?Finals|Next Generation"
# Events outside the ATP Tour main-tour scope; also dropped later by matching to canonical Series.
EXCLUDED_RE = (r"Australian Open|French Open|Wimbledon|US Open|Davis Cup|Hopman Cup|Laver Cup|Fed Cup|"
               r"Olympic|World Team Cup|Grand Slam Cup|Challenger|Hopman|United Cup|ATP Cup")
CATEGORY_WORDS = (
    ("ATP Tour Masters 1000", "atp_masters_1000"), ("ATP Tour 500", "atp_500"),
    ("ATP Tour 250", "atp_250"), ("Next Generation ATP Finals", "next_gen_finals"),
    ("ATP Finals", "atp_finals"))


def wiki_url(title: str) -> str:
    return "https://en.wikipedia.org/wiki/" + urllib.parse.quote(html.unescape(title), safe="_(),'%")


def fetch(url: str, raw_dir: Path, delay: float = 1.0) -> tuple[bytes, str]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(url.encode()).hexdigest()[:16] + ".html"
    path = raw_dir / name
    if not path.exists():
        code = ""
        for attempt in range(6):
            res = subprocess.run(
                ["curl", "-sS", "-m", "60", "-L", "-A", "Mozilla/5.0", "-o", str(path),
                 "-w", "%{http_code}", url], capture_output=True, text=True, check=False)
            code = res.stdout.strip()
            time.sleep(delay)
            if code != "429":
                break
            time.sleep(15 * (attempt + 1))
        if code != "200":
            path.unlink(missing_ok=True)
            raise RuntimeError(f"{url}: HTTP {code}")
    return path.read_bytes(), url


def to_text(raw: bytes) -> str:
    t = raw.decode("utf8")
    t = t[t.find('id="mw-content-text"'):]
    t = re.sub(r"<(script|style).*?</\1>", "", t, flags=re.DOTALL)
    t = re.sub(r"</(p|tr|h\d|li|div)>", "\n", t)
    t = re.sub(r"</t[dh]>", " | ", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", t))


def revision(raw: bytes) -> int | None:
    m = re.search(rb'"wgRevisionId":(\d+)', raw)
    return int(m.group(1)) if m else None


_DATE = r"(\d{1,2})(?: (%s))?(?: (\d{4}))?"  # day [month] [year]


def _one_range(seg: str, year: int) -> tuple[str, str] | None:
    seg = seg.replace("\u2013", "-").replace("\u2014", "-").replace("\xa0", " ")
    mons = "|".join(MONTHS)
    m = re.search(rf"(\d{{1,2}})(?: ({mons}))?(?: (\d{{4}}))? ?- ?(\d{{1,2}}) ({mons})(?: (\d{{4}}))?", seg)
    if not m:  # US order: "February 18-24", "July 15 - July 21", "March 4-17"
        u = re.search(rf"({mons}) (\d{{1,2}}) ?- ?(?:({mons}) )?(\d{{1,2}})", seg)
        if not u:
            return None
        m1, d1, m2, d2 = u.groups()
        m2 = m2 or m1
        y2 = year
        y1 = y2 - 1 if MONTHS[m1] > MONTHS[m2] else y2
        return (dt.date(y1, MONTHS[m1], int(d1)).isoformat(), dt.date(y2, MONTHS[m2], int(d2)).isoformat())
    d1, m1, y1, d2, m2, y2 = m.groups()
    m1 = m1 or m2
    y2 = int(y2) if y2 else year
    y1 = int(y1) if y1 else (y2 - 1 if MONTHS[m1] > MONTHS[m2] else y2)
    return (dt.date(y1, MONTHS[m1], int(d1)).isoformat(), dt.date(y2, MONTHS[m2], int(d2)).isoformat())


def parse_dates(text: str, year: int) -> tuple[str, str] | None:
    """Parse the infobox ``Date`` row (men's part when women share it)."""
    m = re.search(r"\nDate \| ([^\n]+?) \|", text)
    if not m:
        return None
    cell = m.group(1)
    if "(men)" in cell:
        before = cell.split("(men)")[0]
        cell = before.split("(women)")[-1]
    return _one_range(cell, year)


def category_of(text: str) -> str | None:
    m = re.search(r"part of the (ATP (?:World )?Tour (?:250|500|Masters 1000)|ATP (?:World Tour )?Finals|Next Generation ATP Finals)", text)
    if not m:
        return None
    return dict(CATEGORY_WORDS)[m.group(1).replace("World Tour", "Tour").replace("ATP Tour Finals", "ATP Finals")]


def parse_singles(text: str) -> dict:
    out: dict = {}
    m = re.search(r"\nDraw \| (\d+) \((\d+) Qualifiers.*?Q / (\d+) Wild", text)
    if m:
        out["main_draw_players"] = int(m.group(1))
        out["qualifier_places"] = int(m.group(2))
        out["wild_cards"] = int(m.group(3))
    else:
        m = re.search(r"\nDraw \| (\d+)", text)
        out["main_draw_players"] = int(m.group(1)) if m else None
    m = re.search(r"\nSeeds \| (\d+)", text)
    out["seeds"] = int(m.group(1)) if m else None
    bye = re.search(r"[^.\n]*bye[^.\n]*\.", text[:6000], flags=re.IGNORECASE)
    out["bye_statement"] = bye.group(0).strip() if bye else None
    out["lucky_losers_named"] = len(re.findall(r"lucky loser", text[text.find("Qualifying"):], flags=re.IGNORECASE)) > 0
    out["has_qualifying_draw"] = "\nQualifying draw" in text or "\nQualifying Draw" in text
    return out


SCHEDULE_IDS = ("Schedule", "Calendar", "Schedule_and_results", "January")


def _schedule_start(page: str) -> int:
    for sid in SCHEDULE_IDS:
        i = page.find(f'id="{sid}"')
        if i >= 0:
            return i
    return -1


def build(year: int, raw_dir: Path) -> dict:
    season_raw = None
    for title in (f"{year}_ATP_Tour", f"{year}_ATP_World_Tour"):
        season_url = f"https://en.wikipedia.org/wiki/{title}"
        try:
            season_raw, _ = fetch(season_url, raw_dir)
        except RuntimeError:
            continue
        if _schedule_start(season_raw.decode("utf8")) >= 0:
            break
    if season_raw is None:
        raise RuntimeError(f"no season article for {year}")
    season = season_raw.decode("utf8")
    start = _schedule_start(season)
    seg = season[start:start + 2_500_000]
    rows = []
    for tr in re.findall(r"<tr.*?</tr>", seg, flags=re.DOTALL):
        cells = re.findall(r"<t([dh])([^>]*)>(.*?)</t[dh]>", tr, flags=re.DOTALL)
        if not cells:
            continue
        label = html.unescape(re.sub(r"<[^>]+>", "", cells[0][2])).strip()
        first = cells[1][2] if re.match(r"^\d{1,2} [A-Z][a-z]{2}", label) and len(cells) > 1 else cells[0][2]
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", first))).strip()
        if len(text) < 20:
            continue
        if re.search(EXCLUDED_RE, text) or re.search(EXCLUDED_RE, first[:600]):
            continue
        base = r'href="https://en\.wikipedia\.org/wiki/(' + str(year) + "_"
        main = re.search(base + r'[^"#?]*?)"', first)
        sing = re.findall(base + r"""[^"#?]*?(?:_Singles|_singles|Men%27s_singles)[^"#?]*?)\"""", first)
        sing += re.findall(base + r"""[^"#?]*?_–_(?:Men's_)?[Ss]ingles)\"""", first)
        if not main:
            continue
        rows.append({"schedule_text": text[:160], "main": main.group(1) if main else None,
                     "singles": sing[0] if sing else None, "schedule_format": re.search(r"(\d+)S(?:/(\d+)Q)?", text)})
    events = []
    for r in rows:
        if not r["main"]:
            continue
        item = {"schedule_text": r["schedule_text"], "wikipedia_main": r["main"]}
        try:
            raw, url = fetch(wiki_url(r["main"]), raw_dir)
        except RuntimeError:
            continue  # article does not exist
        txt = to_text(raw)
        item["main_source"] = {"url": url, "revision_id": revision(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                                "bytes": len(raw)}
        item["wikipedia_dates"] = parse_dates(txt, year)
        item["wikipedia_category_id"] = category_of(txt)
        sf = r["schedule_format"]
        item["schedule_main_capacity"] = int(sf.group(1)) if sf else None
        item["schedule_qualifying_draw"] = int(sf.group(2)) if sf and sf.group(2) else None
        if r["singles"]:
            try:
                raw, url = fetch(wiki_url(r["singles"]), raw_dir)
            except RuntimeError:
                raw = None
            if raw is not None:
                item["singles_source"] = {"url": url, "revision_id": revision(raw),
                                          "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                item["singles"] = parse_singles(to_text(raw))
        events.append(item)
    return {"season_source": {"url": season_url, "revision_id": revision(season_raw),
                              "sha256": hashlib.sha256(season_raw).hexdigest(), "bytes": len(season_raw)},
            "events": events}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("year", type=int)
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    data = build(a.year, a.raw)
    data["retrieved_at"] = dt.datetime.now(dt.UTC).date().isoformat()
    a.out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    print(len(data["events"]), "events")


if __name__ == "__main__":
    main()
