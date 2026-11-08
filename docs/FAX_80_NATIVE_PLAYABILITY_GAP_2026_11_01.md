# FAX 80-Edition source → native execution compatibility audit

## Why this matters

The existing Saved copied-FAX preparation proves 1,000 initial players and 80 *planned* World Tour Editions; isolated native MatchEngine tests prove four-player knockouts across weeks and Signed Seasons. These are different authorities. Together they do **not** prove a single 80-Edition FAX calendar is actually playable.

This read-only tool compares all 80 reference Calendar Editions against the legacy native v2 executor and separately reports the original source prerequisites for canonical Q/Main. It preserves exact source identity, templates, Year/Season weeks and all as-authored Category points. A structurally compatible event is still not proof of Entry, player validity or real play.

## Command

Run from the repository root: `python -m tools.audit_fax_native_playability --output fax-native-audit.json`

Optional input flags are `--templates`, `--category-points` and `--initial-native-week` (default 2, the documented currently integrated initial Tour owner). All inputs are read-only; the only write is the explicitly chosen JSON output path. Nonzero **exit code 2** means at least one FAX Edition is structurally blocked, so no system may call this a passed release gate.

The report schema is `fax_native_playability_gap_audit.v1`. It contains the original Calendar source fingerprint, all 80 original Edition IDs, categories and unchanged source geometry, missing stage values, per-Edition blockers and an aggregated matrix. `actually_played_edition_count_proven=0` states this tool did not execute any matches, not that no other Run has played any.

## Canonical Q/Main source prerequisites

Each row's `canonical_q_main_source_prerequisites` is separate from the old v2 verdict. It uses the physical Main bracket and each separate Q section to derive stages from the same mapping as canonical results and point awards. Gold24 needs `round_of_32` despite admitting only 24 players. A BYE followed by an initial loss still needs that first-round award. Gold's four four-player Q sections do not use `qualification_round`; Platinum's four six-player Q sections have eight physical slots each and do use it. An authored zero is valid; an absent, negative or non-integer value is not a zero.

On the original checked-in source, all 40 Gold Editions lack `qualification_winner`, `qualification_final` and `qualification_semifinal`. All 40 Platinum Editions also lack `qualification_round`. The source's Main awards cover the required stage keys for both shapes. The 35/51 expected real matches are geometry, not results or new execution evidence. This diagnostic changes no point values or canonical source fingerprints.

None of the 80 original Editions carries an explicit `native_announcement_week` override. The report checks presence, not validity, and gives only an upper bound for an in-Run announcement from the first match; Entry, WC or Draw can require an earlier date. `null` means no preceding in-Run week exists. `FAX-ACCEPT-WT-001` and `002` both start in SW1, so a Week-1 bootstrap alone cannot keep their dates and satisfy the full-week lead requirement. Preserving both dates needs an explicit pre-Run publication source or another owner-approved chronology. The audit does not create either, infer dates or move any Edition.

### Admin check for one Saved Draw

`GET /admin/runs/{run_id}/branches/{branch_id}/tournaments/{event_id}/draw/saved-native-preflight`
takes `season` and `expected_saved_revision_id`. It authenticates the current
Branch-owned Saved Calendar, Draw Input and Draw with the native feeder reader.
It returns the Saved revision, Draw and feeder plan fingerprints for review and
reports absent and invalid required point stages separately. It reads only the
authored Edition table and does not consult a live category registry or apply
default points. An unsaved or stale source returns a conflict.

`point_table_status=complete` means coverage of required stage keys only.
Same-week Ranked execution requires W61 and an existing following publication
week. Both Ranked and Unranked still need the normal adoption preview, which
validates schedule and announcement. This read does not adopt the Draw, publish
an Edition or award points.

## Legacy native v2 gap codes

| Code | Gap (not automatically repaired) |
| --- | --- |
| `main_field_not_supported_by_native_v2_executor` | Platinum 32/Gold 24 FAX Main sizes differ from the production native 4/8 full main-only knockout |
| `qualification_structure_not_modelled_by_native_v2` | Qualifier draw, slots and canonical qualification results are distinct from native main-only Entry |
| `wild_card_bye_geometry_not_losslessly_mapped` | Original WC/BYE capacity cannot be silently dropped or made into a 4-player field |
| `multiweek_edition_timing_not_losslessly_mapped` | Long-duration original template scheduling needs chronological mapping |
| `announcement_not_future_from_native_bootstrap` | Source SW1–3 cannot be announced in the future after current native bootstrap W2; no retrospective mutation |
| `required_category_point_awards_missing` | Missing original Category award stages are not implicit zero rewards |
| `legacy_and_native_point_stages_need_explicit_mapping` | Round-of-16/32 point-stage names are not synonymous with the small native v2 stages |
| `native_v2_domain_rejected_event` | Actual native immutable domain constructor rejects a structurally tentative candidate |

Multiple gap codes can describe one source Edition. Native v3 group/hybrid is **not** automatically a faithful replacement for original FAX knockout format. This tool does not run real Entry/Draw/MatchEngine, create a Run, change Saved revisions, assign tournament results, determine unexplored policies or fill missing points.

## Test and release contract

Critical tests inspect the real 80-Edition source and canonical Calendar fingerprint without creating any registry. Synthetic positive/negative fixtures probe the actual native v2 domain constructor for the **limited** supported 4-player case. Adversarial cases include duplicate IDs, foreign seasons and wrong source calendars. A Draft-inclusive hosted workflow runs the exact source audit, expects explicit exit code 2 for current incompatibility, and uploads the truthful machine-readable JSON. A successful test of detection is not a successful release gate.

The next implementation dependency is a reviewed accurate FAX 24/32 Main/Qualification/points/timing bridge with provenance and owner-approved policy where unresolved. Only then can the real 1,000-player, 80-played-Edition FAX season be claimed. This report must not be treated as the bridge itself.


## Verified result on the actual checked-in FAX source (2026-11-01)

The dedicated CI run [41349933045](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/41349933045) executed all six new tests against the real source, ran the report command and retained its exact 80-event JSON as [artifact 13100881247](https://github.com/Jasmetk0/squash-tour-beta/actions/runs/41349933045/artifacts/13100881247).

Canonical Calendar fingerprint: `e2150e66eef92943b56b2d22f3de26b8fe6c161669bd5d24c770c516f560e197`.

| Observed source attribute / blocker | Editions |
| --- | ---: |
| Original source Editions / structurally blocked | **80 / 80** |
| Original GOLD / Platinum templates | **40 / 40** |
| GOLD Main 24 / PLATINUM Main 32 | **40 / 40** |
| Qualification size 16 / 24 | **40 / 40** |
| Main full-field unsupported by current native v2 4/8 | **80** |
| Qualification incompatible with native main-only executor | **80** |
| WC/BYE original geometry not losslessly mapped | **80** |
| Category point stages missing | **80** |
| Legacy ↔ native point-stage mapping not lossless | **80** |
| Announcements too early from the specified W2 bootstrap | **4** |
| Actually played Editions proven by this audit | **0** |

The four early announcement source identities are `FAX-ACCEPT-WT-001` and `002` (SW1), `003` (SW2) and `004` (SW3). These counts are the observed source snapshot, **not promises** about future templates or an owner's authored new point configuration. Each issue count is independent and can overlap another category. The source is explicitly a release fixture and not final FAX sporting canon.

**Decision implication:** prioritize an authenticated, historically versioned 24/32 Main and Qualification knockout bridge plus an honest initial-announcement strategy before claiming any 80-played-Edition reference acceptance. Missing point awards require existing owner authority, not a synthetic zero default.
