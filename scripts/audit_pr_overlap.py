#!/usr/bin/env python3
"""Read-only GitHub PR path-overlap audit; overlap is not a merge-conflict proof."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCHEMA = "pr_path_overlap_audit.v1"
REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _get(url: str, token: str | None) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "SquashEngine-PR-Overlap-Audit",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urlopen(Request(url, headers=headers), timeout=20) as response:
            return json.load(response)
    except (HTTPError, URLError, ValueError) as exc:
        # Never print request headers, authentication, or full exception bodies.
        raise ValueError("GitHub read failed; audit is incomplete (network, permissions or rate limit)") from exc


def _pages(repo: str, suffix: str, token: str | None) -> list:
    all_rows: list = []
    for page in range(1, 101):
        joiner = "&" if "?" in suffix else "?"
        url = f"https://api.github.com/repos/{repo}/{suffix}{joiner}per_page=100&page={page}"
        rows = _get(url, token)
        if not isinstance(rows, list):
            raise ValueError("Unexpected GitHub response; audit is incomplete")
        all_rows.extend(rows)
        if len(rows) < 100:
            return all_rows
    raise ValueError("GitHub pagination exceeded 10,000 entries; audit is incomplete")


def _files_for_pr(repo: str, number: int, token: str | None) -> list[dict]:
    rows = _pages(repo, f"pulls/{number}/files", token)
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"PR #{number} has no reliable file list")
    if len(rows) >= 3000:
        raise ValueError(f"PR #{number} reached GitHub\u0027s 3,000-file API cap; audit incomplete")
    return rows


def collect_live(repo: str, base: str, token: str | None) -> list[dict]:
    if not REPO_PATTERN.fullmatch(repo) or not base or "/" in base:
        raise ValueError("Expected owner/repo and a simple base branch name")
    # GitHub list-pulls endpoint includes every open PR; do not silently cap at a sample.
    raw = _pages(repo, "pulls?state=open", token)
    prs = []
    for item in raw:
        if not isinstance(item, dict) or item.get("base", {}).get("ref") != base:
            continue
        number, head = item.get("number"), item.get("head", {}).get("sha")
        if not isinstance(number, int) or not isinstance(head, str) or not head:
            raise ValueError("Invalid PR identity in live inventory")
        files = _files_for_pr(repo, number, token)
        # Re-read HEAD after collecting paged files: avoid mixed old/new file lists.
        fresh = _get(f"https://api.github.com/repos/{repo}/pulls/{number}", token)
        if not isinstance(fresh, dict) or fresh.get("head", {}).get("sha") != head:
            raise ValueError(f"PR #{number} changed during the audit; retry")
        prs.append({"number": number, "title": item.get("title", ""), "head_sha": head,
                    "base": base, "files": files})
    return prs


def _paths(files: object) -> set[str]:
    if not isinstance(files, list) or not files:
        raise ValueError("Every PR needs a nonempty, complete files list")
    paths = set()
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("filename"), str):
            raise ValueError("Invalid GitHub file record")
        name = entry["filename"]
        if not name or name.startswith("/") or "\\" in name or any(seg in ("", ".", "..") for seg in name.split("/")):
            raise ValueError("Invalid repository-relative path")
        paths.add(name)
        if entry.get("status") == "renamed":
            old = entry.get("previous_filename")
            if not isinstance(old, str) or not old:
                raise ValueError("Renamed file is missing previous_filename")
            paths.update(_paths([{"filename": old}]))
    return paths


def analyze(prs: list[dict], *, repo: str, base: str,
            source: str, candidate: list[str] | None = None) -> dict:
    if source not in ("live", "offline"):
        raise ValueError("Unknown inventory source")
    if not REPO_PATTERN.fullmatch(repo) or not base:
        raise ValueError("Invalid repo or base")
    indexed = []
    seen = set()
    for pr in prs:
        if not isinstance(pr, dict) or not isinstance(pr.get("number"), int) or pr["number"] < 1:
            raise ValueError("Invalid PR number")
        if pr["number"] in seen or pr.get("base") != base:
            raise ValueError("Duplicate or wrong-base PR in inventory")
        if not isinstance(pr.get("head_sha"), str) or not re.fullmatch(r"[a-fA-F0-9]{40}", pr["head_sha"]):
            raise ValueError("Missing exact 40-character PR head SHA")
        seen.add(pr["number"])
        indexed.append((pr["number"], _paths(pr.get("files")), pr["head_sha"], str(pr.get("title", ""))))
    indexed.sort(key=lambda x: x[0])
    pairs = []
    for i, a in enumerate(indexed):
        for b in indexed[i + 1:]:
            shared = sorted(a[1] & b[1])
            if shared:
                pairs.append({"pr_a": a[0], "pr_b": b[0], "paths": shared})
    candidate_hits = []
    if candidate is not None:
        proposed = _paths([{"filename": value} for value in candidate])
        for number, paths, _, _ in indexed:
            shared = sorted(paths & proposed)
            if shared:
                candidate_hits.append({"pr": number, "paths": shared})
    return {
        "schema_version": SCHEMA, "source": source, "repository": repo, "base": base,
        "incomplete": False, "pr_count": len(indexed),
        "prs": [{"number": n, "title": t, "head_sha": sha, "file_count": len(p)}
                for n, p, sha, t in indexed],
        "overlaps": pairs, "candidate": {"paths": sorted(proposed), "overlaps": candidate_hits}
        if candidate is not None else None,
        "limitations": ["Identical paths identify coordination risk, not a proven Git merge conflict.",
                        "Different paths may still depend on the same symbols, schemas or behavior.",
                        "Offline snapshots are historical only; live reports represent read time, not future state."],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="Jasmetk0/squash-tour-beta")
    parser.add_argument("--base", default="buuk")
    parser.add_argument("--offline", type=Path, help="JSON {prs:[...]} fixture; never claimed live")
    parser.add_argument("--candidate-paths", type=Path, help="Text file, one proposed repository path per line")
    parser.add_argument("--output", type=Path, help="Write NEW JSON file; refuse overwrite")
    args = parser.parse_args(argv)
    try:
        if args.offline:
            snapshot = json.loads(args.offline.read_text(encoding="utf-8"))
            if not isinstance(snapshot, dict) or not isinstance(snapshot.get("prs"), list):
                raise ValueError("Offline file needs a prs array")
            prs, source = snapshot["prs"], "offline"
        else:
            prs, source = collect_live(args.repo, args.base, os.environ.get("GITHUB_TOKEN")) , "live"
        proposed = None
        if args.candidate_paths:
            proposed = [p.strip() for p in args.candidate_paths.read_text(encoding="utf-8").splitlines()
                        if p.strip() and not p.lstrip().startswith("#")]
            if not proposed:
                raise ValueError("Candidate path file must contain at least one path")
        report = analyze(prs, repo=args.repo, base=args.base, source=source, candidate=proposed)
        result = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(result)
        else:
            print(result, end="")
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"PR overlap audit failed (no complete result): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
