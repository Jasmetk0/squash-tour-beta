import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'

import {
  generateInitialPlayerPool,
  getInitialPlayerPool,
  lockInitialPoolPlayer,
  regenerateInitialPlayerPool,
  unlockInitialPoolPlayer
} from '../api/client'
import type { InitialPoolPlayer } from '../api/types'
import { PageIntro, SectionCard, SummaryPills, MetadataList } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function AdminPlayersPage(): JSX.Element {
  const queryClient = useQueryClient()
  const [season, setSeason] = useState('2000/2001')
  const [seed, setSeed] = useState(12345)
  const [targetPoolSize, setTargetPoolSize] = useState(128)
  const [countryCode, setCountryCode] = useState('')
  const [region, setRegion] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const poolQuery = useQuery({
    queryKey: ['initial-player-pool', season],
    queryFn: () => getInitialPlayerPool(season),
    retry: false
  })

  const previewMutation = useMutation({
    mutationFn: () => generateInitialPlayerPool({ season, seed, target_pool_size: targetPoolSize, dry_run: true })
  })
  const persistMutation = useMutation({
    mutationFn: () => generateInitialPlayerPool({ season, seed, target_pool_size: targetPoolSize, dry_run: false }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['initial-player-pool', season] })
  })
  const regenerateMutation = useMutation({
    mutationFn: () =>
      regenerateInitialPlayerPool({
        season,
        seed,
        target_pool_size: targetPoolSize,
        country_code: countryCode.trim() || undefined,
        region: region.trim() || undefined,
        dry_run: false
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['initial-player-pool', season] })
  })
  const lockMutation = useMutation({
    mutationFn: ({ playerId, locked }: { playerId: string; locked: boolean }) =>
      locked ? lockInitialPoolPlayer(playerId) : unlockInitialPoolPlayer(playerId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['initial-player-pool', season] })
  })

  const activePool = previewMutation.data ?? persistMutation.data ?? regenerateMutation.data ?? poolQuery.data
  const players = activePool?.players ?? []
  const selected = useMemo(() => players.find((player) => player.player_id === selectedId) ?? players[0] ?? null, [players, selectedId])

  return (
    <section className="panel">
      <PageIntro
        title="Players / Initial Pool"
        subtitle="Admin / Engine foundation for deterministic initial 2000/2001 player-pool preview, locking, and regeneration."
      />
      <p className="status">This is Admin/Engine data. Viewer player profiles will be read-only later.</p>
      <p className="status">Locked players are preserved by regeneration. Generation is deterministic for the same config + seed.</p>

      <SectionCard title="Generation controls">
        <div className="grid">
          <label>
            Season
            <input value={season} onChange={(event) => setSeason(event.target.value)} />
          </label>
          <label>
            Seed
            <input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
          </label>
          <label>
            Target pool size
            <input type="number" min={1} max={2000} value={targetPoolSize} onChange={(event) => setTargetPoolSize(Number(event.target.value))} />
          </label>
          <label>
            Country filter
            <input value={countryCode} onChange={(event) => setCountryCode(event.target.value.toUpperCase())} placeholder="EGY" />
          </label>
          <label>
            Region filter
            <input value={region} onChange={(event) => setRegion(event.target.value)} placeholder="EUROPE" />
          </label>
        </div>
        <div className="button-row">
          <button type="button" onClick={() => previewMutation.mutate()} disabled={previewMutation.isPending}>Generate preview</button>
          <button type="button" onClick={() => persistMutation.mutate()} disabled={persistMutation.isPending}>Persist generated pool</button>
          <button type="button" onClick={() => regenerateMutation.mutate()} disabled={regenerateMutation.isPending}>Regenerate unlocked</button>
        </div>
        {poolQuery.isLoading ? <p className="status">Loading current initial pool…</p> : null}
        {poolQuery.error ? <p className="error">Failed to load current pool: {formatApiError(poolQuery.error)}</p> : null}
        {previewMutation.error ? <p className="error">Preview failed: {formatApiError(previewMutation.error)}</p> : null}
        {persistMutation.error ? <p className="error">Persist failed: {formatApiError(persistMutation.error)}</p> : null}
        {regenerateMutation.error ? <p className="error">Regeneration failed: {formatApiError(regenerateMutation.error)}</p> : null}
        {activePool ? <p className="status">Fingerprint: {activePool.metadata.generation_fingerprint}</p> : null}
      </SectionCard>

      {activePool ? (
        <SectionCard title="Initial pool summary">
          <SummaryPills
            items={[
              { label: 'Total players', value: activePool.summary.total_players },
              { label: 'Locked', value: activePool.summary.locked_players },
              { label: 'Unlocked', value: activePool.summary.unlocked_players },
              { label: 'Countries', value: activePool.summary.countries_represented },
              { label: 'Avg current', value: activePool.summary.average_current_ability },
              { label: 'Avg potential', value: activePool.summary.average_potential_ability },
              { label: 'S-tier', value: activePool.summary.by_potential_tier.S ?? 0 },
              { label: 'A-tier', value: activePool.summary.by_potential_tier.A ?? 0 },
              { label: 'B-tier', value: activePool.summary.by_potential_tier.B ?? 0 }
            ]}
          />
          <MetadataList
            items={[
              { label: 'Career stages', value: formatDistribution(activePool.summary.by_career_stage) },
              { label: 'Countries', value: formatDistribution(activePool.summary.by_country) },
              { label: 'Changed count', value: activePool.metadata.changed_count },
              { label: 'Preserved locked', value: activePool.metadata.preserved_locked_count }
            ]}
          />
        </SectionCard>
      ) : null}

      <SectionCard title="Generated players table">
        {players.length === 0 ? <p className="status">No initial pool persisted yet. Generate a preview or persist a generated pool.</p> : null}
        {players.length > 0 ? (
          <table aria-label="Initial player pool table">
            <thead>
              <tr>
                <th>Lock</th><th>player_id</th><th>Name</th><th>Country</th><th>Age</th><th>Birth</th><th>Stage</th><th>Tier</th><th>Current</th><th>Potential</th><th>Archetype</th><th>Play style</th><th>Tech</th><th>Move</th><th>Phys</th><th>Mental</th><th>Cons</th><th>Clutch</th><th>Recovery</th><th>Source</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {players.map((player) => (
                <tr key={player.player_id}>
                  <td>{player.locked ? '🔒' : '🔓'}</td>
                  <td><button type="button" onClick={() => setSelectedId(player.player_id)}>{player.player_id}</button></td>
                  <td>{player.name}</td><td>{player.country_code}</td><td>{player.current_age_years}</td><td>{player.birth_year} / W{player.birth_year_week}</td><td>{player.career_stage}</td><td>{player.potential_tier}</td><td>{player.current_ability}</td><td>{player.potential_ability}</td><td>{player.archetype}</td><td>{player.play_style}</td><td>{player.attributes.technique}</td><td>{player.attributes.movement}</td><td>{player.attributes.physical}</td><td>{player.attributes.mental}</td><td>{player.attributes.consistency}</td><td>{player.attributes.clutch}</td><td>{player.attributes.recovery}</td><td>{player.generation_source}</td>
                  <td><button type="button" onClick={() => lockMutation.mutate({ playerId: player.player_id, locked: !player.locked })}>{player.locked ? 'Unlock' : 'Lock'}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </SectionCard>

      <SectionCard title="Player detail">
        {selected ? <PlayerDetail player={selected} /> : <p className="status">Select a generated player to inspect details.</p>}
      </SectionCard>
    </section>
  )
}

function PlayerDetail({ player }: { player: InitialPoolPlayer }): JSX.Element {
  return (
    <div>
      <h4>{player.name} ({player.player_id})</h4>
      <MetadataList
        items={[
          { label: 'Identity', value: `${player.country_code}, age ${player.current_age_years}, born ${player.birth_year} W${player.birth_year_week}` },
          { label: 'Ability', value: `${player.current_ability} current / ${player.potential_ability} potential (${player.potential_tier})` },
          { label: 'Attributes', value: Object.entries(player.attributes).map(([key, value]) => `${key}: ${value}`).join(', ') },
          { label: 'Hidden traits', value: Object.entries(player.hidden_career_traits).map(([key, value]) => `${key}: ${value}`).join(', ') },
          { label: 'Generation metadata', value: `${player.generation_source}, seed ${player.generation_seed}, fingerprint ${player.generation_fingerprint}` },
          { label: 'Edit status', value: 'Full editing is intentionally deferred; lock/unlock is implemented for this foundation slice.' }
        ]}
      />
    </div>
  )
}

function formatDistribution(values: Record<string, number>): string {
  const entries = Object.entries(values)
  return entries.length ? entries.map(([key, value]) => `${key}: ${value}`).join(', ') : 'none'
}
