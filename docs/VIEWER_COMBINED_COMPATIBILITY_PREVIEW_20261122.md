# Viewer integration compatibility preview — 22 November 2026

> **DIAGNOSTIC ONLY — DO NOT MERGE.** This synthetic tree overlays the exact changed file blobs from 14 independently open Viewer PRs onto an unchanged snapshot of `buuk 71f03fb9242427d3dbc46d9106d58d21442df98c`. No original PR or `buuk` file is changed.

## Frozen components
- PR #1844: 3 changed files
- PR #1845: 2 changed files
- PR #1846: 2 changed files
- PR #1847: 2 changed files
- PR #1848: 2 changed files
- PR #1849: 2 changed files
- PR #1850: 2 changed files
- PR #1851: 3 changed files
- PR #1852: 3 changed files
- PR #1853: 3 changed files
- PR #1854: 7 changed files
- PR #1855: 6 changed files
- PR #1856: 3 changed files
- PR #1857: 3 changed files

## What this preview can prove
- Every candidate's new or edited file appears at the same exact blob SHA as the original PR.
- No file-path overlap exists across all 14 candidate PRs, so this is a reliable **same-tree frontend compile/test smoke**.
- The Fast CI on this synthetic commit can detect combined TypeScript, module linkage, critical test and Vite bundle failures absent from individually green PRs.

## What it does NOT prove
- No real FastAPI/HTTP/SQLite/Chromium acceptance, ATP/FAX, W52/W80 adapter coverage, Saved correctness, or runtime routing/navigation smoke.
- Git textual merge ordering and GitHub protected merge requirements are **not** established by a synthetic overlay.
- Work still owns independent design, security and conflict integration review; Radim is the sole owner who can merge original PRs.
- This temporary diagnostic PR is not a merge queue. **Do not merge its large aggregate tree.**

File overlaps checked in this snapshot: **none**; 43 unique paths in 14 Viewer PRs.
