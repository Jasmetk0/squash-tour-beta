"""Scoped, immutable SQLite storage of reviewed generation proposals.

The saved preview is a non-authoritative checkpoint. There is deliberately no
method here that Adopt/Save can call without the normal production recheck.
"""
from __future__ import annotations

import json
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import RunGenerationProposalModel


def _decode(row: RunGenerationProposalModel) -> dict:
    try:
        value = json.loads(row.payload_json)
        if not isinstance(value, dict) or canonical_hash(value) != row.content_fingerprint:
            raise ValueError("Saved generation proposal checksum is invalid")
        if (value.get("run_id"), value.get("branch_id"), value.get("proposal_id"),
            value.get("label"), value.get("saved_revision_id"),
            value.get("draft_version"), value.get("package_fingerprint"),
            value.get("preview_fingerprint")) != (
                row.run_id, row.branch_id, row.proposal_id, row.label,
                row.saved_revision_id, row.draft_version,
                row.package_fingerprint, row.preview_fingerprint,
            ):
            raise ValueError("Saved generation proposal row metadata disagrees with payload")
        if value.get("preview", {}).get("fingerprint") != row.preview_fingerprint:
            raise ValueError("Saved generation proposal preview fingerprint changed")
        return value
    except (TypeError, KeyError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError("Saved generation proposal contains invalid data") from exc


def save_proposal(
    sessions: sessionmaker[Session], *, data: dict, max_per_branch: int = 12,
) -> dict:
    run_id, branch_id, proposal_id = (
        data["run_id"], data["branch_id"], data["proposal_id"],
    )
    with sessions.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        key = (run_id, branch_id, proposal_id)
        existing = session.get(RunGenerationProposalModel, key)
        fingerprint = canonical_hash(data)
        if existing is not None:
            if existing.content_fingerprint != fingerprint:
                raise ValueError("Proposal ID already exists with different saved content")
            return _decode(existing)
        count = session.query(RunGenerationProposalModel).filter_by(
            run_id=run_id, branch_id=branch_id,
        ).count()
        if count >= max_per_branch:
            raise ValueError("Too many saved generation proposals for this Branch (maximum 12)")
        row = RunGenerationProposalModel(
            run_id=run_id, branch_id=branch_id, proposal_id=proposal_id,
            label=data["label"], saved_revision_id=data["saved_revision_id"],
            draft_version=data["draft_version"],
            package_fingerprint=data["package_fingerprint"],
            preview_fingerprint=data["preview_fingerprint"],
            content_fingerprint=fingerprint,
            payload_json=json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        )
        session.add(row)
    return data


def list_proposals(
    sessions: sessionmaker[Session], *, run_id: str, branch_id: str,
) -> list[dict]:
    with sessions() as session:
        rows = session.execute(
            select(RunGenerationProposalModel).where(
                RunGenerationProposalModel.run_id == run_id,
                RunGenerationProposalModel.branch_id == branch_id,
            ).order_by(RunGenerationProposalModel.label, RunGenerationProposalModel.proposal_id)
        ).scalars().all()
        # Check each saved full cohort once, not six times for six metadata
        # columns. A 1000-player snapshot can be several MB.
        summaries = []
        for row in rows:
            data = _decode(row)
            summaries.append({
                key: data[key] for key in (
                    "proposal_id", "label", "saved_revision_id",
                    "draft_version", "package_fingerprint", "preview_fingerprint",
                )
            })
        return summaries


def get_proposal(
    sessions: sessionmaker[Session], *, run_id: str, branch_id: str, proposal_id: str,
) -> dict | None:
    with sessions() as session:
        row = session.get(RunGenerationProposalModel, (run_id, branch_id, proposal_id))
        return _decode(row) if row else None


def delete_proposal(
    sessions: sessionmaker[Session], *, run_id: str, branch_id: str, proposal_id: str,
) -> bool:
    with sessions.begin() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        row = session.get(RunGenerationProposalModel, (run_id, branch_id, proposal_id))
        if row is None:
            return False
        _decode(row)  # don't silently discard corrupted material
        session.delete(row)
        return True
