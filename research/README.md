# Squash Engine Research — evidence before decisions

This directory is a long-lived research library for **all planned versions** of Squash Engine: pre-alpha, alpha, beta, 1.0 and later. It is **not** a second Master, not an implementation registry and not a list of approved features.

## Authority

Follow [AGENTS.md](../AGENTS.md) and the existing documentation precedence. The canonical product authority remains [SQUASH_ENGINE_MASTER_VISION.md](../SQUASH_ENGINE_MASTER_VISION.md) and newer explicit owner decisions. [CURRENT_STATE.md](../CURRENT_STATE.md) is implementation evidence, not proof of everything envisioned; [ROADMAP.md](../ROADMAP.md) summarizes delivery dependencies.

A study must **never** silently convert a `[LATER]`, `[OPEN]`, `[PROVISIONAL]` or research hypothesis into a `[DECIDED]` pre-alpha requirement. Only the product owner can accept product changes. ChatGPT Work coordinates assessment and any later proposal for canon/implementation. AI-generated research is subject to independent verification.

## Workflow

1. **Brief** — a narrow research question, authoritative repository inputs, candidate external sources and explicit exclusions.
2. **Research** — source-backed findings; separate empirical facts, cross-sport analogies, modelling assumptions and creative ideas. Include original links, publication years and uncertainty.
3. **Verify** — check source authenticity, suitability, calculation methods, contradictions and applicability to the fictional *globally popular squash* world. Do not claim runtime tests without executed evidence.
4. **Review** — reconcile with the latest Master and relevant current code; note conflicts and alternatives. A reviewer may reject unsupported conclusions.
5. **Owner decision** — if needed, ask the owner to accept, revise, defer or reject a proposal; record that decision in the appropriate canonical document through a separately reviewed change.
6. **Apply and measure** — only after approval, hand off well-bounded implementation/calibration tasks to the normal development workflow and evaluate measured simulation results.

This process can inform current or future versions. A study marked *future candidate* is not a pre-alpha commitment.

## Research status labels

- **PLANNED** — scope prepared, research not yet delivered.
- **RESEARCHED** — evidence and conclusions submitted, not yet independently checked.
- **VERIFIED** — sources and reasoning independently checked; this is **not product approval**.
- **OWNER DECIDED** — an explicit owner decision exists, linked to the canonical record.
- **CLOSED** — study archived, superseded or rejected with reason.

These are **research workflow statuses**, not Master product statuses.

## Storage and quality rules

- [INDEX.md](INDEX.md) tracks one research ID per topic.
- Store brief and reviewed Markdown summaries in `studies/<ID>-<slug>/`; use [templates/STUDY_TEMPLATE.md](templates/STUDY_TEMPLATE.md) for reports.
- Retain source URLs, access dates, licence/quotation limitations, source version, study date, reviewer and evidence confidence. Distinguish facts from speculative mechanisms and proposals.
- Raw research or large proprietary datasets should remain externally referenced when appropriate; do not dump massive generated reports, copyrighted studies or duplicate Earth datasets into git.
- Do not change `config/earth_research/`, simulation behaviour, Master or unrelated code as part of research capture.
- Gemini is one research contributor, **not** a canonical authority or required future tool.
- If the researcher cannot read a file (e.g. sees ZIP/DEFLATE bytes), state that limitation; provide narrow, plain-text source excerpts instead of inventing a repository audit.

## Primary criterion

Prefer few useful, well-verified findings that can change design, calibration or test plans over a large volume of unreviewed AI prose.
