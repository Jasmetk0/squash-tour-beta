# Ranked / Unranked Tournament Edition V1

This focused slice stores explicit `ranked` / `unranked` identity and an effective ranking-points table on each Season Calendar event (the current Tournament Edition record). A newly built Edition copies and normalizes the currently resolved points distribution; later edits to category/template points therefore do not rewrite it.

Completeness is operation-scoped. A Ranked Admin Draft can be persisted incomplete. Its required keys are derived from its actual main and Qualification draw sizes, and every required value must be a non-boolean integer at least zero. Lifecycle, ranking-dependent entry generation, and event simulation reject an incomplete Ranked Edition before mutation. Publication/announcement has no authoritative mutation command in the current architecture; the lifecycle prerequisite is exposed for that future command rather than inventing a publication boolean.

Unranked Editions run the normal match/result/history pipeline, but their persisted point-award package contains no per-player MSA/race award records and therefore inserts no ranking contribution (the current ranking foundation has not yet implemented Best N storage).

New Editions snapshot only values actually resolved from their configured inline table or points-table reference. Missing Main Draw values remain missing. Qualification keys are required only from the already established stage vocabulary; no numerical Qualification calibration or additive Qualification/Main Draw scoring is introduced here. The deeper component model remains deferred.

## Compatibility boundary

Calendar records persisted before this schema have neither Edition field. They retain the pre-V1 Ranked behavior through `ranking_configuration_legacy=true`, including the existing points resolver. Newly built or Admin-edited Editions persist `ranking_configuration_legacy=false`, explicit status, and a copied table. Category is never used to infer status. Status/table edits fail closed after the Edition status leaves `planned`; retroactive ranking-history rewriting is intentionally unsupported.

## Deferred

Season-to-season Category table inheritance, additive Qualification/Main Draw scoring redesign, explicit public-announcement command wiring, Best N storage redesign, and retroactive status/history rewrites remain separate slices.
