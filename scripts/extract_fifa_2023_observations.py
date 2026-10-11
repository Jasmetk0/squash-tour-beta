"""Extract national headline counts from the downloaded FIFA 2023 report.

Usage: python scripts/extract_fifa_2023_observations.py REPORT.pdf OUTPUT.json
Requires PyMuPDF only for this offline research operation, not at engine runtime.
Missing values remain null. This does not author any game ratings.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import fitz


def extract(pdf_path: Path) -> dict:
    observations = []
    with fitz.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf):
            text = page.get_text()
            if not all(label in text for label in ("COUNTRY", "INFORMATION", "PROFESSIONAL PLAYERS", "PROFESSIONAL CLUBS")):
                continue
            # In this edition the two national totals use large type in the top
            # right. Font-size/position avoids confusing league table rows with totals.
            words = page.get_text("words")
            totals = sorted((word for word in words
                             if 220 < word[1] < 350 and word[3] - word[1] > 70
                             and word[0] > 2200 and re.fullmatch(r"[\d,]+|-", word[4])),
                            key=lambda word: word[0])
            if len(totals) != 2:
                raise ValueError(f"Page {page_index + 1}: ambiguous headline counts")
            title_words = sorted((word for word in words
                                  if 250 < word[0] < 1500 and 90 < word[1] < 230
                                  and word[3] - word[1] > 45), key=lambda word: (word[1], word[0]))
            association = " ".join(word[4] for word in title_words).strip()
            if not association:
                raise ValueError(f"Page {page_index + 1}: missing association title")
            values = [None if word[4] == "-" else int(word[4].replace(",", "")) for word in totals]
            observations.append(dict(association=association, pdf_page=page_index + 1,
                                     professional_players=values[0], professional_clubs=values[1],
                                     identity_note=("Source labels this page KUWAIT but shows Kyrgyzstan flag/emblem; unresolved, do not join automatically." if page_index + 1 == 38 else None)))
    if len(observations) != 211:
        raise ValueError("Expected 211 association pages")
    return {
        "schema_version": "earth_source_observations.v1",
        "source_id": "fifa-professional-2023",
        "source_url": "https://digitalhub.fifa.com/m/2a5dc95026d9cf8a/original/FIFA-Professional-Football-Report-2023.pdf",
        "source_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "edition": 2023,
        "scope": "Men's professional football. Associations, not ISO countries. Missing is null, not zero.",
        "review_status": "extracted_not_reconciled",
        "published_global_totals": {"professional_players": 128694, "professional_clubs": 3986},
        "extracted_national_sums": {key: sum(row[key] or 0 for row in observations)
                                    for key in ("professional_players", "professional_clubs")},
        "limitations": "National-page sums differ from the published global headline. Preserve both; reconcile before calibration. Counts describe employment and do not directly measure six game attributes.",
        "observations": observations,
    }


if __name__ == "__main__":
    result = extract(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "observations"}, ensure_ascii=False))
