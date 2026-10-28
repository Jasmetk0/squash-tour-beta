"""One persisted Branch slot, with canonical independent accepted match evidence.

The v13 sporting ledger owns results. Tournament views below are derived from
that ledger, never a second mutable result store. Old executors retain old seeds.
"""

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
from types import SimpleNamespace
from typing import Literal

from pydantic import Field, model_validator
from pydantic_core import to_json

from beta_engine.core import DeterministicRng
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches.health import (
    EffectiveMatchHealthSnapshot,
    project_player_health,
)
from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import MatchContext
from beta_engine.domain.players.calendar_canonical_match import canonical_participant
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
    continuation_anchor,
    continuation_effects,
)
from beta_engine.domain.players.calendar_followup_knockout import (
    ROUNDS,
    ROUNDS_EIGHT,
    CalendarFollowupKnockout,
)
from beta_engine.domain.players.calendar_followup_points import (
    CalendarFollowupEightPointPolicy,
    CalendarFollowupPointPolicy,
    derive_followup_awards,
)
from beta_engine.domain.players.calendar_match_state import CalendarMatchStatePolicy
from beta_engine.domain.players.calendar_native_competition import (
    CalendarNativeCompetitionCheckpoint,
    native_match_slot,
    native_projections,
    terminal_players,
)
from beta_engine.domain.players.calendar_native_sporting_checkpoint import (
    CalendarNativeSportingCheckpoint,
    CalendarNativeSportingWeek,
)
from beta_engine.domain.players.calendar_sporting_checkpoint import (
    CalendarSportingCheckpoint,
)
from beta_engine.domain.players.sporting import PlayerSportingRecord
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    CanonicalPlayerMatchProjection,
)
from beta_engine.domain.tournaments.calendar_native_tour import (
    CalendarNativeCompetitionTourState,
    CalendarNativeTourState,
)
from beta_engine.domain.tournaments.calendar_tour import (
    CalendarEditionAuthority,
    CalendarTourState,
)

from beta_engine.domain.tournaments.calendar_groups import (
    NativeGroupTieDecision, completed_group_result, group_plan, group_decisions,
    TournamentGroupStandingsUnresolvedTie,
)
from beta_engine.domain.matches.formats import EffectiveMatchFormatSnapshot, MatchFormat

_replay_projections = ContextVar("global_slot_private_replay_projections", default=None)


@contextmanager
def global_replay_projection_scope():
    """Memoize private frozen values only during one pure verification replay.

    The verifier owns freshly decoded inputs and creates new frozen models for
    every change. Nothing escapes this scope as a validation proof. Physical
    rows, source graphs and later calls still get their ordinary byte checks.
    Callers must neither expose nor mutate these private models during replay.
    """
    token = _replay_projections.set({"fingerprints": {}, "tournaments": {}}) if _replay_projections.get() is None else None
    try:
        yield
    finally:
        if token is not None:
            _replay_projections.reset(token)


def _replay_fingerprint(value, *, sporting=False):
    scope = _replay_projections.get()
    key = (id(value), sporting)
    memo = scope["fingerprints"] if scope is not None else {}
    known = memo.get(key)
    if known is not None and known[0] is value:
        return known[1]
    fingerprint = _incremental_checkpoint_fingerprint(value, scope) if scope is not None and not sporting else None
    if fingerprint is None:
        body = value.model_dump(mode="json")
        if sporting:
            body.pop("prepared_awards", None)
        fingerprint = canonical_hash(body)
    if scope is not None:
        memo[key] = (value, fingerprint)
        while len(memo) > 256:
            memo.pop(next(iter(memo)))
    return fingerprint


def _incremental_checkpoint_fingerprint(value, scope):
    """Hash the SAME canonical JSON, reusing only private immutable prefixes.

    No alternate persisted hash, declared fingerprint or physical proof is used.
    Exact event identities bind a reusable prefix; replacement/truncation drops
    its suffix. Outside the private replay scope the ordinary full hash runs.
    """
    if (type(value) is not GlobalCompetitionCheckpoint
        or set(type(value).model_fields) != {'schema_version', 'run_id', 'branch_id', 'competition_root', 'events'}
        or type(value).model_computed_fields
        or type(value).__pydantic_decorators__.model_serializers
        or type(value).__pydantic_decorators__.field_serializers
        or type(value.events) is not tuple or len(value.events) > 4096
        or any(type(x) is not str for x in (value.run_id, value.branch_id, value.schema_version))
        or any(type(event) not in (GlobalSlot, CalendarNativeSportingWeek, CalendarFollowupKnockout) for event in value.events)):
        return None
    def encode(body):
        return json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    cache = scope.setdefault('checkpoint_prefixes', {})
    key = (id(value.competition_root), value.run_id, value.branch_id, value.schema_version)
    entry = cache.get(key)
    collect = scope.get('collect_checkpoint_value_hashes', False)
    if entry is None or entry[0] is not value.competition_root or (collect and entry[4] is None):
        body = value.model_dump(mode='json', exclude={'events'})
        if set(body) != {'schema_version', 'run_id', 'branch_id', 'competition_root'}:
            return None
        before = [encode(k) + b':' + encode(body[k]) for k in sorted(body) if k < 'events']
        after = [encode(k) + b':' + encode(body[k]) for k in sorted(body) if k > 'events']
        prefix = b'{' + b','.join(before) + (b',' if before else b'') + b'"events":['
        suffix = b']' + (b',' if after else b'') + b','.join(after) + b'}'
        auxiliary = None
        auxiliary_suffix = None
        if collect:
            try:
                ordered = json.loads(encode(body))
                def core(data):
                    return to_json(data, inf_nan_mode='constants')
                before_core = [core(k) + b':' + core(ordered[k]) for k in sorted(ordered) if k < 'events']
                after_core = [core(k) + b':' + core(ordered[k]) for k in sorted(ordered) if k > 'events']
                auxiliary = [hashlib.sha256(b'{' + b','.join(before_core) + (b',' if before_core else b'') + b'"events":[')]
                auxiliary_suffix = b']' + (b',' if after_core else b'') + b','.join(after_core) + b'}'
            except (TypeError, ValueError):
                # Older compatible Pydantic installations can retain the full
                # canonical-value path without this optional comparison hash.
                scope['collect_checkpoint_value_hashes'] = False
        entry = (value.competition_root, [], [hashlib.sha256(prefix)], suffix, auxiliary, auxiliary_suffix)
        cache[key] = entry
        while len(cache) > 4:
            cache.pop(next(iter(cache)))
    _, events, hashes, suffix, auxiliary, auxiliary_suffix = entry
    shared = 0
    while shared < min(len(events), len(value.events)) and events[shared] is value.events[shared]:
        shared += 1
    del events[shared:]
    del hashes[shared + 1:]
    if auxiliary is not None:
        del auxiliary[shared + 1:]
    for event in value.events[shared:]:
        encoded = encode(event.model_dump(mode='json'))
        state = hashes[-1].copy()
        state.update((b',' if events else b'') + encoded)
        if auxiliary is not None:
            try:
                state_core = auxiliary[-1].copy()
                state_core.update((b',' if events else b'') + to_json(json.loads(encoded), inf_nan_mode='constants'))
                auxiliary.append(state_core)
            except (TypeError, ValueError):
                auxiliary = None
                scope['collect_checkpoint_value_hashes'] = False
                cache[key] = (entry[0], events, hashes, suffix, None, None)
        events.append(event)
        hashes.append(state)
    result = hashes[-1].copy()
    result.update(suffix)
    fingerprint = result.hexdigest()
    if auxiliary is not None:
        equivalent_value = auxiliary[-1].copy()
        equivalent_value.update(auxiliary_suffix)
        values = scope.setdefault('checkpoint_value_hashes', {})
        values[fingerprint] = equivalent_value.digest()
        while len(values) > 128:
            values.pop(next(iter(values)))
    return fingerprint


def _prime_private_fingerprint(value, fingerprint):
    """Reuse an actual canonical value hash only in a private frozen scope.

    Callers must have computed it from strictly decoded actual content (or its
    authenticated identical-byte DTO). This is never a physical/source proof.
    Outside the private scope ordinary properties always compute fresh hashes.
    """
    scope = _replay_projections.get()
    if scope is not None:
        memo = scope['fingerprints']
        memo[(id(value), False)] = (value, fingerprint)
        while len(memo) > 256:
            memo.pop(next(iter(memo)))


def is_slot_edition(authority):
    return authority.edition.schema_version in {"calendar_tournament_edition.v2", "calendar_tournament_edition.v3"}


def is_group_edition(authority):
    return authority.edition.schema_version == "calendar_tournament_edition.v3"


def edition_plan(authority, matches, slots=()):
    if is_group_edition(authority):
        return group_plan(authority, matches, group_decisions(slots, authority.edition.edition_id))
    ids = tuple(s.player_id for s in authority.draw.main.slots) if authority.draw else ()
    prior = tuple(matches.get(f"{authority.edition.edition_id}:{suffix}") for suffix in bracket(authority))
    return tuple((f"{authority.edition.edition_id}:{suffix}", native_match_slot(authority, i),
                  participants(ids, prior, i) if ids else (), 5)
                 for i, suffix in enumerate(bracket(authority)))


def slot_match_id(authority, index):
    if is_group_edition(authority):
        if authority.draw is None:
            return authority.edition.edition_id + ":group:pending-draw"
        schedule = authority.draw.schedule
        if index < len(schedule.matches):
            return schedule.matches[index].match_id
        offset = index - len(schedule.matches)
        count = authority.edition.group_configuration.groups.group_count * authority.edition.group_configuration.groups.advancing_per_group
        if offset < 0 or offset >= count - 1:
            raise ValueError("Group slot match index is outside its configured bracket")
        round_number = 1
        while offset >= count // (2 ** round_number):
            offset -= count // (2 ** round_number)
            round_number += 1
        suffix = f"first:M{offset + 1}" if round_number == 1 else f"R{round_number}:M{offset + 1}"
        return f"{authority.edition.edition_id}:hybrid:knockout:{suffix}"
    return f"{authority.edition.edition_id}:{bracket(authority)[index]}"



def match_seed(authority, match_id):
    return int(
        canonical_hash(
            {
                "schema_version": "global_match_seed.v1",
                "root": authority.edition.simulation_seed,
                "edition": authority.edition.edition_id,
                "week": authority.edition.week.ordinal,
                "match": match_id,
            }
        )[:15],
        16,
    )


def bracket(authority):
    return ROUNDS_EIGHT if authority.edition.main_entrant_count == 8 else ROUNDS


class FrozenSlotMatch(FrozenInput):
    edition_id: str
    index: int = Field(ge=0, le=6)
    match_id: str
    seed: int
    projections: tuple[CanonicalPlayerMatchProjection, CanonicalPlayerMatchProjection]
    health: EffectiveMatchHealthSnapshot
    source_saved_head: str
    sequence: int = Field(ge=1)


class FrozenGroupSlotMatch(FrozenSlotMatch):
    schema_version: Literal["frozen_group_slot_match.v1"] = "frozen_group_slot_match.v1"
    index: int = Field(ge=0, le=8255)
    effective_match_format: EffectiveMatchFormatSnapshot


class GlobalSlot(FrozenInput):
    schema_version: Literal["calendar_global_slot.v1", "calendar_global_slot.v2"] = "calendar_global_slot.v1"
    run_id: str
    branch_id: str
    week: RunWeekPosition
    number: int = Field(ge=1)
    source_checkpoint_fingerprint: str
    source_health_fingerprint: str
    players: tuple[PlayerSportingRecord, ...]
    authorities: tuple[CalendarEditionAuthority, ...]
    scheduled: tuple[FrozenSlotMatch | FrozenGroupSlotMatch, ...]
    accepted: tuple[CalendarContinuationMatch, ...] = ()
    group_tie_decisions: tuple[NativeGroupTieDecision, ...] = Field(default=(), exclude_if=lambda value: not value)
    # Keep the original empty-field omission in the native serializer. A wrap
    # serializer materializes every player's full attributes and rally log an
    # extra time whenever an enclosing checkpoint is serialized.
    inherited_match_ids: tuple[str, ...] = Field(
        default=(), exclude_if=lambda value: not value,
    )

    @property
    def snapshot_fingerprint(self):
        scope = _replay_projections.get()
        memo = scope["fingerprints"] if scope is not None else {}
        key = (id(self), "slot_snapshot")
        known = memo.get(key)
        if known is not None and known[0] is self:
            return known[1]
        result = canonical_hash(
            {
                "schema_version": "calendar_slot_snapshot.v1",
                "run_id": self.run_id,
                "branch_id": self.branch_id,
                "week": self.week.model_dump(mode="json"),
                "number": self.number,
                "source_checkpoint": self.source_checkpoint_fingerprint,
                "health": self.source_health_fingerprint,
                "players": [p.model_dump(mode="json") for p in self.players],
                "authorities": [a.execution_fingerprint for a in self.authorities],
            }
        )
        if scope is not None:
            memo[key] = (self, result)
            while len(memo) > 256:
                memo.pop(next(iter(memo)))
        return result

    @property
    def conflicts(self):
        seen = {}
        for item in self.scheduled:
            for player in item.projections:
                seen.setdefault(player.player_id, []).append(item.match_id)
        return {
            pid: tuple(sorted(mids))
            for pid, mids in sorted(seen.items())
            if len(mids) > 1
        }

    @property
    def remaining(self):
        done = {m.match_id for m in self.accepted} | set(self.inherited_match_ids)
        return tuple(m for m in self.scheduled if m.match_id not in done)

    @property
    def fingerprint(self):
        return _replay_fingerprint(self)

    @model_validator(mode="after")
    def canonical_evidence(self):
        if self.schema_version == "calendar_global_slot.v1" and (self.group_tie_decisions or any(isinstance(m, FrozenGroupSlotMatch) for m in self.scheduled) or any(is_group_edition(a) for a in self.authorities)):
            raise ValueError("Historical slot cannot acquire group authority")
        if any(r.edition_id not in {a.edition.edition_id for a in self.authorities} for r in self.group_tie_decisions):
            raise ValueError('Global slot tie decision has a foreign Edition source')
        if len({r.command_id for r in self.group_tie_decisions}) != len(self.group_tie_decisions):
            raise ValueError('Global slot contains duplicate tie decision commands')
        ids = tuple(m.match_id for m in self.scheduled)
        done = tuple(m.match_id for m in self.accepted)
        if set(self.inherited_match_ids) & set(done) or not set(
            self.inherited_match_ids
        ) <= set(ids):
            raise ValueError("Global slot has invalid inherited match references")
        if (
            not ids
            or ids != tuple(sorted(set(ids)))
            or done != tuple(sorted(set(done)))
            or not set(done) <= set(ids)
        ):
            raise ValueError("Global slot has noncanonical or foreign match evidence")
        snapshot = self.snapshot_fingerprint if self.accepted else None
        if any(
            (m.run_id, m.branch_id, m.week, m.source_checkpoint_fingerprint)
            != (self.run_id, self.branch_id, self.week, snapshot)
            for m in self.accepted
        ):
            raise ValueError("Accepted match differs from frozen global slot owner")
        return self


class GlobalTournamentResult(CalendarFollowupKnockout):
    schema_version: Literal["calendar_followup_knockout.v7"] = (
        "calendar_followup_knockout.v7"
    )

    @property
    def fingerprint(self):
        return _replay_fingerprint(self)

    @property
    def sporting_fingerprint(self):
        return _replay_fingerprint(self, sporting=True)

    @model_validator(mode="after")
    def validate_bracket(self):
        # Actual input/results are independently rebuilt from the slot ledger.
        # This view still enforces complete feeder topology and configured points.
        suffixes = ROUNDS_EIGHT if len(self.entrant_ids) == 8 else ROUNDS
        if (
            len(self.matches) != len(suffixes)
            or len(set(self.entrant_ids)) != len(self.entrant_ids)
            or not self.edition_authority_fingerprint
            or self.scope != "configured_tour_knockout"
        ):
            raise ValueError("Incomplete or unbound global tournament")
        for i, (m, suffix) in enumerate(zip(self.matches, suffixes, strict=True)):
            if (m.run_id, m.week.ordinal, m.match_id) != (
                self.run_id,
                self.week.ordinal,
                f"{self.tournament_id}:{suffix}",
            ) or (
                self.schema_version.endswith(".v7") and m.branch_id != self.branch_id
            ):
                raise ValueError("Global tournament contains a foreign match")
            expected = participants(self.entrant_ids, self.matches[:i], i)
            if (m.result.player_a_id, m.result.player_b_id) != expected:
                raise ValueError(
                    "Global tournament did not consume actual feeder winners"
                )
        if (
            self.prepared_policy is None
            or self.prepared_awards != derive_followup_awards(self)
        ):
            raise ValueError(
                "Global tournament points differ from complete actual results"
            )
        return self


class ForkGlobalTournamentResult(GlobalTournamentResult):
    schema_version: Literal["calendar_followup_knockout.v8"] = (
        "calendar_followup_knockout.v8"
    )


class GlobalCompetitionCheckpoint(CalendarNativeCompetitionCheckpoint):
    schema_version: Literal["calendar_sporting_checkpoint.v13"] = (
        "calendar_sporting_checkpoint.v13"
    )
    competition_root: (
        CalendarSportingCheckpoint
        | CalendarNativeSportingCheckpoint
        | CalendarNativeCompetitionCheckpoint
    )
    events: tuple[
        GlobalSlot | CalendarNativeSportingWeek | CalendarFollowupKnockout, ...
    ] = ()

    @property
    def fingerprint(self):
        return _replay_fingerprint(self)

    @property
    def source_checkpoint(self):
        return getattr(
            self.competition_root, "source_checkpoint", self.competition_root
        )

    @property
    def players(self):
        players = self.competition_root.players
        for event in self.events:
            players = (
                event.advance.target_players
                if isinstance(event, CalendarNativeSportingWeek)
                else terminal_players(
                    players,
                    event.accepted if isinstance(event, GlobalSlot) else event.matches,
                )
            )
        return players

    @property
    def tournaments(self):
        return (
            self.competition_root.tournaments
            + tuple(e for e in self.events if isinstance(e, CalendarFollowupKnockout))
            + completed_tournaments(self.events)
        )

    @property
    def played_continuations(self):
        return self.competition_root.played_continuations + tuple(
            m
            for e in self.events
            if not isinstance(e, CalendarNativeSportingWeek)
            for m in (e.accepted if isinstance(e, GlobalSlot) else e.matches)
        )

    @property
    def week_events(self):
        # The public match-count reader needs each accepted match exactly once.
        return (
            self.competition_root.week_events
            + tuple(
                m for e in self.events if isinstance(e, GlobalSlot) for m in e.accepted
            )
            + tuple(e for e in self.events if isinstance(e, CalendarFollowupKnockout))
        )


class GlobalTourState(CalendarNativeCompetitionTourState):
    schema_version: Literal["calendar_tour_authority.v5"] = "calendar_tour_authority.v5"
    competition_root_tour: (
        CalendarTourState | CalendarNativeTourState | CalendarNativeCompetitionTourState
    )

    @property
    def fingerprint(self):
        return _replay_fingerprint(self)


def upgrade(state, checkpoint, head):
    if isinstance(state, GlobalTourState):
        return state, checkpoint
    values = {k: getattr(state, k) for k in CalendarTourState.model_fields}
    tour = GlobalTourState.model_construct(
        **{
            **values,
            "schema_version": "calendar_tour_authority.v5",
            "competition_root_tour": state,
            "competition_root_saved_head": head,
        }
    )
    cp = GlobalCompetitionCheckpoint(
        run_id=checkpoint.run_id,
        branch_id=checkpoint.branch_id,
        competition_root=checkpoint,
    )
    return tour.model_copy(update={"checkpoint_fingerprint": cp.fingerprint}), cp


def participants(ids, matches, index):
    first = len(ids) // 2
    if index < first:
        return tuple(ids[index * 2 : index * 2 + 2])
    offset = (
        (index - first) * 2
        if len(ids) == 8 and index < 6
        else 4
        if len(ids) == 8
        else 0
    )
    feeders = (offset, offset + 1)
    if any(i >= len(matches) or matches[i] is None for i in feeders):
        return ()
    return tuple(matches[i].result.winner_player_id for i in feeders)


def completed_tournaments(events, *, owner=None):
    slots = tuple(e for e in events if isinstance(e, GlobalSlot))
    scope = _replay_projections.get()
    key = (tuple(id(slot) for slot in slots), owner)
    if scope is not None and key in scope["tournaments"]:
        return scope["tournaments"][key][1]
    authorities = {a.edition.edition_id: a for e in slots for a in e.authorities}
    matches = {m.match_id: m for e in slots for m in e.accepted}
    result = []
    for eid, a in sorted(authorities.items()):
        if is_group_edition(a):
            event = completed_group_result(a, slots, owner=owner)
            if event is not None:
                result.append(event)
            continue
        ordered = tuple(matches.get(f"{eid}:{suffix}") for suffix in bracket(a))
        if any(m is None for m in ordered):
            continue
        first = next(e for e in slots if any(s.edition_id == eid for s in e.scheduled))
        source = next(
            s.source_saved_head for s in first.scheduled if s.edition_id == eid
        )
        policy = (
            CalendarFollowupEightPointPolicy
            if len(ordered) == 7
            else CalendarFollowupPointPolicy
        )(
            category_label=eid,
            validity_weeks=a.edition.validity_weeks,
            **a.edition.point_table,
        )
        model = (
            ForkGlobalTournamentResult if owner is not None else GlobalTournamentResult
        )
        event = model.model_construct(
            run_id=first.run_id,
            branch_id=owner or first.branch_id,
            tournament_id=eid,
            command_id="global-tournament:" + a.execution_fingerprint,
            source_saved_head=source,
            source_checkpoint_fingerprint=first.source_checkpoint_fingerprint,
            week=first.week,
            seed=a.edition.simulation_seed,
            entrant_ids=tuple(s.player_id for s in a.draw.main.slots),
            operator_label="Global Simulation Slots",
            audit_reason="Actual matches from the shared frozen slot ledger",
            request_fingerprint=a.execution_fingerprint,
            matches=ordered,
            prepared_policy=policy,
            prepared_awards=(),
            edition_authority_fingerprint=a.execution_fingerprint,
            scope="configured_tour_knockout",
        )
        event = event.model_copy(
            update={"prepared_awards": derive_followup_awards(event)}
        )
        # These matches were already decoded/validated as part of the slot
        # ledger. Validate the derived bracket and its typed fields without a
        # JSON round trip that reparses every rally in every historical week.
        # The slot command verifier still independently replays MatchEngine.
        result.append(model.model_validate({
            key: getattr(event, key) for key in model.model_fields
        }))
    result = tuple(result)
    if scope is not None:
        # Keep slot references so Python cannot recycle their identities while
        # this private value projection is retained. Changed slots are new models.
        scope["tournaments"][key] = (slots, result)
        while len(scope["tournaments"]) > 16:
            scope["tournaments"].pop(next(iter(scope["tournaments"])))
    return result


def next_schedule(state, checkpoint):
    """Schedule only; never execute MatchEngine during inspection or preview."""
    slots = tuple(
        e
        for e in getattr(checkpoint, "global_slots", getattr(checkpoint, "events", ()))
        if isinstance(e, GlobalSlot)
    )
    opened = next((s for s in slots if s.remaining), None)
    if opened is not None:
        if opened.week.ordinal != state.week.ordinal:
            raise ValueError("Unresolved global slot belongs to an earlier week")
        return (
            opened.number,
            tuple(
                (
                    next(
                        a
                        for a in opened.authorities
                        if a.edition.edition_id == s.edition_id
                    ),
                    s.index,
                    tuple(p.player_id for p in s.projections),
                )
                for s in opened.remaining
            ),
            opened,
        )
    history = getattr(checkpoint, "history_global_slots", slots)
    accepted = {
        m.match_id: m for s in history if isinstance(s, GlobalSlot) for m in s.accepted
    }
    due = []
    for a in state.editions:
        if (
            not is_slot_edition(a)
            or a.edition.week.ordinal != state.week.ordinal
            or a.tournament_fingerprint
        ):
            continue
        if not a.draw:
            due.append((a.edition.start_slot + 3, a, 0, ()))
            continue
        try:
            plan = edition_plan(a, accepted, history)
        except TournamentGroupStandingsUnresolvedTie:
            # Reserve the dependent playoff slot: never advance past it and
            # then resume from a later sporting snapshot after Admin resolves it.
            if a.edition.group_configuration.format_kind == "groups_knockout":
                schedule = a.draw.schedule
                due.append((a.edition.start_slot + 3 + schedule.match_day_count,
                            a, len(schedule.matches), ()))
            continue
        missing = [(i, item) for i, item in enumerate(plan) if item[0] not in accepted]
        if not missing:
            continue
        number = min(item[1] for _, item in missing)
        for index, (_, n, ids, _) in missing:
            if n == number:
                due.append((number, a, index, ids))
    if not due:
        return None, (), None
    number = min(d[0] for d in due)
    return number, tuple((a, i, ids) for n, a, i, ids in due if n == number), None


def freeze_slot(state, checkpoint, *, world, lifecycle, health, source, head):
    number, due, opened = next_schedule(state, checkpoint)
    if number is None:
        raise ValueError("No unresolved global match slot in the current week")
    if opened is not None:
        return opened
    history = getattr(checkpoint, "history_global_slots", getattr(checkpoint, "events", ()))
    for authority, _, player_ids in due:
        if is_group_edition(authority) and authority.draw and not player_ids:
            matches = {m.match_id: m for s in history if isinstance(s, GlobalSlot)
                       for m in s.accepted}
            edition_plan(authority, matches, history)
    ids = [
        a.edition.edition_id
        for a in state.editions
        if a.edition.week.ordinal == state.week.ordinal
        and not a.result_confirmed
        and not is_slot_edition(a)
        and a.edition.start_slot + 3 <= number
    ]
    if ids:
        raise ValueError(
            "Earlier legacy Edition requires its preserved executor: " + ", ".join(ids)
        )
    if any(not a.draw for a, _, _ in due):
        raise ValueError(
            "Slot requires reviewed Saved draws: "
            + ", ".join(a.edition.edition_id for a, _, _ in due if not a.draw)
        )
    authorities = tuple(
        sorted(
            {a.edition.edition_id: a for a, _, _ in due}.values(),
            key=lambda a: a.edition.edition_id,
        )
    )
    initial = GlobalSlot.model_construct(
        schema_version="calendar_global_slot.v2" if any(is_group_edition(a) for a in authorities) else "calendar_global_slot.v1",
        run_id=state.run_id,
        branch_id=state.branch_id,
        week=lifecycle.week,
        number=number,
        source_checkpoint_fingerprint=checkpoint.fingerprint,
        source_health_fingerprint=health.fingerprint,
        players=checkpoint.players,
        authorities=authorities,
        scheduled=(),
        accepted=(),
    )
    baseline = SimpleNamespace(
        players=checkpoint.players, fingerprint=initial.snapshot_fingerprint
    )
    profiles = {p.player_id: p for p in health.players}
    scheduled = []
    for a, i, pids in due:
        mid = slot_match_id(a, i)
        medical = EffectiveMatchHealthSnapshot(
            player_profiles=tuple(project_player_health(profiles[pid]) for pid in pids)
        )
        scheduled.append(
            (FrozenGroupSlotMatch if is_group_edition(a) else FrozenSlotMatch)(
                **({"effective_match_format": (a.draw.schedule.matches[i].effective_match_format
                    if i < len(a.draw.schedule.matches) else EffectiveMatchFormatSnapshot.create(
                        format=MatchFormat(best_of=a.edition.group_configuration.knockout_best_of, games_to=11, win_by=2),
                        source_scope="phase_override", source_key=a.edition.fingerprint + ":knockout",
                    ))} if is_group_edition(a) else {}),
                edition_id=a.edition.edition_id,
                index=i,
                match_id=mid,
                seed=match_seed(a, mid),
                projections=native_projections(
                    baseline, world, lifecycle, source, pids
                ),
                health=medical,
                source_saved_head=a.played_saved_head or head,
                sequence=1,
            )
        )
    # Sequence is stable within the complete slot and independent of accepted order.
    scheduled = tuple(
        s.model_copy(update={"sequence": len(checkpoint.played_continuations) + i + 1})
        for i, s in enumerate(sorted(scheduled, key=lambda s: s.match_id))
    )
    return GlobalSlot.model_validate_json(
        initial.model_copy(update={"scheduled": scheduled}).model_dump_json()
    )


def calculate_match(slot, item):
    snapshot = slot.snapshot_fingerprint
    ctx = MatchContext(
        match_id=item.match_id,
        player_a=canonical_participant(item.projections[0]),
        player_b=canonical_participant(item.projections[1]),
        best_of=item.effective_match_format.format.best_of if isinstance(item, FrozenGroupSlotMatch) else 5,
        games_to=11,
        win_by=2,
    )
    nested = {
        "command_id": "global-match:"
        + canonical_hash({"slot": snapshot, "match": item.match_id}),
        "match_id": item.match_id,
        "expected_saved_head": item.source_saved_head,
        "expected_checkpoint_fingerprint": snapshot,
        "player_a_id": item.projections[0].player_id,
        "player_b_id": item.projections[1].player_id,
        "seed": item.seed,
        "operator_label": "Global Simulation Slots",
        "audit_reason": "Actual match from the shared frozen slot snapshot",
    }
    inputs = {
        "schema_version": "calendar_continuation_match.v3" if isinstance(item, FrozenGroupSlotMatch) else "calendar_continuation_match.v2",
        "run_id": slot.run_id,
        "branch_id": slot.branch_id,
        "week": slot.week,
        "sequence": item.sequence,
        "command_id": nested["command_id"],
        "match_id": item.match_id,
        "source_saved_head": item.source_saved_head,
        "source_checkpoint_fingerprint": snapshot,
        "seed": item.seed,
        "operator_label": nested["operator_label"],
        "audit_reason": nested["audit_reason"],
        "request_fingerprint": canonical_hash(
            {"run_id": slot.run_id, "branch_id": slot.branch_id, "command": nested}
        ),
        "input_context": ctx,
        "canonical_projections": item.projections,
        "projection_policy": CanonicalMatchInputProjectionPolicy(),
        "state_policy": CalendarMatchStatePolicy(),
        "source_health_fingerprint": slot.source_health_fingerprint,
        "effective_health": item.health,
    }
    anchor = continuation_anchor(SimpleNamespace(**inputs))
    result = MatchEngine(DeterministicRng(item.seed)).simulate(
        ctx, log_anchor_hash=anchor, effective_match_health=item.health
    )
    _, effects = continuation_effects(
        SimpleNamespace(players=slot.players), ctx, result, inputs["state_policy"]
    )
    return CalendarContinuationMatch(
        **inputs, result=result, effects=effects, log_anchor_hash=anchor
    )


def accept_slot(checkpoint, slot, *, match_id=None):
    selected = tuple(
        s for s in slot.remaining if match_id is None or s.match_id == match_id
    )
    if not selected:
        raise ValueError("Selected match is not unresolved in the nearest global slot")
    selected_ids = {m.match_id for m in selected}
    for item in selected:
        if any(p.numeric_calibration_required for p in item.health.player_profiles):
            raise ValueError(
                f"Global slot {slot.number}, {item.match_id}: unresolved numeric Health effects"
            )
    for pid, ids in slot.conflicts.items():
        if selected_ids.intersection(ids):
            raise ValueError(
                f"Global slot {slot.number}: player {pid} collides in {', '.join(ids)}"
            )
    accepted = tuple(
        sorted(
            (*slot.accepted, *(calculate_match(slot, s) for s in selected)),
            key=lambda m: m.match_id,
        )
    )
    successor = slot.model_copy(update={"accepted": accepted})
    if getattr(checkpoint, "schema_version", None) == "native_fork_competition.v1":
        return checkpoint.with_global_slot(successor), successor
    events = checkpoint.events
    if (
        events
        and isinstance(events[-1], GlobalSlot)
        and events[-1].week == slot.week
        and events[-1].number == slot.number
    ):
        events = events[:-1]
    return checkpoint.model_copy(update={"events": (*events, successor)}), successor


def inherit_open_slot(slot, *, branch_id):
    """New fork snapshot references accepted source matches without re-owning them."""
    value = slot.model_copy(
        update={
            "branch_id": branch_id,
            "accepted": (),
            "inherited_match_ids": tuple(
                sorted(
                    set(slot.inherited_match_ids) | {m.match_id for m in slot.accepted}
                )
            ),
        }
    )
    value = value.model_copy(
        update={
            "scheduled": tuple(
                s.model_copy(
                    update={
                        "projections": tuple(
                            p.model_copy(
                                update={
                                    "source_sporting_fingerprint": value.snapshot_fingerprint
                                }
                            )
                            for p in s.projections
                        )
                    }
                )
                for s in value.scheduled
            )
        }
    )
    return GlobalSlot.model_validate_json(value.model_dump_json())
