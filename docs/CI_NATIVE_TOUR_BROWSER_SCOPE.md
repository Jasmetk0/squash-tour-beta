# Native Tour client edits and unrelated browser runs

This is a CI scheduling change, not a sporting/runtime or Master decision.
Base: `buuk` `93a3f946e86af8265b8e7539d6c6ffcd174f3282` (merged #1547).
The separate career-record PR #1548 is untouched.

## Observed cause

#1548 at `a858bcdad30df3d928625b99cbd0fccf6793136a` adds
`inspectCalendarTourRecords` to the shared frontend API client. That five-line
addition triggers six legacy hybrid browser workflows as well as the native Tour
acceptance. The legacy scenarios cover ranking closure, two-round championship,
real hybrid week advancement, second-week Full Simulation, same-parent restart,
and the Week-61 human Save boundary. They do not call native Tour wrappers.

Cancellation of superseded PR workflows already exists. This change addresses
unnecessary scenario selection, not runner queue latency or native replay speed.

## Conservative decision boundary

Each of the six existing jobs retains its name and complete browser scenario.
After frontend dependency installation it runs the selector's tests and examines
the **PR base versus the actually checked-out commit**, including both versions
of the production frontend consumer tree. Git content is read in batches.

A skip requires all of these:

- The changed files stay within the bounded native Tour source/test/doc scope.
- The shared client differs only in isolated exported native Tour functions
  (or insignificant leading/trailing trivia). Every other top-level declaration
  remains textually identical; imports, HTTP transport and eager initialization
  are never classified as native wrappers.
- Shared client code does not refer to those native names. Only the dedicated
  `CalendarTourPanel.tsx` may consume them. Non-explicit client imports/reexports,
  runtime dynamic client access and unknown module indirection force a full run.
- The exact workflow path filters are recognized. Other scenario sources,
  workflow/selector changes and frontend dependencies force a full run.

Manual dispatch always runs. Missing base objects, unavailable Git data, parse
errors and unfamiliar structures fall back to running; a broken selector/test
step fails the job rather than producing a successful skip. Summaries distinguish
selection from actual browser execution and identify the compared commits and
isolated functions.

The native Tour API, native season API and native browser workflows are unchanged.
Full release gates are unchanged. No match count, fixture population, assertion,
browser deadline or backend integrity check was reduced.

## Verification

Local `node --test web/scripts/ciHybridBrowserImpact.test.mjs` covers parser,
transport/side-effect changes, renamed/deleted paths, Git base availability,
actual CLI outputs, consumer aliases/reflection and conservative fallbacks.
The Git fixture includes UTF-8 content to exercise byte-sized batch parsing.

Against the actual #1548 commit and its real base, all six workflows select out
the unrelated scenario. Local selection took approximately 0.96–1.25 seconds
per workflow, excluding dependency installation. This is not a hosted end-to-end
time saving measurement. Changes to shared backend/frontend/config/test support
still select the complete browser.

The selector tests run before browser selection in all six workflows. Because
this PR changes the selector/workflows themselves, **all six full browser
scenarios must run on its final head**. Record their actual results in the PR;
do not claim this document as evidence of green hosted acceptance.
