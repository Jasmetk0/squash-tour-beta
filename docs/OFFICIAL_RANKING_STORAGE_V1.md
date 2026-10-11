# Official Ranking candidate storage V1

Adds `official_ranking_candidates` to the existing SQLAlchemy Base metadata.
Existing schema creation adds this table without replacing legacy snapshots.
No endpoint or Viewer read path is switched to this table by this increment.

`OfficialRankingCandidateStore` takes the caller's Session. `append` validates
the snapshot, Run/Branch identity and read-only flags, then flushes without
committing. The future Week Transition unit of work can therefore commit or
roll back the candidate with its other state changes. A candidate is not an
authoritative publication or an advancement of the Run clock.

The first candidate requires explicit parentless bootstrap. Later candidates
must follow the stored head by exactly one week, including season rollover,
and link its fingerprint. Identical retries return existing content; conflicting
content for the same week is rejected without overwrite. Database primary-key
uniqueness protects concurrent inserts. On an IntegrityError or lock conflict,
the caller must roll back and retry the entire transaction; this adapter never
partially commits or hides database failures.

History reads validate all locally stored records oldest first: identity, week,
payload integrity and previous fingerprint. Missing internal/first ancestors
fail closed. Empty histories are valid and there is no independent trusted
terminal-head manifest here: deletion of the tail, or malicious coordinated
replacement of payload and metadata, requires the future revision/publication
anchor to detect. This is not an authentication mechanism.

Fork bootstrap is rejected until an ancestry adapter exists. Full source
provenance, discipline, corrections, historical first-publication resolution,
Saved Revision/restore/export integration and atomic Week Transition publication
remain follow-ups. No sport rules, simulation calibration or Master changes.

Verification uses a disposable file-backed SQLite database: commit/reload,
Week 61 rollover, exact retries, conflicting candidates, bootstrap/gap guards,
scope/read-only/fork isolation, corrupt payload/hash/missing ancestor rejection,
and rollback of both candidate and another transition write. Domain ranking
tests remain separate from these persistence integration tests.
