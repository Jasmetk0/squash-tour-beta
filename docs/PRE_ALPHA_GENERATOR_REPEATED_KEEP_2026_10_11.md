# Repeated Session Keep — preview-only lineage (candidate)

Authority: Master v78 §§9.6, 27.20, 31.33; AGENTS.md; docs/PRE_ALPHA_TEST_POLICY.md.

## Request and reproducibility

`RunWorldInitialPoolPreviewRequest` accepts an optional `keep_history` containing **prior** regeneration steps, each with `seed`, `keep_from_seed`, `keep_from_preview_fingerprint` and sorted `keep_player_ids`. The current step continues to use the existing one-pass fields. The history is required only for a second or later Keep pass and is bounded to 16 recorded steps (17 total session regenerations). No player objects, stats, or permanent locks are accepted from the browser.

For every next preview, server reconstructs the previous preview on the current Run-owned saved World and verifies each exact fingerprint before allowing the current Keep identities. Breaks, stale World/content, wrong scope and malformed ID selections fail closed. Seed uniqueness is required *between consecutive passes*; replay is deterministic. Old first-preview and one-pass payload fingerprints are unchanged because an absent/empty history is omitted from fingerprint material, while new history is included and authenticated.

The frontend retains Keep checkboxes across successive regenerations and lets the user grow/reduce the selected subset. A changed pending selection blocks Adopt until another regeneration or restoration of the previously applied selection. The reviewed **whole batch** remains the only Adopt payload; display-only filters/page changes do not alter authority. Adopt into Working Draft and manual Save are separate; preview never writes to Run.

## Scope and limits

Session Keep locks are stripped from resulting generated players *before* preview and InitialWorld adoption. Later career updates are not frozen. No field-level locks, individual editable attributes, shared-group constraints, resumable proposal file, nested quotas or new travel mechanics are included. The temporary 17-step V1 request limit is protective rather than a gameplay constraint and can be lifted after a bounded replay design.

## Evidence required

Focused backend tests prove two and three authentic generations and stale/tampered ancestry rejections, unchanged old fingerprints and unlocked final adoption. Frontend tests ensure repeatable Keep and Adopt/Save separation. Real browser smoke tests first+second Keep with extra player preserved and then completes ranking, tournament and saved replay after restart. Every required final-head check must pass before merge.
