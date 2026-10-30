# Portable Saved Branch archive v1 — implementation candidate

Base: `buuk` `9980628243f6ac637cb6ab803af1e4c632520849`.
One custom export of a selected Saved HEAD, complete reachable history and required
owner/Viewer/source dependencies; identity-preserving cold restore into an installation
where the identities and Run name are unused. This is neither the full Run archive
nor the compact snapshot. Other Master §24 modes remain pre-alpha requirements.

## Adapter audit and implementation boundary

The repository already has original Saved hash/owner/lineage verification,
physical native source proof validation, native fork aggregate persistence and
component capture/restore adapters. The missing boundary is a portable envelope,
closed dependency collection, independent validation, and atomic cold installation.
The implementation reuses those adapters; it does not serialize arbitrary tables,
execute imported SQL or remap sporting identities.

Frontend PR #1676 and all Entry validation/driver files are outside this change.
This candidate remains Draft until both real HTTP/SQLite transfer paths, adversarial
cases and applicable final-head acceptance have actually executed successfully.
