# World Package Timezone Area registry writes

Sonar input `AaGB5oi4kbvvLNhyeN1j` (`pythonsecurity:S2083`) points to
`WorldPackageCountriesService.replace_timezone_areas`. The original report's
broad file-content traversal claim is not itself proof: registry identifiers
and package-owned metadata paths already have independent validation.

A concrete adjacent write defect is reproducible. The method opened the fixed
package-local `.timezone_areas.json.tmp` with truncation. A pre-existing symlink
there redirected writes outside the package; a regular unrelated file at that
name was overwritten and removed. This requires control over files within an
editable custom package, followed by an ordinary Admin registry update. It is
not a claim of unauthenticated remote code execution or compromise from API
strings alone. Package filesystem symlink isolation is an existing repository
invariant (`test_codeql_security_boundaries.py`).

The replacement creates its own exclusive, unique temporary file in the
registry directory. Both installation and byte-exact rollback use that path;
only that operation's own temporary file is cleaned up. Symlinked destinations
and registry directories are rejected. Validation failure removes a newly
created registry or restores the exact previous bytes. Failure before the
atomic replacement leaves the original untouched. Existing JSON formatting,
optimistic fingerprint, schema/reference validation, read-only built-in rules
and API results are preserved. This does not add cross-process locking or
claim to defeat arbitrary hostile concurrent replacement of ancestor directories.

Five focused regressions cover unrelated regular temporary files, a temporary
symlink to an external sentinel, validation rollback for missing/existing
registries and an injected installation failure. The first two fail against
the original implementation. The legitimate production registry roundtrip and
HTTP contracts remain part of the owning package checks.

The broader World Package suite also exposed an obsolete clone test: the generic
clone API now reports a missing built-in source as a structured HTTP 200 failure,
whereas that test expected an old hard-coded 404 and used the repository's real
World Package directory. It now uses a disposable FAX-only registry and verifies
the missing-source failure, absence of any target, and an unchanged source tree.
No clone runtime behavior changed and no acceptance test was skipped.

Hosted relevant checks on the final head remain required before owner merge.
This is one bounded advisory-derived fix, not completion of all 296 findings or
full pre-alpha certification. Owner alone merges; no auto-merge.

Final local validation: all 138 owning-package, actual HTTP and filesystem
boundary cases passed together in 88.38 seconds, including all five new
regressions. Scoped E9/F/I lint, Python compilation and whitespace checks pass.
Full-file Ruff additionally reports five unchanged baseline warnings outside
the changed code; this fix does not broaden into their cleanup.
