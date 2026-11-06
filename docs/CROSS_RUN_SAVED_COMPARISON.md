# Cross-Run Saved source comparison

This read-only Admin slice extends reachable Saved component comparison to two
independently selected Run/Branch contexts. It is **not completion of Master §7.8
or PAQ-021**: domain-level player, tournament, match/ranking differences and their
sporting-time presentation remain required subsequent work. No canon is deferred
or removed by this implementation boundary.

## Implemented boundary

Global Admin → Runs → Compare Saved Runs opens `/admin/compare-runs`. Each side
selects an actual Run, a Branch belonging to it, and one loaded reachable Saved
Revision. Older history pages load explicitly and must preserve their HEAD,
sequence, cursor and source identities. Selection never activates an Admin or
Viewer Branch. Compare is explicit; changing unsent choices hides older results.
Swap only swaps choices until Compare is pressed. A complete shared URL reloads
the same explicit pair. CS/EN and display filtering do not execute a new comparison.

`GET /admin/cross-run-compare` resolves each source through the existing validated
Saved-history boundary. A shared ancestor keeps its original revision Branch while
the selected Branch proves reachability. Missing/foreign sources return 404;
physical Saved/history corruption returns 409. No cached validation is manufactured
and no Working Draft or current Package substitutes for missing Saved content.

The response returns source metadata, changed Run/Branch fields and SHA-256
fingerprints of canonical JSON components. `null` is a stored value with a real
fingerprint; absent components have no fingerprint. Metadata includes explicit
before/after presence flags. `0`, `false`, empty strings, missing and null stay
distinct. Dictionary insertion order does not create false component differences.
Component payloads are not converted to large strings and labelled fingerprints.

The UI checks both response contexts, HEADs, revision hashes, original owners,
sequence/parent/schema and status consistency against independently loaded history
before displaying evidence. It does not match people across Runs by similar names
or infer sporting causality/time from opaque component hashes or Save timestamps.

## Validation and retained limits

Focused service contracts cover all four component statuses, canonical hashes,
null/missing/type distinctions and bounded fingerprint output. Actual HTTP/SQLite
integration creates Runs through production commands, tests both source error
paths, exact shared-ancestor scope and corruption after a warm read, and compares
all SQLite rows before/after browsing. A real HTTP test also uses a four-player
native sporting/Tour Saved source, restarts SQLite and rejects corrupted history.
None bypasses caches, hash checks or physical dependencies.

The dedicated workflow runs actual Chromium against production HTTP/SQLite and
the compiled UI, including both selectors, a shared ancestor under a different
selected Branch, explicit Swap/Compare, local filtering, CS/EN, URL reload,
SQLite restart and no mutation requests/row changes. Screenshots and JSON evidence
are retained. Mocked React tests are described separately and are not that gate.

History resolution currently inherits the existing complete-lineage validation
cost for each source. Component response hashes stay bounded, but this does not
prove long-Run latency/RSS bounds, streaming or full domain comparison. The complete
pre-alpha release/50-season acceptance remains separate. Master, sporting rules,
Saved writers and existing comparison/recovery authority are unchanged.

## Advisory Sonar review

Static review of the five annotations on repair commit `0398b48e` found no
confirmed vulnerability in this slice. This is a bounded annotation assessment,
not a complete security audit; no repository `SECURITY.md` was present.

| Sonar issue suffix | Assessment and evidence |
| --- | --- |
| `h0Sc` (pip build scripts) | Intended reviewed CI build: editable installation of this checkout requires its build backend. The workflow has only `contents: read` and no deployment or configured secrets. No injected command is established. |
| `h0Sb` (API traversal) | Test-only helper, fixed loopback origin, fixed routes and IDs created by the same disposable app; comparison parameters are URL encoded. It is not a production endpoint taking caller-supplied paths. |
| `h0Se` (npm lifecycle) | `npm ci` uses the checked-in lockfile; build lifecycle scripts, including esbuild, are intentional. No lower-trust command source is demonstrated. |
| `h0Sd` (unlocked Python resolution) | Valid reproducibility/supply-chain concern for separate coordinated review. Existing project dependency ranges are reused; no compromised or vulnerable resolved package is established here. |
| `h0Sa` (report path traversal) | The output directory comes from explicit `--artifacts`, literal `/tmp/cross-saved-evidence` in CI, with a constant `result.json` basename. Git/API/SQLite values become report content, never its destination. |

These findings are not suppressed and Sonar's gate is not weakened. The owner's
policy treats Sonar as advisory; its red aggregate is not a functional-test pass.
Ordinary dependency compromise remains possible in any build pipeline and is not
disproved by these static boundary observations.
