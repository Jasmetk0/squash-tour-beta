"""Career identity from the already authenticated Saved lifecycle and prospect source.

A born prospect does not need a first match to have an identity. Future source
records are excluded by actual lifecycle membership and the recorded 15th birthday.
No mutable Run-wide catalog or sibling Branch is read.
"""
from types import SimpleNamespace


def career_world(world, state, lifecycle, prospects):
    initial = {p.player_id for p in world.players}
    identities, born = {}, {}
    if lifecycle is not None:
        if (lifecycle.run_id, lifecycle.branch_id) != (world.run_id, world.branch_id):
            raise ValueError('Career lifecycle belongs to another Saved Branch')
        allowed = {p.player_id: p for p in lifecycle.players if p.player_id not in initial}
        if prospects is not None:
            if prospects.run_id != world.run_id:
                raise ValueError('Career prospect source belongs to another Run')
            for row in prospects.for_week(state.week.ordinal).records:
                pid = row.get('prospect_id')
                if pid not in allowed:
                    continue
                player = allowed[pid]
                if (row.get('birth_year'), row.get('birth_year_week')) != (player.birth_year, player.birth_year_week):
                    raise ValueError('Career birth identity differs from the Saved lifecycle')
                position = state.week.calendar.calendar_to_season(player.birth_year + 15, player.birth_year_week)
                if position is None:
                    raise ValueError('Career birth lies outside the Saved Run clock')
                ordinal = state.week.calendar.ordinal(position.season_index, position.season_week)
                if ordinal > state.week.ordinal:
                    raise ValueError('Saved lifecycle contains a future career identity')
                name, country = row.get('display_name'), row.get('country_code')
                if not isinstance(name, str) or not name.strip() or not isinstance(country, str) or len(country) != 3:
                    raise ValueError('Saved career identity is unavailable')
                identities[pid] = SimpleNamespace(player_id=pid, name=name.strip(), country_code=country)
                born[pid] = ordinal
    return SimpleNamespace(run_id=world.run_id, branch_id=world.branch_id, players=world.players,
                           initial_turn_pro=getattr(world, 'initial_turn_pro', None), fingerprint=world.fingerprint,
                           career_identities=identities, career_birth_ordinals=born)


def saved_career_world(world, state, payload):
    from beta_engine.infrastructure.db.player_lifecycle_state import decode_prevalidated_lifecycle
    from beta_engine.infrastructure.db.run_prospect_source_state import load_saved_run_prospect_source
    history = decode_prevalidated_lifecycle(payload, run_id=world.run_id, branch_id=world.branch_id)
    lifecycle = next((s for s in reversed(history or ()) if s.week.ordinal <= state.week.ordinal), None)
    return career_world(world, state, lifecycle, load_saved_run_prospect_source(payload, run_id=world.run_id))
