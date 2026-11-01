# Pre-Alpha FAX 80-Edition Calendar Audit

## Objective
Independent production-oriented audit of the reference FAX calendar containing exactly 80 World Tour Editions (`PRE_ALPHA_FAX_80_EDITION_CALENDAR.md`).

## Methodology
An automated acceptance test suite was created in `tests/acceptance/test_pre_alpha_fax_calendar_80_edition_audit.py` targeting `PreAlphaFaxAcceptanceCalendarSource`. This suite deterministically validates:
1. Source Edition identities, counts, and dates.
2. The fundamental difference between *created* 80 Editions and *actually played* 80 Editions.
3. The rejection of damaged or incomplete inputs, confirming that requirements are firmly checked by the application.

## Findings

### Exact Identity and 80 Edition Generation
The audit confirmed that `PreAlphaFaxAcceptanceCalendarSource` deterministically produces a season calendar containing precisely 80 Editions for `2000/2001`. Each edition is successfully populated with a unique identity spanning `FAX-ACCEPT-WT-001` through `FAX-ACCEPT-WT-080`, and properly affiliated with the `2000/2001` season label.

### Created vs. Played Editions Distinction
The generation process strictly emits Tournaments with the status `"planned"` and includes the explicit `pre_alpha_release_fixture=True` flag in event level overrides. This confirms the separation of concerns: the Calendar Source is solely responsible for creating and planning the 80 fixtures. It does not auto-advance their states, play matches, or mark them as completed/played.

### Rejection of Damaged/Incomplete Inputs
The source actively guards against corrupted environmental inputs, preserving clear negative evidence when underlying dependencies fail:
- **Invalid Season:** Attempting to build the calendar for an unsupported season (e.g., `"2001/2002"`) immediately raises a `ValueError`.
- **Missing Templates:** If the underlying `TournamentTemplatesConfigService` returns no active `WORLD_TOUR` templates, the generator accurately interrupts execution with a precise error stating `"Pre-alpha FAX acceptance calendar requires at least one active WORLD_TOUR template"`.

No existing sporting rules were modified or invented to make the audit tests pass. The pre-existing architecture accurately adheres to the 80 Edition FAX requirements.
