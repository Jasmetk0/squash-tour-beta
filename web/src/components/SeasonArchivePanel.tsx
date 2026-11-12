import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { getSeasonArchive, getSeasonDetail } from '../api/client'
import { validSeasonArchive, validSeasonDetail } from '../api/seasonArchive'
import type { PresenceRow } from '../api/seasonArchive'
import { formatApiError } from '../utils/apiErrors'

type Props = {
  runId: string; branchId: string; savedHead: string; cs: boolean
  playerName?: (id: string) => string
}

const FIELD: Record<string, [string, string]> = {
  ranking_policy_id: ['ID ranking politiky', 'ranking policy id'],
  ranking_best_n: ['Best N', 'Best N'],
  development_policy_fingerprint: ['politika vývoje hráčů', 'player development policy'],
  weeks_per_season: ['týdnů v sezóně', 'weeks per season']
}

export function SeasonArchivePanel({ runId, branchId, savedHead, cs, playerName }: Props): JSX.Element {
  const [selected, setSelected] = useState<number | null>(null)
  const [other, setOther] = useState<number | null>(null)
  const title = cs ? 'Archiv sezón a porovnání' : 'Season archive and comparison'
  const archiveQuery = useQuery({
    queryKey: ['season-archive', runId, branchId, savedHead],
    queryFn: () => getSeasonArchive(runId, branchId), retry: false
  })
  const detailQuery = useQuery({
    queryKey: ['season-detail', runId, branchId, savedHead, selected, other],
    queryFn: () => getSeasonDetail(runId, branchId, selected!, other!),
    enabled: selected !== null && other !== null && selected !== other, retry: false
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
    {archive.seasons.length === 0
      ? <p>{cs ? 'Zatím není dokončena žádná sezóna.' : 'No season is completed yet.'}</p>
      : <div className="table-responsive"><table aria-label={cs ? 'Archiv dokončených sezón' : 'Completed season archive'}>
        <thead><tr><th>{cs ? 'Sezóna' : 'Season'}</th><th>{cs ? 'Edice' : 'Editions'}</th>
          <th>{cs ? 'Vedoucí hráč' : 'Leading player'}</th><th>{cs ? 'Vedoucí země (tituly, body)' : 'Leading country (titles, points)'}</th>
          <th>{cs ? 'Profesionálem / konec' : 'Turned pro / retired'}</th><th>Best N</th><th /></tr></thead>
        <tbody>{archive.seasons.map(s => <tr key={s.season_index}>
          <td>{s.season_label}</td>
          <td>{s.overview.no_completed_editions ? (cs ? 'žádná dokončená' : 'none completed') : s.overview.completed_edition_count}</td>
          <td>{s.leading_player ? `${name(s.leading_player.player_id)} (${s.leading_player.titles})` : '—'}</td>
          <td>{s.leading_country ? `${s.leading_country.country_code} (${s.leading_country.titles}, ${s.leading_country.awarded_points})` : '—'}</td>
          <td>{s.overview.turned_pro.length} / {s.overview.retired.length}</td>
          <td>{s.rules.ranking_best_n}</td>
          <td><button type="button" aria-pressed={selected === s.season_index} onClick={() => setSelected(s.season_index)}>
            {cs ? 'Vybrat' : 'Select'} {s.season_label}</button></td>
        </tr>)}</tbody></table></div>}
    {archive.seasons.length > 1 && <>
      <label>{cs ? 'Vybraná sezóna' : 'Selected season'}{' '}
        <select value={selected ?? ''} onChange={e => setSelected(e.target.value === '' ? null : Number(e.target.value))}>
          <option value="">—</option>{archive.seasons.map(s => <option key={s.season_index} value={s.season_index}>{s.season_label}</option>)}
        </select></label>{' '}
      <label>{cs ? 'Porovnat s' : 'Compare with'}{' '}
        <select value={other ?? ''} onChange={e => setOther(e.target.value === '' ? null : Number(e.target.value))}>
          <option value="">—</option>{archive.seasons.filter(s => s.season_index !== selected)
            .map(s => <option key={s.season_index} value={s.season_index}>{s.season_label}</option>)}
        </select></label>
    </>}
    {detailQuery.isPending && selected !== null && other !== null && <p role="status">{cs ? 'Načítám porovnání…' : 'Loading comparison…'}</p>}
    {detailQuery.error && <p role="status">{formatApiError(detailQuery.error)}</p>}
    {detail && !checked && <p role="alert">{cs
      ? 'Porovnání neodpovídá vybrané revizi nebo sezónám a nebylo zobrazeno.'
      : 'The comparison does not match the selected revision or seasons and was not displayed.'}</p>}
    {checked && selected !== null && other !== null && <div aria-label={cs ? 'Porovnání sezón' : 'Season comparison'}>
      <h4>{label(selected)} {cs ? 'oproti' : 'vs'} {label(other)}</h4>
      {checked.detail.comparability.comparable
        ? <p role="status">{cs ? 'Zaznamenaná pravidla (ranking a vývoj hráčů) jsou v obou sezónách stejná.' : 'The recorded rules (ranking and player development) are the same in both seasons.'}</p>
        : <div role="alert"><p><strong>{cs ? 'Omezená srovnatelnost: pravidla se mezi sezónami liší.' : 'Limited comparability: the rules differ between the seasons.'}</strong></p>
          <ul>{checked.detail.comparability.differences.map(d => <li key={d.field}>
            {(FIELD[d.field] ?? [d.field, d.field])[cs ? 0 : 1]}: {String(d.selected).slice(0, 24)} → {String(d.comparison).slice(0, 24)}</li>)}</ul></div>}
      <p>{cs ? 'Porovnávají se jen: ' : 'Compared only: '}{checked.detail.comparability.compared_fields.join(', ')}
        {' · '}{cs ? 'neporovnáno: ' : 'not compared: '}{checked.detail.comparability.not_compared.join(', ')}</p>
      <p>{cs ? 'Chybějící strana znamená, že hráč či země v dané sezóně nebyly v Edicích zastoupeny; to není nula.'
        : 'A missing side means the player or country was not represented in that season’s Editions; that is not zero.'}</p>
      <h5>{cs ? 'Země' : 'Countries'}</h5>
      <div className="table-responsive"><table>{head(cs ? 'Země' : 'Country')}<tbody>{rows(checked.detail.countries, 'country_code')}</tbody></table></div>
      <details><summary>{cs ? 'Hráči' : 'Players'}</summary>
        <div className="table-responsive"><table>{head(cs ? 'Hráč' : 'Player')}<tbody>{rows(checked.detail.players, 'player_id')}</tbody></table></div></details>
    </div>}
  </section>
}
