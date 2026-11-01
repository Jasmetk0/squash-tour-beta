# FAX 80-Edition source → native execution compatibility audit

## Why this matters

The existing Saved copied-FAX preparation proves 1,000 initial players and 80 *planned* World Tour Editions; isolated native MatchEngine tests prove four-player knockouts across weeks and Signed Seasons. These are different authorities. Together they do **not** prove a single 80-Edition FAX calendar is actually playable.

This read-only tool compares every one of the 80 actual reference Calendar Editions against the currently supported native knockout executable contract. It preserves exact source identity, templates, Year/Season weeks and all as-authored Category points. A structurally compatible event is still not proof of Entry, player validity or real play.

## Command

Run from the repository root: `python -m tools.audit_fax_native_playability --output fax-native-audit.json`

Optional input flags are `--templates`, `--category-points` and `--initial-native-week` (default 2, the documented currently integrated initial Tour owner). All inputs are read-only; the only write is the explicitly chosen JSON output path. Nonzero **exit code 2** means at least one FAX Edition is structurally blocked, so no system may call this a passed release gate.

The report schema is `fax_native_playability_gap_audit.v1`. It contains the original Calendar source fingerprint, all 80 original Edition IDs, categories and unchanged source geometry, missing stage values, per-Edition blockers and an aggregated matrix. `actually_played_edition_count_proven=0` states this tool did not execute any matches, not that no other Run has played any.

## Precise gap codes

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

