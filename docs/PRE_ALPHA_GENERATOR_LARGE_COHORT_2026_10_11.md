# Large initial cohort — scoped implementation and acceptance

Date: 11 October 2026. Product authority: Master v78, §§9.4–9.6, 27.19–27.20 and 31.33.

## Implementation boundary

The single production Run → Players generator supports a first-week 2000/01 preview of **1–1,000 players** through its saved Run-owned World. Backend request already permits up to 2,000, but the UI restricts to the capacity this PR explicitly covers. All generated rows and summaries belong to one exact seed/World/HEAD/draft/review fingerprint; table pagination of 50 visible rows is not an operation, group constraint or adoption subset. Search, sort and filters remain strictly visual. Keep remains one regeneration per base preview; it does not create persistent locks.

The production preview contract refuses duplicate player identities even when row counts match. The source ability 1–99 fields remain explicitly marked non-canonical, not invented 0–200 OVR. The preview itself never touches a Run. Only explicit Adopt stages the InitialWorld, and a separate deliberate Save persists an immutable Saved Revision; independent World snapshots and read-only built-in sources remain unchanged.

## Acceptance requirements and evidence boundary

The new focused real-browser workflow starts its own isolated backend and SQLite; enters through the Admin UI, copies and saves a World snapshot, previews 1,000, checks 50-row pagination, explicitly Adopts and Saves, enumerates all 20 pages of canonical Saved Players with exactly 1,000 distinct IDs, publishes the initial Official Ranking, restarts the backend process and verifies the same identities/order. It saves the trace and evidence artifact and fails on browser JavaScript errors or HTTP 5xx. Deterministic frontend component tests cover page changes/filters/Keep and no silent adoption. The existing `tests/api/test_earth_world_run_acceptance.py` already covers 1,000-player FIFA/ATP product generation, actual SQLite save/reopen and fork.

The workflow must finish green on the last commit before declaring this PR merge-ready. This is not a certification of a full-season simulation, official pre-alpha release or future-generation mechanics.
