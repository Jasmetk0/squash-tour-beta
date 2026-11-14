import { useQuery } from '@tanstack/react-query'

import { getSeasonArchive, getSeasonDetail } from '../api/client'
import { validSeasonArchive, validSeasonDetail } from '../api/seasonArchive'
import type { PresenceRow } from '../api/seasonArchive'
import { formatApiError } from '../utils/apiErrors'
import { readerPage, readerPageCount, readerSlice, useReaderParams } from './readerUrlState'

type Props = {
  runId: string; branchId: string; savedHead: string; cs: boolean
  playerName?: (id: string) => string
}

const FIELD: Record<string, [string, string]> = {
  ranking_policy_id: ['ID ranking politiky', 'ranking policy id'],
  ranking_best_n: ['Best N', 'Best N'],
  development_policy_fingerprint: ['politika vývoje hráčů', 'player development policy'],
  weeks_per_season: ['týdnů v sezóně', 'weeks per season'],
  edition_point_tables_fingerprint: ['bodové tabulky Edic', 'Edition point tables'],
  edition_formats_fingerprint: ['formáty Edic', 'Edition formats']
}

export function SeasonArchivePanel({ runId, branchId, savedHead, cs, playerName }: Props): JSX.Element {
  const url = useReaderParams('season', JSON.stringify([runId, branchId, savedHead]))
  const parseSeason = (value: string) => /^(0|[1-9]\d*)$/.test(value) && Number.isSafeInteger(Number(value)) ? Number(value) : null
  const selectedRaw = url.get('selected')
  const otherRaw = url.get('other')
  const selected = parseSeason(selectedRaw)
  const other = parseSeason(otherRaw)
  const archiveSearch = url.get('search').toLocaleLowerCase()
  const archiveOrder = url.get('order', 'asc')
  const title = cs ? 'Archiv sezón a porovnání' : 'Season archive and comparison'
  const archiveQuery = useQuery({
    queryKey: ['season-archive', runId, branchId, savedHead],
    queryFn: () => getSeasonArchive(runId, branchId), retry: false
  })
  const seasons = archiveQuery.data?.seasons ?? []
  const hasSelected = selected !== null && seasons.some(s => s.season_index === selected)
  const hasOther = other !== null && seasons.some(s => s.season_index === other)
  const validPair = hasSelected && hasOther && selected !== other
  const detailQuery = useQuery({
    queryKey: ['season-detail', runId, branchId, savedHead, selected, other],
    queryFn: () => getSeasonDetail(runId, branchId, selected!, other!),
    enabled: validPair && Boolean(archiveQuery.data && validSeasonArchive(archiveQuery.data, { runId, branchId, savedHead })), retry: false
  })
  if (archiveQuery.isPending) {
    return <section aria-label={title}><h3>{title}</h3><p role="status">{cs ? 'Načítám archiv…' : 'Loading archive…'}</p></section>
  }
  if (archiveQuery.error) {
    return <section aria-label={title}><h3>{title}</h3><p role="status">
      {cs ? 'Archiv sezón není pro tuto revizi dostupný: ' : 'The season archive is unavailable for this revision: '}
      {formatApiError(archiveQuery.error)}</p></section>
  }
  const archive = archiveQuery.data
  if (!validSeasonArchive(archive, { runId, branchId, savedHead })) {
    return <section aria-label={title}><h3>{title}</h3><p role="alert">{cs
      ? 'Odpověď neodpovídá vybrané Branch nebo uložené revizi a nebyla zobrazena.'
      : 'The response does not match the selected Branch or Saved revision and was not displayed.'}</p></section>
  }
  const name = (id: string) => playerName?.(id) ?? id
  const archiveRows = archive.seasons.map((value, index) => ({ value, index }))
    .filter(({ value }) => [value.season_label, String(value.season_index), value.leading_player?.name ?? '',
      value.leading_player?.player_id ?? '', value.leading_country?.country_code ?? '']
      .join(' ').toLocaleLowerCase().includes(archiveSearch))
    .sort((a, b) => (archiveOrder === 'desc' ? -1 : 1) *
      (a.value.season_index - b.value.season_index) || a.index - b.index)
  const label = (index: number) => archive.seasons.find(s => s.season_index === index)?.season_label ?? `S${index + 1}`
  const detail = detailQuery.data
  const checked = detail && selected !== null && other !== null &&
    validSeasonDetail(detail, { runId, branchId, savedHead, season: selected, compareTo: other }) ? detail : null
  const absent = cs ? 'nezastoupeno' : 'not represented'
  const cell = (m: PresenceRow['selected'], f: 'titles' | 'finals' | 'awarded_points') => m === null ? absent : m[f]
  const rows = (items: PresenceRow[], key: 'country_code' | 'player_id') => items.map(r => {
    const id = String(r[key])
    return <tr key={id}>
      <td>{key === 'player_id' ? name(id) : id}</td>
      <td>{cell(r.selected, 'titles')}</td><td>{cell(r.comparison, 'titles')}</td>
      <td>{r.delta === null ? (cs ? 'bez rozdílu (chybí jedna strana)' : 'no delta (one side missing)') : r.delta.titles}</td>
      <td>{cell(r.selected, 'awarded_points')}</td><td>{cell(r.comparison, 'awarded_points')}</td>
      <td>{r.delta === null ? '—' : r.delta.awarded_points}</td>
    </tr>
  })
  const comparisonTable = (items: PresenceRow[], key: 'country_code' | 'player_id') => {
    const prefix = key === 'country_code' ? 'countries' : 'players'
    const search = url.get(prefix + '_search').toLocaleLowerCase()
    const presence = url.get(prefix + '_presence', 'all')
    const sort = url.get(prefix + '_sort', 'name')
    const page = readerPage(url.get(prefix + '_page', '1'))
    const filtered = items.map((value, index) => ({ value, index })).filter(({ value }) =>
      (presence === 'all' || value.presence === presence) &&
      [String(value[key] ?? ''), key === 'player_id' ? name(String(value.player_id)) : '']
        .join(' ').toLocaleLowerCase().includes(search))
      .sort((a, b) => {
        const compare = sort === 'titles' || sort === 'points'
          ? (() => {
              const field = sort === 'titles' ? 'titles' : 'awarded_points'
              const av = a.value.selected?.[field]
              const bv = b.value.selected?.[field]
              return av === undefined ? (bv === undefined ? 0 : 1) : bv === undefined ? -1 : bv - av
            })()
          : String(a.value[key]).localeCompare(String(b.value[key]))
        return compare || a.index - b.index
      })
    const pages = readerPageCount(filtered.length)
    const current = Math.min(page, pages)
    const set = (field: string, value: string, replace = false) =>
      url.set({ [prefix + '_' + field]: value, [prefix + '_page']: null }, replace)
    return <>
      <label>{cs ? 'Hledat' : 'Search'}{' '}
        <input value={url.get(prefix + '_search')} onChange={e => set('search', e.target.value, true)} /></label>{' '}
      <label>{cs ? 'Zastoupení' : 'Presence'}{' '}
        <select value={['all', 'both', 'only_selected', 'only_comparison'].includes(presence) ? presence : 'all'}
          onChange={e => set('presence', e.target.value)}>
          <option value="all">{cs ? 'Vše' : 'All'}</option>
          <option value="both">{cs ? 'Obě sezony' : 'Both seasons'}</option>
          <option value="only_selected">{cs ? 'Jen vybraná' : 'Selected only'}</option>
          <option value="only_comparison">{cs ? 'Jen srovnávaná' : 'Comparison only'}</option>
        </select></label>{' '}
      <label>{cs ? 'Řazení' : 'Sort'}{' '}
        <select value={['name', 'titles', 'points'].includes(sort) ? sort : 'name'} onChange={e => set('sort', e.target.value)}>
          <option value="name">{cs ? 'Podle jména/ID' : 'Name/ID'}</option>
          <option value="titles">{cs ? 'Tituly ve vybrané' : 'Selected titles'}</option>
          <option value="points">{cs ? 'Body ve vybrané' : 'Selected points'}</option>
        </select></label>
      <p>{cs ? 'Zobrazeno' : 'Matching'}: {filtered.length} / {items.length}</p>
      {filtered.length === 0 ? <p>{cs ? 'Žádné odpovídající záznamy.' : 'No matching records.'}</p>
        : <div className="table-responsive"><table>{head(key === 'country_code' ? (cs ? 'Země' : 'Country') : (cs ? 'Hráč' : 'Player'))}
          <tbody>{rows(readerSlice(filtered, current).map(e => e.value), key)}</tbody></table></div>}
      <nav aria-label={cs ? 'Stránkování porovnání' : 'Comparison pagination'}>
        <button type="button" disabled={current <= 1} onClick={() => url.set({ [prefix + '_page']: String(current - 1) })}>{cs ? 'Předchozí' : 'Previous'}</button>
        {' '}{cs ? 'Strana' : 'Page'} {current} / {pages}{' '}
        <button type="button" disabled={current >= pages} onClick={() => url.set({ [prefix + '_page']: String(current + 1) })}>{cs ? 'Další' : 'Next'}</button>
      </nav>
    </>
  }
  const head = (first: string) => <thead><tr>
    <th>{first}</th>
    <th>{cs ? 'Tituly (vybraná)' : 'Titles (selected)'}</th><th>{cs ? 'Tituly (srovnávaná)' : 'Titles (comparison)'}</th>
    <th>{cs ? 'Rozdíl titulů' : 'Titles delta'}</th>
    <th>{cs ? 'Body (vybraná)' : 'Points (selected)'}</th><th>{cs ? 'Body (srovnávaná)' : 'Points (comparison)'}</th>
    <th>{cs ? 'Rozdíl bodů' : 'Points delta'}</th></tr></thead>
  return <section aria-label={title}>
    <h3>{title}</h3>
    <p>{cs
      ? 'Pouze čtení z uložené revize vybrané Branch. Neexistuje žádné složené skóre země; zobrazují se výslovné ukazatele. Přehled sám nic nezastavuje ani nevytváří.'
      : 'Read-only from the selected Branch Saved revision. There is no composite country score; explicit metrics are shown. The view neither pauses the simulation nor creates anything.'}</p>
    <label>{cs ? 'Hledat v archivu' : 'Search archive'}{' '}
      <input value={url.get('search')} onChange={e => url.set({ search: e.target.value }, true)} /></label>{' '}
    <label>{cs ? 'Seřadit' : 'Sort'}{' '}
      <select value={archiveOrder === 'desc' ? 'desc' : 'asc'} onChange={e => url.set({ order: e.target.value })}>
        <option value="asc">{cs ? 'Od nejstarší' : 'Oldest first'}</option>
        <option value="desc">{cs ? 'Od nejnovější' : 'Newest first'}</option>
      </select></label>{' '}
    <button type="button" onClick={() => url.reset()}>{cs ? 'Reset filtrů' : 'Reset filters'}</button>
    {archive.seasons.length === 0
      ? <p>{cs ? 'Zatím není dokončena žádná sezóna.' : 'No season is completed yet.'}</p>
      : archiveRows.length === 0 ? <p>{cs ? 'Žádná sezona neodpovídá hledání.' : 'No seasons match the search.'}</p>
      : <div className="table-responsive"><table aria-label={cs ? 'Archiv dokončených sezón' : 'Completed season archive'}>
        <thead><tr><th>{cs ? 'Sezóna' : 'Season'}</th><th>{cs ? 'Edice' : 'Editions'}</th>
          <th>{cs ? 'Vedoucí hráč' : 'Leading player'}</th><th>{cs ? 'Vedoucí země (tituly, body)' : 'Leading country (titles, points)'}</th>
          <th>{cs ? 'Profesionálem / konec' : 'Turned pro / retired'}</th><th>Best N</th><th /></tr></thead>
        <tbody>{archiveRows.map(({ value: s }) => <tr key={s.season_index}>
          <td>{s.season_label}</td>
          <td>{s.overview.no_completed_editions ? (cs ? 'žádná dokončená' : 'none completed') : s.overview.completed_edition_count}</td>
          <td>{s.leading_player ? `${name(s.leading_player.player_id)} (${s.leading_player.titles})` : '—'}</td>
          <td>{s.leading_country ? `${s.leading_country.country_code} (${s.leading_country.titles}, ${s.leading_country.awarded_points})` : '—'}</td>
          <td>{s.overview.turned_pro.length} / {s.overview.retired.length}</td>
          <td>{s.rules.ranking_best_n}</td>
          <td><button type="button" aria-pressed={selected === s.season_index} onClick={() => url.set({ selected: String(s.season_index) })}>
            {cs ? 'Vybrat' : 'Select'} {s.season_label}</button></td>
        </tr>)}</tbody></table></div>}
    {archive.seasons.length > 1 && <>
      <label>{cs ? 'Vybraná sezóna' : 'Selected season'}{' '}
        <select value={selected ?? ''} onChange={e => url.set({ selected: e.target.value || null })}>
          <option value="">—</option>{archive.seasons.map(s => <option key={s.season_index} value={s.season_index}>{s.season_label}</option>)}
        </select></label>{' '}
      <label>{cs ? 'Porovnat s' : 'Compare with'}{' '}
        <select value={other ?? ''} onChange={e => url.set({ other: e.target.value || null })}>
          <option value="">—</option>{archive.seasons.map(s =>
            <option key={s.season_index} value={s.season_index}>{s.season_label}</option>)}
        </select></label>
    </>}
    {(selectedRaw !== '' || otherRaw !== '') && !validPair && <p role="alert">{cs
      ? 'Vyberte dvě různé existující sezony. Neplatné či shodné volby nelze porovnat.'
      : 'Select two distinct existing seasons. Invalid or identical selections cannot be compared.'}</p>}
    {detailQuery.isPending && validPair && <p role="status">{cs ? 'Načítám porovnání…' : 'Loading comparison…'}</p>}
    {detailQuery.error && <p role="status">{formatApiError(detailQuery.error)}</p>}
    {detail && !checked && <p role="alert">{cs
      ? 'Porovnání neodpovídá vybrané revizi nebo sezónám a nebylo zobrazeno.'
      : 'The comparison does not match the selected revision or seasons and was not displayed.'}</p>}
    {checked && selected !== null && other !== null && <div aria-label={cs ? 'Porovnání sezón' : 'Season comparison'}>
      <h4>{label(selected)} {cs ? 'oproti' : 'vs'} {label(other)}</h4>
      {checked.detail.comparability.comparable
        ? <p role="status">{cs ? 'Porovnávaná zaznamenaná pravidla jsou v obou sezónách stejná.' : 'The compared recorded rules (ranking, player development and Edition settings) are the same in both seasons.'}</p>
        : <div role="alert"><p><strong>{cs ? 'Omezená srovnatelnost: pravidla se mezi sezónami liší.' : 'Limited comparability: the rules differ between the seasons.'}</strong></p>
          <ul>{checked.detail.comparability.differences.map(d => <li key={d.field}>
            {(FIELD[d.field] ?? [d.field, d.field])[cs ? 0 : 1]}: {String(d.selected).slice(0, 24)} → {String(d.comparison).slice(0, 24)}</li>)}</ul></div>}
      <p>{cs ? 'Porovnávají se jen: ' : 'Compared only: '}{checked.detail.comparability.compared_fields.join(', ')}
        {' · '}{cs ? 'neporovnáno: ' : 'not compared: '}{checked.detail.comparability.not_compared.join(', ')}</p>
      <p>{cs ? 'Chybějící strana znamená, že hráč či země v dané sezóně nebyly v Edicích zastoupeny; to není nula.'
        : 'A missing side means the player or country was not represented in that season’s Editions; that is not zero.'}</p>
      <h5>{cs ? 'Země' : 'Countries'}</h5>
      {comparisonTable(checked.detail.countries, 'country_code')}
      <details><summary>{cs ? 'Hráči' : 'Players'}</summary>
        {comparisonTable(checked.detail.players, 'player_id')}</details>
    </div>}
  </section>
}
