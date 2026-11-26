"""Pin input bytes and fail closed on missing or ambiguous identity."""
import hashlib

import pytest

from scripts.audit_atp_2019_external_tournaments import read_pinned, compare_2019
from scripts.audit_atp_2019_research import ROOT, load


def test_exact_bytes_or_reject(tmp_path):
    path = tmp_path / "sample.csv"
    data = b"one,two\r\n"
    path.write_bytes(data)
    source = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    assert read_pinned(path, source) == data
    path.write_bytes(data.replace(b"\r\n", b"\n"))
    with pytest.raises(ValueError, match="pinned source"):
        read_pinned(path, source)


def test_duplicate_external_id_fails_before_counts():
    root = ROOT / "research_2019"
    m = load(root / "external_tournament_input.json")
    row = [""] * 31
    row[0], row[4], row[8] = "2019-407", "407", "2019"
    data = (",".join(row) + "\n") * 2
    with pytest.raises(ValueError, match="Duplicate ATP event ID"):
        compare_2019(data.encode(), m, load(root / "inventory.json"))


def test_manifest_does_not_claim_all_identities():
    m = load(ROOT / "research_2019/external_tournament_input.json")
    obs = m["observed_2019"]
    assert obs["all"] == 68 and obs["in_scope"] == 63
    assert len(obs["matched_reviewed"]) + obs["remaining_identity_review"] == 63
    assert len(m["source"]["sha256"]) == 64
    assert all(x["sha256"] is None for x in m["missing_local_inputs"])
