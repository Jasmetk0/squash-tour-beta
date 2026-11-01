"""Unit contracts for the offline analyzer and the live-read safety boundary."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / "scripts" / "audit_pr_overlap.py"
spec = importlib.util.spec_from_file_location("audit_pr_overlap", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def pr(number, paths, *, base="buuk"):
    return {"number": number, "base": base, "title": f"Test {number}",
            "head_sha": f"{number:040x}", "files": [{"filename": p} for p in paths]}


def test_exact_paths_only_and_stable_order():
    items = [pr(13, ["z.py", "src/a.py"]), pr(2, ["src/a.py", "x.py"]),
             pr(9, ["src/b.py", "z.py"])]
    report = module.analyze(items, repo="Owner/repo", base="buuk", source="offline")
    assert report["pr_count"] == 3
    assert [(r["pr_a"], r["pr_b"], r["paths"]) for r in report["overlaps"]] == [
        (2, 13, ["src/a.py"]), (9, 13, ["z.py"])]
    assert report["source"] == "offline" and report["candidate"] is None


def test_renames_count_both_paths_and_candidate():
    a = pr(1, ["new.py"])
    a["files"] = [{"filename": "new.py", "status": "renamed", "previous_filename": "old.py"}]
    report = module.analyze([a, pr(2, ["old.py"])], repo="O/R", base="buuk",
                            source="offline", candidate=["new.py"])
    assert report["overlaps"] == [{"pr_a": 1, "pr_b": 2, "paths": ["old.py"]}]
    assert report["candidate"]["overlaps"] == [{"pr": 1, "paths": ["new.py"]}]


@pytest.mark.parametrize("change", [
    lambda x: x.append(x[0]),
    lambda x: x[0].update(base="main"),
    lambda x: x[0].update(head_sha="wrong"),
    lambda x: x[0].update(files=[]),
    lambda x: x[0].update(files=[{"filename": "../secret"}]),
    lambda x: x[0].update(files=[{"filename": "/tmp/file"}]),
    lambda x: x[0].update(files=[{"filename": "foo\\bar"}]),
    lambda x: x[0].update(files=[{"filename": "a", "status": "renamed"}]),
])
def test_incomplete_or_unsafe_inventory_fails_closed(change):
    items = [pr(1, ["a"])]
    change(items)
    with pytest.raises(ValueError):
        module.analyze(items, repo="O/R", base="buuk", source="offline")


def test_live_head_changes_are_rejected(monkeypatch):
    payload = {"number": 15, "title": "new", "base": {"ref": "buuk"},
               "head": {"sha": "a" * 40}}
    monkeypatch.setattr(module, "_pages", lambda repo, suffix, token: [payload]
                        if suffix.startswith("pulls?") else [{"filename": "a.py"}])
    monkeypatch.setattr(module, "_get", lambda url, token: {"head": {"sha": "b" * 40}})
    with pytest.raises(ValueError, match="changed during"):
        module.collect_live("O/R", "buuk", None)


def test_offline_cli_new_file_and_refuses_overwrite(tmp_path):
    source = tmp_path / "snapshot.json"
    source.write_text(json.dumps({"prs": [pr(2, ["a.py"])]}), encoding="utf-8")
    candidate = tmp_path / "paths.txt"
    candidate.write_text("# comment\na.py\n", encoding="utf-8")
    output = tmp_path / "result.json"
    args = ["--repo", "O/R", "--offline", str(source), "--candidate-paths", str(candidate),
            "--output", str(output)]
    assert module.main(args) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["candidate"]["overlaps"][0]["pr"] == 2
    assert module.main(args) == 1
    assert json.loads(output.read_text(encoding="utf-8")) == result


def test_empty_inventory_valid_and_empty_candidate_invalid():
    assert module.analyze([], repo="O/R", base="buuk", source="offline")["overlaps"] == []
    with pytest.raises(ValueError):
        module.analyze([], repo="O/R", base="buuk", source="offline", candidate=[])
