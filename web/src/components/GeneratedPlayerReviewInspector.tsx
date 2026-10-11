/** Read-only, verified InitialWorld inspection; filters never alter the adoption payload. */
import { useMemo, useState } from 'react'
import type { RunInitialWorldPlayer } from '../api/runInitialWorldSetup'

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

/**
 * Product rule: sort/search/display filters are read-only inspection,
 * not group constraints and not a session Keep/Lock action.
 */
export function GeneratedPlayerReviewInspector({ players, locale = 'en', keepIds = [], onKeepChange }: {
  players: RunInitialWorldPlayer[]
  locale?: 'cs' | 'en'
  keepIds?: string[]
  onKeepChange?: (playerId: string, checked: boolean) => void
}): JSX.Element {
  const cs = locale === 'cs'
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState('')
  const [tier, setTier] = useState('')
  const [sort, setSort] = useState<SortKey>('name')
  const [page, setPage] = useState(0)
  const [allCountries, setAllCountries] = useState(false)
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
    <p role="status">{cs ? 'Zobrazeno' : 'Showing'} {visible.length} / {summary.total}.
      {' '}{cs ? 'Filtry mění pouze zobrazení. Potvrzení vždy použije celou dávku.' :
        'Display filters never change the reviewed cohort. Confirm always adopts the whole batch.'}</p>
    <div className="table-responsive" role="region" aria-label="Complete generated player preview">
      <table>
        <thead><tr>{onKeepChange && <th>{cs ? 'Ponechat' : 'Keep'}</th>}<th>{cs ? 'Hráč' : 'Player'}</th><th>{cs ? 'Země' : 'Country'}</th>
          <th>{cs ? 'Věk' : 'Age'}</th><th>{cs ? 'Aktuální / potenciál (1–99)' : 'Current / potential (1–99)'}</th>
          <th>{cs ? 'Třída' : 'Tier'}</th></tr></thead>
        <tbody>{displayed.map(player => <tr key={player.player_id}>
          {onKeepChange && <td><input type="checkbox"
            aria-label={'Keep ' + player.player_id} checked={keepIds.includes(player.player_id)}
            onChange={e => onKeepChange(player.player_id, e.target.checked)} /></td>}
          <td>{player.name}<small> · {player.player_id}</small></td>
          <td>{player.country_code}</td><td>{player.age_years_at_season_start}</td>
          <td>{player.current_ability} / {player.potential_ability}</td>
          <td>{player.potential_tier}</td>
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
