import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'

import {
  createCustomInitialPoolPlayer,
  generateInitialPlayerPool,
  getInitialPlayerPool,
  getInitialPoolAuditEvents,
  lockInitialPoolPlayer,
  regenerateInitialPlayerPool,
  unlockInitialPoolPlayer,
  updateInitialPoolPlayer
} from '../api/client'
import type { CustomInitialPoolPlayerCreatePayload, InitialPoolAttributes, InitialPoolHiddenTraits, InitialPoolPlayer, InitialPoolPlayerUpdatePayload } from '../api/types'
import { PageIntro, SectionCard, SummaryPills, MetadataList } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

const defaultAttributes: InitialPoolAttributes = { technique: 70, movement: 70, physical: 70, mental: 70, consistency: 70, clutch: 70, recovery: 70 }
const defaultTraits: InitialPoolHiddenTraits = { potential_ceiling: 82, growth_curve: 'steady', professionalism: 0.7, ambition: 0.7, travel_tolerance: 0.6, schedule_aggression: 0.5, injury_proneness: 0.25, resilience: 0.7 }
const tiers = ['S', 'A', 'B', 'C', 'D'] as const
const stages = ['junior', 'developing', 'breakthrough', 'prime', 'veteran', 'late_career']

export function AdminPlayersPage(): JSX.Element {
  const queryClient = useQueryClient()
  const [season, setSeason] = useState('2000/2001')
  const [seed, setSeed] = useState(12345)
  const [targetPoolSize, setTargetPoolSize] = useState(128)
  const [countryCode, setCountryCode] = useState('')
  const [region, setRegion] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [custom, setCustom] = useState<CustomInitialPoolPlayerCreatePayload>({
    name: '', player_id: '', country_code: 'AAA', nationality: 'AAA', birth_year: 1976, birth_year_week: 1,
    current_ability: 70, potential_ability: 82, potential_tier: 'B', career_stage: 'prime', play_style: 'balanced', archetype: 'all_court', attributes: defaultAttributes, hidden_career_traits: defaultTraits, reason: ''
  })
  const [edit, setEdit] = useState<InitialPoolPlayerUpdatePayload>({})

  const poolQuery = useQuery({ queryKey: ['initial-player-pool', season], queryFn: () => getInitialPlayerPool(season), retry: false })
  const auditQuery = useQuery({ queryKey: ['initial-player-pool-audit', season], queryFn: () => getInitialPoolAuditEvents({ season }), retry: false })

  const invalidatePool = () => {
    queryClient.invalidateQueries({ queryKey: ['initial-player-pool', season] })
    queryClient.invalidateQueries({ queryKey: ['initial-player-pool-audit', season] })
  }
  const previewMutation = useMutation({ mutationFn: () => generateInitialPlayerPool({ season, seed, target_pool_size: targetPoolSize, dry_run: true }) })
  const persistMutation = useMutation({ mutationFn: () => generateInitialPlayerPool({ season, seed, target_pool_size: targetPoolSize, dry_run: false }), onSuccess: invalidatePool })
  const regenerateMutation = useMutation({ mutationFn: () => regenerateInitialPlayerPool({ season, seed, target_pool_size: targetPoolSize, country_code: countryCode.trim() || undefined, region: region.trim() || undefined, dry_run: false }), onSuccess: invalidatePool })
  const lockMutation = useMutation({ mutationFn: ({ playerId, locked }: { playerId: string; locked: boolean }) => locked ? lockInitialPoolPlayer(playerId) : unlockInitialPoolPlayer(playerId), onSuccess: invalidatePool })
  const createMutation = useMutation({
    mutationFn: () => createCustomInitialPoolPlayer(buildCustomPayload(custom, season)),
    onSuccess: (player) => { setSelectedId(player.player_id); invalidatePool() }
  })
  const updateMutation = useMutation({ mutationFn: ({ playerId, payload }: { playerId: string; payload: InitialPoolPlayerUpdatePayload }) => updateInitialPoolPlayer(playerId, payload), onSuccess: invalidatePool })

  const activePool = previewMutation.data ?? persistMutation.data ?? regenerateMutation.data ?? poolQuery.data
  const players = activePool?.players ?? []
  const selected = useMemo(() => players.find((player) => player.player_id === selectedId) ?? players[0] ?? null, [players, selectedId])

  useEffect(() => {
    if (selected) {
      setEdit({ name: selected.name, current_ability: selected.current_ability, potential_ability: selected.potential_ability, potential_tier: selected.potential_tier, career_stage: selected.career_stage, archetype: selected.archetype, play_style: selected.play_style, attributes: selected.attributes, hidden_career_traits: selected.hidden_career_traits, reason: '' })
    }
  }, [selected])

  return (
    <section className="panel">
      <PageIntro title="Players / Initial Pool" subtitle="Admin / Engine foundation for deterministic initial player-pool preview, custom player creation, safe editing, locking, and regeneration." />
      <p className="status">This is Admin/Engine data. Viewer player profiles remain read-only later.</p>
      <p className="status">Locked and manual players are regeneration-safe. Generation is deterministic for the same config + seed.</p>

      <SectionCard title="Generation controls">
        <div className="grid">
          <label>Season<input value={season} onChange={(event) => setSeason(event.target.value)} /></label>
          <label>Seed<input type="number" value={seed} onChange={(event) => setSeed(Number(event.target.value))} /></label>
          <label>Target pool size<input type="number" min={1} max={2000} value={targetPoolSize} onChange={(event) => setTargetPoolSize(Number(event.target.value))} /></label>
          <label>Country filter<input value={countryCode} onChange={(event) => setCountryCode(event.target.value.toUpperCase())} placeholder="EGY" /></label>
          <label>Region filter<input value={region} onChange={(event) => setRegion(event.target.value)} placeholder="EUROPE" /></label>
        </div>
        <div className="button-row"><button type="button" onClick={() => previewMutation.mutate()} disabled={previewMutation.isPending}>Generate preview</button><button type="button" onClick={() => persistMutation.mutate()} disabled={persistMutation.isPending}>Persist generated pool</button><button type="button" onClick={() => regenerateMutation.mutate()} disabled={regenerateMutation.isPending}>Regenerate unlocked</button></div>
        {poolQuery.isLoading ? <p className="status">Loading current initial pool…</p> : null}
        {[poolQuery, previewMutation, persistMutation, regenerateMutation, createMutation, updateMutation].map((item, index) => item.error ? <p key={index} className="error">Action failed: {formatApiError(item.error)}</p> : null)}
        {createMutation.isSuccess ? <p className="status">Custom player created as Manual / locked.</p> : null}
        {updateMutation.isSuccess ? <p className="status">Player edits saved as a Manual override.</p> : null}
        {activePool ? <p className="status">Fingerprint: {activePool.metadata.generation_fingerprint}</p> : null}
      </SectionCard>

      <SectionCard title="Custom player form">
        <p className="status">Create story players and historical anchors explicitly. Custom players default to Manual / locked and survive automatic regeneration.</p>
        <PlayerEditFields value={custom} onChange={setCustom} includeIdentity />
        <button type="button" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>Create custom player</button>
      </SectionCard>

      {activePool ? <SectionCard title="Initial pool summary"><SummaryPills items={[{ label: 'Total players', value: activePool.summary.total_players }, { label: 'Locked', value: activePool.summary.locked_players }, { label: 'Unlocked', value: activePool.summary.unlocked_players }, { label: 'Countries', value: activePool.summary.countries_represented }, { label: 'Avg current', value: activePool.summary.average_current_ability }, { label: 'Avg potential', value: activePool.summary.average_potential_ability }, { label: 'S-tier', value: activePool.summary.by_potential_tier.S ?? 0 }, { label: 'A-tier', value: activePool.summary.by_potential_tier.A ?? 0 }, { label: 'B-tier', value: activePool.summary.by_potential_tier.B ?? 0 }]} /><MetadataList items={[{ label: 'Career stages', value: formatDistribution(activePool.summary.by_career_stage) }, { label: 'Countries', value: formatDistribution(activePool.summary.by_country) }, { label: 'Changed count', value: activePool.metadata.changed_count }, { label: 'Preserved locked', value: activePool.metadata.preserved_locked_count }]} /></SectionCard> : null}

      <SectionCard title="Generated players table">
        {players.length === 0 ? <p className="status">No initial pool persisted yet. Generate a preview, persist a generated pool, or create a custom player.</p> : null}
        {players.length > 0 ? <table aria-label="Initial player pool table"><thead><tr><th>Lock</th><th>player_id</th><th>Name</th><th>Country</th><th>Age</th><th>Birth</th><th>Stage</th><th>Tier</th><th>Current</th><th>Potential</th><th>Archetype</th><th>Play style</th><th>Tech</th><th>Move</th><th>Phys</th><th>Mental</th><th>Cons</th><th>Clutch</th><th>Recovery</th><th>Source</th><th>Manual</th><th>Actions</th></tr></thead><tbody>{players.map((player) => <tr key={player.player_id}><td>{player.locked ? '🔒' : '🔓'}</td><td><button type="button" onClick={() => setSelectedId(player.player_id)}>{player.player_id}</button></td><td>{player.name}</td><td>{player.country_code}</td><td>{player.current_age_years}</td><td>{player.birth_year} / W{player.birth_year_week}</td><td>{player.career_stage}</td><td>{player.potential_tier}</td><td>{player.current_ability}</td><td>{player.potential_ability}</td><td>{player.archetype}</td><td>{player.play_style}</td><td>{player.attributes.technique}</td><td>{player.attributes.movement}</td><td>{player.attributes.physical}</td><td>{player.attributes.mental}</td><td>{player.attributes.consistency}</td><td>{player.attributes.clutch}</td><td>{player.attributes.recovery}</td><td>{player.generation_source}</td><td>{player.manual_override ? 'Manual override' : 'Generated / unlocked'}</td><td><button type="button" onClick={() => lockMutation.mutate({ playerId: player.player_id, locked: !player.locked })}>{player.locked ? 'Unlock' : 'Lock'}</button></td></tr>)}</tbody></table> : null}
      </SectionCard>

      <SectionCard title="Player detail and safe edit">
        {selected ? <><PlayerDetail player={selected} /><p className="status">Saving edits marks the player as manual_override and preserves them from automatic regeneration.</p><PlayerEditFields value={edit} onChange={setEdit} /><button type="button" onClick={() => updateMutation.mutate({ playerId: selected.player_id, payload: edit })} disabled={updateMutation.isPending}>Save player edits</button></> : <p className="status">Select a generated player to inspect details.</p>}
      </SectionCard>

      <SectionCard title="Initial pool audit">
        {auditQuery.data?.audit_events.length ? <ul>{auditQuery.data.audit_events.map((event) => <li key={event.audit_id}><strong>{event.action}</strong> {event.player_id ?? 'pool'} by {event.actor}; reason: {event.reason ?? 'none'}; changed: {event.changed_fields.join(', ') || 'none'}; before/after: {event.before_fingerprint ?? 'none'} → {event.after_fingerprint ?? 'none'}</li>)}</ul> : <p className="status">No audit events recorded for this season yet.</p>}
      </SectionCard>
    </section>
  )
}

function buildCustomPayload(custom: CustomInitialPoolPlayerCreatePayload, season: string): CustomInitialPoolPlayerCreatePayload {
  return {
    ...custom,
    player_id: custom.player_id?.trim() ?? '',
    nationality: custom.nationality?.trim() || null,
    created_for_season: season
  }
}

function PlayerEditFields({ value, onChange, includeIdentity = false }: { value: CustomInitialPoolPlayerCreatePayload | InitialPoolPlayerUpdatePayload; onChange: (value: any) => void; includeIdentity?: boolean }): JSX.Element {
  const attrs = value.attributes ?? defaultAttributes
  const traits = value.hidden_career_traits ?? defaultTraits
  const set = (patch: Record<string, unknown>) => onChange({ ...value, ...patch })
  const setAttr = (key: keyof InitialPoolAttributes, next: number) => set({ attributes: { ...attrs, [key]: next } })
  const setTrait = (key: keyof InitialPoolHiddenTraits, next: number | string) => set({ hidden_career_traits: { ...traits, [key]: next } })
  return <div className="grid">{includeIdentity ? <><label>Custom player ID optional<input value={(value as CustomInitialPoolPlayerCreatePayload).player_id ?? ''} onChange={(e) => set({ player_id: e.target.value })} /></label><label>Country code<input value={(value as CustomInitialPoolPlayerCreatePayload).country_code ?? ''} onChange={(e) => set({ country_code: e.target.value.toUpperCase(), nationality: e.target.value.toUpperCase() })} /></label><label>Birth year<input type="number" value={(value as CustomInitialPoolPlayerCreatePayload).birth_year ?? 1976} onChange={(e) => set({ birth_year: Number(e.target.value) })} /></label><label>Birth week<input type="number" min={1} max={52} value={(value as CustomInitialPoolPlayerCreatePayload).birth_year_week ?? 1} onChange={(e) => set({ birth_year_week: Number(e.target.value) })} /></label></> : null}<label>Name<input value={value.name ?? ''} onChange={(e) => set({ name: e.target.value })} /></label><label>Current ability<input type="number" min={1} max={99} value={value.current_ability ?? 70} onChange={(e) => set({ current_ability: Number(e.target.value) })} /></label><label>Potential ability<input type="number" min={1} max={99} value={value.potential_ability ?? 82} onChange={(e) => set({ potential_ability: Number(e.target.value), hidden_career_traits: { ...traits, potential_ceiling: Number(e.target.value) } })} /></label><label>Potential tier<select value={value.potential_tier ?? 'B'} onChange={(e) => set({ potential_tier: e.target.value })}>{tiers.map((tier) => <option key={tier}>{tier}</option>)}</select></label><label>Career stage<select value={value.career_stage ?? 'prime'} onChange={(e) => set({ career_stage: e.target.value })}>{stages.map((stage) => <option key={stage}>{stage}</option>)}</select></label><label>Archetype<input value={value.archetype ?? 'all_court'} onChange={(e) => set({ archetype: e.target.value })} /></label><label>Play style<input value={value.play_style ?? 'balanced'} onChange={(e) => set({ play_style: e.target.value })} /></label>{Object.entries(attrs).map(([key, attrValue]) => <label key={key}>{key}<input type="number" min={1} max={99} value={attrValue} onChange={(e) => setAttr(key as keyof InitialPoolAttributes, Number(e.target.value))} /></label>)}<label>growth_curve<input value={traits.growth_curve} onChange={(e) => setTrait('growth_curve', e.target.value)} /></label>{(['professionalism', 'ambition', 'travel_tolerance', 'schedule_aggression', 'injury_proneness', 'resilience'] as const).map((key) => <label key={key}>{key}<input type="number" min={0} max={1} step={0.01} value={traits[key]} onChange={(e) => setTrait(key, Number(e.target.value))} /></label>)}<label>Reason<input value={value.reason ?? ''} onChange={(e) => set({ reason: e.target.value })} /></label></div>
}

function PlayerDetail({ player }: { player: InitialPoolPlayer }): JSX.Element {
  return <div><h4>{player.name} ({player.player_id})</h4><MetadataList items={[{ label: 'Identity', value: `${player.country_code}, age ${player.current_age_years}, born ${player.birth_year} W${player.birth_year_week}` }, { label: 'Ability', value: `${player.current_ability} current / ${player.potential_ability} potential (${player.potential_tier})` }, { label: 'Attributes', value: Object.entries(player.attributes).map(([key, value]) => `${key}: ${value}`).join(', ') }, { label: 'Hidden traits', value: Object.entries(player.hidden_career_traits).map(([key, value]) => `${key}: ${value}`).join(', ') }, { label: 'Generation metadata', value: `${player.generation_source}, seed ${player.generation_seed}, fingerprint ${player.generation_fingerprint}` }, { label: 'Edit status', value: player.manual_override ? 'Manual override / regeneration-safe' : 'Generated; editing auto-locks and marks manual_override' }]} /></div>
}

function formatDistribution(values: Record<string, number>): string {
  const entries = Object.entries(values)
  return entries.length ? entries.map(([key, value]) => `${key}: ${value}`).join(', ') : 'none'
}
