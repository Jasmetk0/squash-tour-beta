# Parallel PR overlap audit (read-only)

The repository frequently has multiple Draft PRs on `buuk`. Before starting an
independent slice, inspect current PRs and use this script to find **identical
file paths** touched by more than one open PR. It does not replace review of
semantic dependencies and does not decide merges.

```powershell
$env:GITHUB_TOKEN = "<personal token with read-only repository access>"
python scripts/audit_pr_overlap.py --repo Jasmetk0/squash-tour-beta --base buuk
python scripts/audit_pr_overlap.py --candidate-paths planned-files.txt --output overlap.json
```

`planned-files.txt` is one repository-relative file path per line (blank lines
and `#` comments ignored). Output includes PR numbers, exact HEAD SHAs, every
pair with shared files, candidate overlaps, and explicit limits. `--output`
creates a **new** JSON; never overwrites one. No flag ever writes to GitHub.

With `--offline snapshot.json`, use a historical fixture such as
`{"prs":[{"number":1,"title":"example","base":"buuk","head_sha":"<40-hex>","files":[{"filename":"a.py"}]}]}`.
It is always marked `source: offline` and never claims current GitHub state.
Live collection reads every open PR and all its pages, rechecks each HEAD after
reading file lists, and aborts instead of emitting a partial report if PR
contents change, a response is missing, or GitHub rate limits access.

**Safety:** Only paths are compared. A renamed file occupies both old and new
paths. An identical path does not prove a Git merge conflict; separate paths
can still have hidden API or semantic conflicts. A report is momentary evidence,
not a lock preventing subsequent edits. Do not store secrets in reports or commit
personal GitHub tokens.

Focused check: `python -m pytest -q tests/tools/test_audit_pr_overlap.py`.
