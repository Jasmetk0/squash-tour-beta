"""Native non-played group evidence, separate from MatchEngine results/effects."""
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.walkover_authority import TournamentWalkoverResult


class NativeGroupWithdrawal(FrozenInput):
    schema_version: Literal['native_group_withdrawal.v1'] = 'native_group_withdrawal.v1'
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    edition_id: str = Field(min_length=1)
    group_index: int = Field(ge=1)
    player_id: str = Field(min_length=1)
    week: RunWeekPosition
    slot_number: int = Field(ge=1)
    source_saved_head: str = Field(min_length=1)
    source_checkpoint_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    command_id: str = Field(min_length=1)
    operator_label: str = Field(min_length=1)
    audit_reason: str = Field(min_length=1)
    reason_category: Literal['injury', 'illness', 'personal', 'travel', 'no_show', 'ineligible', 'other']
    note: str = Field(default='', max_length=1000)

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))


class NativeGroupWalkover(FrozenInput):
    schema_version: Literal['native_group_walkover.v1'] = 'native_group_walkover.v1'
    run_id: str
    branch_id: str
    edition_id: str
    week: RunWeekPosition
    slot_number: int = Field(ge=1)
    source_checkpoint_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    withdrawal_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    result: TournamentWalkoverResult

    @model_validator(mode='after')
    def different_players(self):
        if self.result.winner_player_id == self.result.loser_player_id:
            raise ValueError('Group walkover cannot award a player against himself')
        return self

    @property
    def match_id(self):
        return self.result.match_id

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode='json'))


def group_withdrawals(slots):
    records = {}
    for slot in slots:
        for record in getattr(slot, 'group_withdrawals', ()):
            key = (record.branch_id, record.command_id)
            if key in records and records[key] != record:
                raise ValueError('Conflicting native group withdrawal evidence')
            records[key] = record
    return tuple(records.values())


def group_resolved_matches(slots):
    result = {}
    for slot in slots:
        for match in (*getattr(slot, 'accepted', ()), *getattr(slot, 'walkovers', ())):
            if match.match_id in result and result[match.match_id] != match:
                raise ValueError('Conflicting played/walkover group evidence')
            result[match.match_id] = match
    return result


def pending_group_walkovers(checkpoint, slot):
    """Resolve only remaining frozen group pairings from actual withdrawal history."""
    history = getattr(checkpoint, 'history_global_slots', getattr(checkpoint, 'events', ()))
    withdrawals = group_withdrawals(history)
    result = {}
    for item in slot.remaining:
        authority = next(a for a in slot.authorities if a.edition.edition_id == item.edition_id)
        if not getattr(authority.edition, 'group_configuration', None):
            continue
        schedule = authority.draw.schedule
        if item.index >= len(schedule.matches):
            continue
        ids = tuple(p.player_id for p in item.projections)
        records = [r for r in withdrawals if r.edition_id == item.edition_id and r.player_id in ids]
        if not records:
            continue
        if len(records) != 1:
            raise ValueError('Two withdrawn opponents require an explicit decided outcome policy')
        record = records[0]
        result[item.match_id] = NativeGroupWalkover(
            run_id=slot.run_id, branch_id=slot.branch_id, edition_id=item.edition_id,
            week=slot.week, slot_number=slot.number,
            source_checkpoint_fingerprint=slot.snapshot_fingerprint,
            withdrawal_fingerprint=record.fingerprint,
            result=TournamentWalkoverResult(match_id=item.match_id,
                loser_player_id=record.player_id,
                winner_player_id=next(pid for pid in ids if pid != record.player_id)),
        )
    return result
