# Pre-alpha FAX 80-Edition acceptance Calendar source

## Purpose

Provide a deterministic first-season Calendar source for the mandatory Master v72 copied-FAX release test.

This source is **not final FAX sporting canon**. It exists to exercise the production tournament pipeline at the decided scale while keeping sporting content decisions separate.

## Construction

- reads the existing active `WORLD_TOUR` Tournament Templates,
- currently uses the canonical Platinum 32 and Gold 24 template authorities,
- instantiates exactly 80 World Tour Editions across SW1–SW61,
- distributes Editions evenly so no season week has more than two of these reference events,
- preserves draw geometry, qualification geometry, seeds, WC/BYE counts, points source, host, region, duration and template snapshots,
- validates the resulting events through the existing `SeasonCalendarService.validate_calendar_events` boundary,
- emits the normal `calendar-2000-2001` canonical Package document shape.

Every reference Edition is explicitly marked by `event_level_overrides.pre_alpha_release_fixture=true` and the Package provenance contains `non_canonical_release_fixture=true`.

## Integration

The copied-FAX Preview → Materialize API now uses this source instead of requiring a separately persisted legacy season calendar. World Package state still comes from the reviewed World source and all resulting state becomes Run-owned through the ordinary Package + Saved Revision boundaries.

## Next

Use the materializer with this 80-Edition source to build the first persisted 1,000-player release fixture, then begin the long acceptance runner. Any missing ranking/entry/draw preparation should be fixed through existing canonical authorities rather than by simplifying this calendar.
