# Versioned effective country rating resolution — 12 October 2026

**Status:** Explicit `country_rating_resolution.linear_v3` for newly adapted Run World copies, without rewriting previously saved World, replay or source Package data.

The authored source format remains `country_rating_history.v2` and an explicitly marked 1–10 scale. Legacy 1–5 values keep their labels and numbers. New Run World adaptation copies history and sets `rating_resolution_version: country_rating_resolution.linear_v3` only when a real 1–10 history exists. The source directory is never rewritten. Absence of the marker retains the existing v2 nearest-year resolution on earlier saved snapshots. Old Country serialization omits the new optional field, protecting existing hash input. Unknown resolver versions are rejected.

At an exact historical year the effective value comes from that authored observation. Between two observations it interpolates linearly. Before/after history it holds the nearest endpoint, and one known point is used alone. Derived intermediate arithmetic uses Decimal from authored tenths and **four decimal places, ROUND_HALF_UP**. Browser matches using integer-tenths interpolation with exact half-up integer arithmetic. Example: 1990:4 and 2000:6 → 1995:5; 1990:4 and 1993:6 → 1991:4.6667. Original authored values are never rounded or added to history.

Effective provenance distinguishes exact, interpolated (two source years and values), one-sided fallback, legacy scalar without time and missing. The country chart shows only authored years. A World country is complete at a selected year only with exact-year population and six exact-year rating anchors; an available fallback number is not complete historical evidence. Population remains nearest-year, including earlier-year ties. Historic Run revisions remain fail-closed until their own historical projection is supported.

Validation scope: deterministic domain resolver and Pydantic round-trip tests, pure frontend projection/history tests, production CI. Full browser World acceptance, 50-season simulation, calibration and old snapshot migrations remain independent.
