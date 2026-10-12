/** Read-only, verified InitialWorld inspection; filters never alter the adoption payload. */
import { useEffect, useMemo, useState } from 'react'
import type { RunInitialWorldPlayer, RunWorldPreviewFieldLock } from '../api/runInitialWorldSetup'

type Group = { label: string; count: number }
type AgeGroup = Group & { min: number; max: number }
export type GeneratorReviewSummary = {
  total: number
  countries: Group[]
  potentialTiers: Group[]
  careerStages: Group[]
  ageGroups: AgeGroup[]
  averageAge: number | null
  averageCurrentAbility: number | null
  averagePotentialAbility: number | null
  ageMinimum: number | null
  ageMaximum: number | null
}

const AGE_BANDS: readonly { label: string; min: number; max: number }[] = [
  { label: '15–17', min: 15, max: 17 },
  { label: '18–22', min: 18, max: 22 },
  { label: '23–29', min: 23, max: 29 },
  { label: '30–34', min: 30, max: 34 },
  { label: '35–45', min: 35, max: 45 }
]

function grouped(players: RunInitialWorldPlayer[], key: (player: RunInitialWorldPlayer) => string): Group[] {
  const counts = new Map<string, number>()
  for (const player of players) {
    const label = key(player)
    counts.set(label, (counts.get(label) ?? 0) + 1)
  }
  return [...counts].map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
}

function average(players: RunInitialWorldPlayer[], key: (p: RunInitialWorldPlayer) => number): number | null {
  if (!players.length) return null
  return Math.round(players.reduce((sum, player) => sum + key(player), 0) / players.length * 10) / 10
}

/** Count real first-week facts from the ENTIRE preview, never filtered display rows. */
export function summariseGeneratedPlayers(players: RunInitialWorldPlayer[]): GeneratorReviewSummary {
  const ages = players.map(p => p.age_years_at_season_start)
  return {
    total: players.length,
    countries: grouped(players, p => p.country_code),
    potentialTiers: grouped(players, p => p.potential_tier || 'unknown'),
    careerStages: grouped(players, p => p.career_stage || 'unknown'),
    ageGroups: AGE_BANDS.map(b => ({
      ...b, count: ages.filter(age => age >= b.min && age <= b.max).length
    })),
    averageAge: average(players, p => p.age_years_at_season_start),
    averageCurrentAbility: average(players, p => p.current_ability),
    averagePotentialAbility: average(players, p => p.potential_ability),
    ageMinimum: ages.length ? Math.min(...ages) : null,
    ageMaximum: ages.length ? Math.max(...ages) : null
  }
}

type SortKey = 'name' | 'country' | 'age' | 'current' | 'potential'
const REVIEW_PAGE_SIZE = 50

/** Browser-only display preference. Never part of a source preview or Adopt payload. */
const COLUMN_STORAGE_KEY = 'squash-engine:generated-player-columns:v1'
const SOURCE_ATTRIBUTE_COLUMNS = [
  'technique', 'movement', 'physical', 'mental', 'consistency', 'clutch', 'recovery'
] as const
type SourceAttribute = typeof SOURCE_ATTRIBUTE_COLUMNS[number]
export type PlayerReviewColumn =
  | 'name' | 'country' | 'age' | 'current' | 'potential' | 'tier' | 'stage'
  | `attributes.${SourceAttribute}`
const OPTIONAL_COLUMNS: readonly PlayerReviewColumn[] = [
  'country', 'age', 'current', 'potential', 'tier', 'stage',
  ...SOURCE_ATTRIBUTE_COLUMNS.map(key => `attributes.${key}` as PlayerReviewColumn)
]
const DEFAULT_COLUMNS: readonly PlayerReviewColumn[] = [
  'name', 'country', 'age', 'current', 'potential', 'tier', 'stage'
]

function readColumnPreference(): PlayerReviewColumn[] {
  try {
    const saved: unknown = JSON.parse(window.localStorage.getItem(COLUMN_STORAGE_KEY) ?? 'null')
    if (!Array.isArray(saved)) return [...DEFAULT_COLUMNS]
    const values = saved.filter((id): id is PlayerReviewColumn =>
      typeof id === 'string' && OPTIONAL_COLUMNS.includes(id as PlayerReviewColumn))
    if (!values.length && saved.length > 0 && !saved.includes('name'))
      return [...DEFAULT_COLUMNS]
    return ['name', ...OPTIONAL_COLUMNS.filter(id => values.includes(id))]
  } catch {
    return [...DEFAULT_COLUMNS]
  }
}

/** Named source-model fields only: never present missing height, handedness or fake OVR. */
function availableColumns(players: RunInitialWorldPlayer[]): PlayerReviewColumn[] {
  return ['name', ...OPTIONAL_COLUMNS.filter(id =>
    id !== 'stage' && !id.startsWith('attributes.')
      ? true
      : id === 'stage'
        ? players.some(p => typeof p.career_stage === 'string' && p.career_stage.length > 0)
        : players.some(p => Number.isFinite(p.attributes?.[id.slice('attributes.'.length)]))
  )]
}

function columnLabel(id: PlayerReviewColumn, cs: boolean): string {
  const labels: Record<PlayerReviewColumn, [string, string]> = {
    name: ['Hráč', 'Player'], country: ['Země', 'Country'],
    age: ['Věk', 'Age'], current: ['Aktuální schopnost (1–99)', 'Current ability (1–99)'],
    potential: ['Potenciál (1–99)', 'Potential (1–99)'],
    tier: ['Třída potenciálu', 'Potential tier'],
    stage: ['Kariérní fáze', 'Career stage'],
    'attributes.technique': ['Technika (1–99)', 'Technique (1–99)'],
    'attributes.movement': ['Pohyb (1–99)', 'Movement (1–99)'],
    'attributes.physical': ['Fyzické (1–99)', 'Physical (1–99)'],
    'attributes.mental': ['Mentální (1–99)', 'Mental (1–99)'],
    'attributes.consistency': ['Konzistence (1–99)', 'Consistency (1–99)'],
    'attributes.clutch': ['Klíčové body (1–99)', 'Clutch (1–99)'],
    'attributes.recovery': ['Regenerace (1–99)', 'Recovery (1–99)']
  }
  return labels[id][cs ? 0 : 1]
}

function columnField(id: PlayerReviewColumn): string | null {
  if (id === 'current') return 'current_ability'
  if (id === 'potential') return 'potential_ability'
  return id.startsWith('attributes.') ? id : null
}

function columnValue(player: RunInitialWorldPlayer, id: PlayerReviewColumn): string {
  if (id === 'name') return player.name
  if (id === 'country') return player.country_code
  if (id === 'age') return String(player.age_years_at_season_start)
  if (id === 'current') return String(player.current_ability)
  if (id === 'potential') return String(player.potential_ability)
  if (id === 'tier') return player.potential_tier
  if (id === 'stage') return player.career_stage || '—'
  const value = player.attributes?.[id.slice('attributes.'.length)]
  return Number.isFinite(value) ? String(value) : '—'
}

/**
 * Product rule: sort/search/display filters are read-only inspection,
 * not group constraints and not a session Keep/Lock action.
 */
export function GeneratedPlayerReviewInspector({ players, locale = 'en', keepIds = [], onKeepChange,
  onSelectPlayer, selectedPlayerId, verifiedFieldLocks = [], pendingFieldLocks = [] }: {
  players: RunInitialWorldPlayer[]
  locale?: 'cs' | 'en'
  keepIds?: string[]
  onKeepChange?: (playerId: string, checked: boolean) => void
  onSelectPlayer?: (playerId: string) => void
  selectedPlayerId?: string | null
  /** The reviewed request's server-authenticated locks only. */
  verifiedFieldLocks?: RunWorldPreviewFieldLock[]
  /** Local unsubmitted edits: visually pending and NEVER an adopted value. */
  pendingFieldLocks?: RunWorldPreviewFieldLock[]
}): JSX.Element {
  const cs = locale === 'cs'
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState('')
  const [tier, setTier] = useState('')
  const [sort, setSort] = useState<SortKey>('name')
  const [page, setPage] = useState(0)
  const [allCountries, setAllCountries] = useState(false)
  const [columns, setColumns] = useState<PlayerReviewColumn[]>(readColumnPreference)
  const available = useMemo(() => availableColumns(players), [players])
  const visibleColumns = available.filter(id => id === 'name' || columns.includes(id))
  const verifiedByPlayer = useMemo(() => {
    const map = new Map<string, Map<string, number>>()
    for (const lock of verifiedFieldLocks) {
      const fields = map.get(lock.player_id) ?? new Map<string, number>()
      fields.set(lock.field, lock.value)
      map.set(lock.player_id, fields)
    }
    return map
  }, [verifiedFieldLocks])
  const pendingByPlayer = useMemo(() => {
    const map = new Map<string, Map<string, number>>()
    for (const lock of pendingFieldLocks) {
      const fields = map.get(lock.player_id) ?? new Map<string, number>()
      fields.set(lock.field, lock.value)
      map.set(lock.player_id, fields)
    }
    return map
  }, [pendingFieldLocks])
  useEffect(() => {
    try {
      window.localStorage.setItem(COLUMN_STORAGE_KEY, JSON.stringify(columns))
    } catch {
      // Private browsing/storage restrictions cannot block preview inspection.
    }
  }, [columns])
  const toggleColumn = (id: PlayerReviewColumn, checked: boolean) => {
    setColumns(current => ['name', ...OPTIONAL_COLUMNS.filter(value =>
      value === id ? checked : current.includes(value))])
  }
  const fieldMarker = (player: RunInitialWorldPlayer, field: string): JSX.Element | null => {
    const approved = verifiedByPlayer.get(player.player_id)?.get(field)
    const pending = pendingByPlayer.get(player.player_id)?.get(field)
    const value = field.startsWith('attributes.')
      ? player.attributes?.[field.slice('attributes.'.length)]
      : field === 'current_ability' ? player.current_ability : player.potential_ability
    const isVerified = approved != null && approved === value
    const isPending = pending != null && pending !== approved
    if (!isVerified && !isPending) return null
    return <span className="generated-review-field-mark" title={
      isPending ? 'Unsubmitted preview field edit — not applied' : 'Verified source field lock'
    } aria-label={
      (isPending ? 'Pending field edit ' : 'Verified field lock ') +
      player.player_id + ' ' + field
    }>{isPending ? ' ✎ pending' : ' ✎'}</span>
  }
  const summary = useMemo(() => summariseGeneratedPlayers(players), [players])
  const visible = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase()
    return players.filter(p =>
      (!needle || p.name.toLocaleLowerCase().includes(needle) ||
        p.player_id.toLocaleLowerCase().includes(needle)) &&
      (!country || p.country_code === country) &&
      (!tier || p.potential_tier === tier)
    ).slice().sort((a, b) => {
      if (sort === 'age') return a.age_years_at_season_start - b.age_years_at_season_start || a.player_id.localeCompare(b.player_id)
      if (sort === 'current') return b.current_ability - a.current_ability || a.player_id.localeCompare(b.player_id)
      if (sort === 'potential') return b.potential_ability - a.potential_ability || a.player_id.localeCompare(b.player_id)
      if (sort === 'country') return a.country_code.localeCompare(b.country_code) || a.player_id.localeCompare(b.player_id)
      return a.name.localeCompare(b.name) || a.player_id.localeCompare(b.player_id)
    })
  }, [players, search, country, tier, sort])
  // Paginate only the visible table. Statistics, Keep, and adoption remain
  // bound to the entire verified preview (never the current page).
  const pageCount = Math.max(1, Math.ceil(visible.length / REVIEW_PAGE_SIZE))
  const activePage = Math.min(page, pageCount - 1)
  const displayed = visible.slice(activePage * REVIEW_PAGE_SIZE, (activePage + 1) * REVIEW_PAGE_SIZE)
  const number = (value: number | null) => value == null ? '—' : String(value)
  const renderGroup = (group: Group, max: number): JSX.Element => (
    <div className="generated-review-bar" key={group.label}>
      <span title={group.label}>{group.label}</span>
      <div className="generated-review-bar__track" aria-hidden="true">
        <div style={{ width: String(100 * group.count / Math.max(1, max)) + '%' }} />
      </div>
      <strong>{group.count}</strong>
    </div>
  )
  return <section className="generated-review-inspector" aria-label="Generated player summary">
    <h5>{cs ? 'Přehled celé dávky' : 'Entire batch overview'}</h5>
    <div className="generated-review-metrics" aria-label="Full batch metrics">
      <div><span>{cs ? 'Hráčů' : 'Players'}</span><strong>{summary.total}</strong></div>
      <div><span>{cs ? 'Zemí' : 'Countries'}</span><strong>{summary.countries.length}</strong></div>
      <div><span>{cs ? 'Průměrný věk' : 'Average age'}</span><strong>{number(summary.averageAge)}</strong></div>
      <div><span>{cs ? 'Rozmezí věku' : 'Age range'}</span><strong>{number(summary.ageMinimum)}–{number(summary.ageMaximum)}</strong></div>
      <div><span>{cs ? 'Průměrná aktuální (1–99)' : 'Mean current (1–99)'}</span><strong>{number(summary.averageCurrentAbility)}</strong></div>
      <div><span>{cs ? 'Průměrný potenciál (1–99)' : 'Mean potential (1–99)'}</span><strong>{number(summary.averagePotentialAbility)}</strong></div>
    </div>
    <p className="status">{cs
      ? 'Souhrny jsou spočtené z celé ověřené dávky, nikoliv z filtrů tabulky. Hodnoty 1–99 jsou zdrojové schopnosti, ne canonical OVR 0–200 ani historický ranking.'
      : 'Statistics always use the entire verified preview, never the filtered table. Source abilities 1–99 are not canonical 0–200 OVR or an Official Ranking.'}</p>
    <div className="generated-review-breakdown">
      <section aria-label="Country breakdown">
        <h6>{cs ? 'Zastoupení zemí' : 'Country distribution'}</h6>
        {(allCountries ? summary.countries : summary.countries.slice(0, 6))
          .map(group => renderGroup(group, summary.countries[0]?.count ?? 1))}
        {summary.countries.length > 6 && <button type="button" onClick={() => setAllCountries(!allCountries)}>
          {allCountries ? (cs ? 'Zobrazit méně' : 'Show fewer') :
            (cs ? 'Všechny země' : 'All countries') + ' (' + summary.countries.length + ')'}
        </button>}
      </section>
      <section aria-label="Age breakdown">
        <h6>{cs ? 'Věkové skupiny – první týden' : 'Opening-week age bands'}</h6>
        {summary.ageGroups.map(group => renderGroup(group, Math.max(...summary.ageGroups.map(x => x.count), 1)))}
      </section>
      <section aria-label="Potential tier breakdown">
        <h6>{cs ? 'Třídy potenciálu – zdrojový model' : 'Potential tiers – source model'}</h6>
        {summary.potentialTiers.map(group => renderGroup(group, summary.potentialTiers[0]?.count ?? 1))}
        {summary.careerStages.length > 0 && <p className="status">
          {cs ? 'Kariérní fáze' : 'Career stages'}: {summary.careerStages.map(g => g.label + ' ' + g.count).join(' · ')}
        </p>}
      </section>
    </div>
    <div className="form-grid generated-review-filters" aria-label="Player review display filters">
      <label>{cs ? 'Hledání v náhledu' : 'Search preview'}
        <input aria-label="Search generated player preview" value={search}
          onChange={e => { setSearch(e.target.value); setPage(0) }}
          placeholder={cs ? 'Jméno nebo ID' : 'Name or player ID'} />
      </label>
      <label>{cs ? 'Filtrovat zemi' : 'Filter country'}
        <select aria-label="Filter generated player country" value={country}
          onChange={e => { setCountry(e.target.value); setPage(0) }}>
          <option value="">{cs ? 'Všechny země' : 'All countries'}</option>
          {summary.countries.map(g => <option key={g.label} value={g.label}>
            {g.label} ({g.count})
          </option>)}
        </select>
      </label>
      <label>{cs ? 'Filtrovat potenciál' : 'Filter potential tier'}
        <select aria-label="Filter generated player potential" value={tier}
          onChange={e => { setTier(e.target.value); setPage(0) }}>
          <option value="">{cs ? 'Všechny třídy' : 'All tiers'}</option>
          {summary.potentialTiers.map(g => <option key={g.label} value={g.label}>
            {g.label} ({g.count})
          </option>)}
        </select>
      </label>
      <label>{cs ? 'Seřadit' : 'Sort'}
        <select aria-label="Sort generated player preview" value={sort}
          onChange={e => { setSort(e.target.value as SortKey); setPage(0) }}>
          <option value="name">{cs ? 'Jméno' : 'Name'}</option>
          <option value="country">{cs ? 'Země' : 'Country'}</option>
          <option value="age">{cs ? 'Věk vzestupně' : 'Age ascending'}</option>
          <option value="current">{cs ? 'Aktuální schopnost sestupně' : 'Current ability descending'}</option>
          <option value="potential">{cs ? 'Potenciál sestupně' : 'Potential descending'}</option>
        </select>
      </label>
    </div>
    {onKeepChange && <p className="status">
      {cs ? 'Keep pro tuto relaci' : 'Session-only Keep'}: {keepIds.length} / {summary.total}.
      {' '}{cs ? 'Výběr sám nic nemění; při regeneraci zachová vybrané hráče přesně podle produkčního náhledu. Keep není trvalý Lock.' :
        'Selecting Keep changes no players until regeneration. Selected players are preserved from the verified preview, not permanently locked.'}
    </p>}
    <details className="generated-review-columns" aria-label="Generated preview columns">
      <summary>{cs ? 'Nastavit sloupce' : 'Choose table columns'} · {visibleColumns.length}</summary>
      <p className="status">{cs
        ? 'Hráč/ID zůstává viditelný. Výběr je pouze prohlížečová preference, nikdy nemění generovanou dávku ani Keep.'
        : 'Player/ID stays visible. This browser-only preference never changes the generated cohort or Keep.'}</p>
      <div className="form-grid" aria-label="Available generated player columns">
        {available.filter(id => id !== 'name').map(id =>
          <label key={id}><input type="checkbox" aria-label={'Show column ' + id}
            checked={columns.includes(id)}
            onChange={event => toggleColumn(id, event.target.checked)} />
            {' '}{columnLabel(id, cs)}
          </label>)}
      </div>
      <button type="button" onClick={() => setColumns([...DEFAULT_COLUMNS])}>
        {cs ? 'Výchozí sloupce' : 'Reset default columns'}
      </button>
    </details>
    <p role="status">{cs ? 'Zobrazeno' : 'Showing'} {visible.length} / {summary.total}.
      {' '}{cs ? 'Filtry mění pouze zobrazení. Potvrzení vždy použije celou dávku.' :
        'Display filters never change the reviewed cohort. Confirm always adopts the whole batch.'}</p>
    <div className="table-responsive" role="region" aria-label="Complete generated player preview">
      <table>
        <thead><tr>{onKeepChange && <th scope="col">{cs ? 'Ponechat' : 'Keep'}</th>}
          {visibleColumns.map(id => <th key={id} scope="col">{columnLabel(id, cs)}</th>)}
        </tr></thead>
        <tbody>{displayed.map(player => <tr key={player.player_id}>
          {onKeepChange && <td><input type="checkbox"
            aria-label={'Keep ' + player.player_id} checked={keepIds.includes(player.player_id)}
            onChange={e => onKeepChange(player.player_id, e.target.checked)} /></td>}
          {visibleColumns.map(id => <td key={id}>
            {id === 'name' ? <>
              {onSelectPlayer
                ? <button type="button" aria-label={'Edit generated player ' + player.player_id}
                    aria-pressed={selectedPlayerId === player.player_id}
                    onClick={() => onSelectPlayer(player.player_id)}>{player.name}</button>
                : player.name}<small> · {player.player_id}</small>
              {(verifiedByPlayer.get(player.player_id)?.size ||
                pendingByPlayer.get(player.player_id)?.size) ? <details
                  aria-label={'Field edit details ' + player.player_id}>
                  <summary>✎ {cs ? 'Pole' : 'Fields'}</summary>
                  {[...new Set([
                    ...verifiedByPlayer.get(player.player_id)?.keys() ?? [],
                    ...pendingByPlayer.get(player.player_id)?.keys() ?? []
                  ])].sort().map(field => <div key={field}>
                    <code>{field}</code>: {verifiedByPlayer.get(player.player_id)?.has(field)
                      ? `verified ${verifiedByPlayer.get(player.player_id)?.get(field)}`
                      : 'not verified'}
                    {pendingByPlayer.get(player.player_id)?.has(field) &&
                      ` · pending ${pendingByPlayer.get(player.player_id)?.get(field)}`}
                  </div>)}
                </details> : null}
            </> : <>
              {columnValue(player, id)}
              {columnField(id) && fieldMarker(player, columnField(id)!)}
            </>}
          </td>)}
        </tr>)}</tbody>
      </table>
    </div>
    <nav className="actions" aria-label="Generated preview pagination">
      <button type="button" disabled={activePage === 0}
        onClick={() => setPage(value => Math.max(0, value - 1))}>
        {cs ? '← Předchozí stránka' : '← Previous preview page'}
      </button>
      <span>{cs ? 'Strana' : 'Page'} {activePage + 1} / {pageCount} ·
        {' '}{cs ? 'Na stránce' : 'On page'} {displayed.length} ·
        {' '}{cs ? 'Po filtrování' : 'Matching'} {visible.length} / {summary.total}</span>
      <button type="button" disabled={activePage + 1 >= pageCount}
        onClick={() => setPage(value => Math.min(pageCount - 1, value + 1))}>
        {cs ? 'Další stránka →' : 'Next preview page →'}
      </button>
    </nav>
    {visible.length === 0 && <p>{cs ? 'Žádný hráč neodpovídá filtrům. Celá dávka je stále připravena k posouzení.' :
      'No preview player matches the display filters; the reviewed cohort has not been changed.'}</p>}
    {(search || country || tier || sort !== 'name') && <button type="button" onClick={() => {
      setSearch(''); setCountry(''); setTier(''); setSort('name'); setPage(0)
    }}>{cs ? 'Vymazat filtry zobrazení' : 'Clear display filters'}</button>}
  </section>
}
