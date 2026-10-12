# Country → Tournaments: immutable Saved Calendar editions

**Scope:** selected Run and Branch; in present mode, the selected Branch's immutable Saved HEAD; in historical revision mode, the exact requested reachable Saved Revision and its original branch ID for shared ancestry. A mutable Run Package draft and planning calendar library are never substitutes for saved Calendar evidence.

Country host selection uses `calendar.event.v1.payload.host_country` on each **edition**, not the host country attached to a tournament template. Each Run Calendar package must have matching `calendar.metadata.v1`; duplicate or malformed event identities, unsupported season or foreign scope fail closed. Season and week determine edition chronology. Current season, historical seasons and saved future plans are kept separate. No results, winners or Country Records are derived from a calendar's status.

The canonical live event detail currently validates only season 2000/2001; links are offered only for that supported present season with exact branch and calendar identifiers. Historical revision and other season links to mutable present-day detail are deliberately unavailable. Historical simulation checkpoints still require authoritative checkpoint → Saved Revision linkage and remain blocked independently of the World data year.

Tests cover season normalization, host-vs-template authority, immutable reads, multiple calendar packages, absent Calendar, and fail-closed scope/identity checks, plus Country tab UI mocking. Future separate slice: Country Records and authoritative published outcomes; eventual cross-season event detail.
