# Admin ranking candidates UI

Read-only UI: link from each branch, scoped history and URL-selected week detail, counted results and unpublished status. Uses the existing read-only API. Query keys include Run and Branch; no placeholder history is carried across branches. Empty, missing, invalid and error states are explicit. Names are not fabricated: the API supplies player IDs.

Validation after #698: 102 component tests passed across AdminRankingCandidatesPage and AdminRunBranchesPage, and TypeScript/Vite production build passed. Candidate coverage includes populated detail and award breakdown, provenance, branch isolation during loading, retry after failure, invalid coordinates, empty history and exact-week selection. Both suites are included in Fast CI. The ranking table uses the existing keyboard-focusable horizontal scroll region.

Dependencies installed successfully using npm 10 (matching CI), without lockfile changes. npm 11 previously failed on optional platform entries. Browser screenshot verification remains unavailable because the local Playwright browser is not installed; component tests use mocked API responses and do not constitute end-to-end backend verification. Backend publication and week advancement are unchanged.
