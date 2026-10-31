# R001 — source manifest and preservation notes

| File | Provenance | What is preserved | Limitation |
| --- | --- | --- | --- |
| `BRIEF.md` | Research programme (ChatGPT) | First scope, questions and guardrails | Not a scientific result |
| `GEMINI_ORIGINAL_REPORT_TEXT_EXTRACT.txt` | User-provided `Plán výzkumu talentů ve squashi.docx`, 38 pages | Searchable, full available **text extraction** from the initial Gemini Deep Research report | Equations, images and page layout from original DOCX are **not** faithfully preserved; original DOCX **not committed** |
| `GEMINI_SELF_AUDIT_01.txt` | User-provided `Vložený text(7).txt` | Full plain-text critical audit produced by Gemini | Claims and math are not independently verified |
| `GEMINI_MASTER_ALIGNMENT_02.txt` | User-provided `Vložený text(8).txt` | Full plain-text follow-up alignment after Gemini was shown two project documents | Not a full Master or source-code audit |
| `REVIEW_AND_HANDOFF.md` | ChatGPT synthesis, 2026-10-31 | C1–C4 candidates, non-adoptions, risk notes and pending Work review | Editorial interpretation, NOT evidence of implementation or scientific peer review |

**Source policy:** Keep the original DOCX outside this repository for any equation/image-level review; do not replace original math with missing or guessed formulas from the text extraction. Independent source/DOI verification remains outstanding. If the original binary is later archived, add it through a separate explicit review (respecting licences, file size and Git history) and update this manifest. No claim of scientific or product approval is implied by storage.

**Research status:** `RESEARCHED` (received and archived); **NOT `VERIFIED`**.
