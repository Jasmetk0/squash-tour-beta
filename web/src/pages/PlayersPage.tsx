/** Product Players inventory: only the selected Branch immutable Saved HEAD. */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getSavedPlayersInventory } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

const PAGE_SIZE = 50

export function PlayersPage(): JSX.Element {
  const {runId}=useParams(),{selectedBranch}=useAdminBranch(),time=useAdminTime()
  return <PlayersInventory key={JSON.stringify([runId,selectedBranch?.branch_id,selectedBranch?.saved_head_revision_id,time.mode,time.viewCheckpointId])}/>
}

function PlayersInventory(): JSX.Element {
  const { runId = '' } = useParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const { selectedBranch, isLoading, error } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const savedHead = selectedBranch?.saved_head_revision_id || null
  const [search, setSearch] = useState('')
  const [country, setCountry] = useState('')
  const [status, setStatus] = useState('')
  const [rankingFilter,setRankingFilter]=useState<''|'ranked'|'unranked'|'unpublished'>('')
  const [includePrepared, setIncludePrepared] = useState(false)
  const [page, setPage] = useState(0)
  const filters = {
    search: search.trim(), country_code: country.trim().toUpperCase(),
    status_filter: status.trim(), include_prepared: includePrepared,
    ...(rankingFilter?{ranking_status_filter:rankingFilter}:{}),
    offset: page * PAGE_SIZE, limit: PAGE_SIZE,
  }
  const ready = Boolean(runId && branchId && savedHead && !isLoading && !error && time.mode === 'present' && !time.isLoading && !time.error)
  const q = useQuery({
    queryKey: ['canonical-saved-players', runId, branchId, savedHead,
      time.mode, time.viewCheckpointId, filters],
    queryFn: () => getSavedPlayersInventory(runId, branchId!, savedHead!, filters),
    enabled: ready,
    retry: false,
  })
  const scoped = ready && q.data?.run_id === runId && q.data?.branch_id === branchId &&
    q.data?.saved_revision_id === savedHead && q.data?.time_context === 'present' &&
    q.data?.offset === filters.offset && q.data?.limit === PAGE_SIZE &&
    q.data.search===filters.search&&q.data.country_code===filters.country_code&&
    q.data.status_filter===filters.status_filter&&q.data.include_prepared===filters.include_prepared&&
    (q.data.ranking_status_filter??'')===rankingFilter
  const data = scoped && q.isSuccess && !q.isFetching ? q.data : null
  const rankingCounts=data?(['ranked','unranked','unpublished'] as const).map(value=>({
    value,count:data.players.filter(p=>p.ranking_status===value).length
  })):[]
  const update = (setter: (value: string) => void, value: string) => {
    setter(value)
    setPage(0)
  }
  const availability = (value: number | null): string | number => value ?? '—'
  const ranking = (player: import('../api/types').SavedInventoryPlayer): string => {
    if (player.ranking_status === 'unpublished') return cs ? 'Nepublikováno' : 'Unpublished'
    return player.ranking_status === 'ranked' ? `#${player.rank}` : 'NR'
  }

  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · CANONICAL PLAYERS</p>
      <h2>{cs ? 'Hráči' : 'Players'}</h2>
      <p className="subtitle">{cs
        ? 'Ověřené identity pouze z uložené revize vybrané branche. Čtení nemění Run.'
        : 'Verified identities from the selected Branch Saved Revision only. Reading never modifies the Run.'}</p>
    </div>
    <div className="run-home-status-block">
      <p><strong>Run:</strong> <code>{runId}</code></p>
      <p><strong>Branch:</strong> {selectedBranch?.display_name ?? '—'}</p>
      <p><strong>Saved Revision:</strong> <code>{savedHead ?? '—'}</code></p>
      <p><strong>{cs ? 'Čas' : 'Time'}:</strong> {time.mode === 'present'
        ? (cs ? 'Současný uložený stav' : 'Current saved state')
        : (cs ? 'Historický checkpoint' : 'Historical checkpoint')}</p>
    </div>
    {time.mode !== 'present' ? <p role="status">{cs
      ? 'Historická projekce hráčů pro zvolený checkpoint zatím není podporována. Současné hráče nezobrazujeme jako minulost.'
      : 'Historical player projection is not supported for this checkpoint. Present players are not presented as history.'}</p> :
      <>
        {isLoading && <p role="status">{cs ? 'Načítám branch…' : 'Loading Branch…'}</p>}
        {error && <p role="alert" className="error">{error}</p>}
        {!savedHead && !isLoading && !error && <p role="alert">{cs
          ? 'Chybí ověřená Saved Revision. Seznam nelze načíst.'
          : 'No verified Saved Revision. Inventory is unavailable.'}</p>}
        <div className="actions">
          <Link to={`/admin/runs/${encodeURIComponent(runId)}/players/generate`}>
            {cs ? 'Generovat' : 'Generate'} →
          </Link>
          <span className="status">{cs ? 'Vytvořit hráče a Import: zatím nejsou připojeny ke canonical Working Draftu' : 'Create and Import: not yet connected to canonical Working Draft'}</span>
        </div>
        <section aria-label="Saved player filters">
          <h3>{cs ? 'Hledání a filtry' : 'Search and filters'}</h3>
          <div className="form-grid">
            <label>{cs ? 'Jméno nebo ID' : 'Name or ID'}
              <input data-run-navigation-readonly aria-label="Player search"
                value={search} maxLength={120} onChange={e=>update(setSearch,e.target.value)} />
            </label>
            <label>{cs ? 'Sportovní země (3 písmena)' : 'Sport country (3 letters)'}
              <input data-run-navigation-readonly aria-label="Player country"
                value={country} maxLength={3} onChange={e=>update(setCountry,e.target.value)} />
            </label>
            <label>{cs ? 'Status (přesná hodnota)' : 'Status (exact value)'}
              <input data-run-navigation-readonly aria-label="Player status"
                value={status} maxLength={80} onChange={e=>update(setStatus,e.target.value)} />
            </label>
          </div>
          <label data-run-navigation-readonly>{cs?'Stav rankingu':'Ranking status'}
            <select aria-label="Ranking status filter" value={rankingFilter} onChange={e=>{
              setRankingFilter(e.target.value as typeof rankingFilter);setPage(0)
            }}>
              <option value="">{cs?'Všechny stavy':'All statuses'}</option>
              <option value="ranked">{cs?'V rankingu':'Ranked'}</option>
              <option value="unranked">{cs?'Mimo ranking po publikaci':'Unranked after publication'}</option>
              <option value="unpublished">{cs?'Ranking nepublikován':'Ranking unpublished'}</option>
            </select>
          </label>
          <button type="button" onClick={()=>{setSearch('');setCountry('');setStatus('');setRankingFilter('');setIncludePrepared(false);setPage(0)}}>
            {cs?'Obnovit výchozí filtry':'Reset filters'}</button>
          <label><input type="checkbox" data-run-navigation-readonly
            checked={includePrepared} onChange={e=>{setIncludePrepared(e.target.checked);setPage(0)}} />
            {' '}{cs ? 'Admin: výslovně zobrazit i uložené připravené prospekty (mohou být z budoucnosti)'
              : 'Admin: explicitly reveal saved prepared prospects (may include future players)'}
          </label>
        </section>
        {(q.isPending||q.isFetching) && ready && <p role="status">{cs ? 'Načítám hráče…' : 'Loading players…'}</p>}
        {q.error && <p role="alert" className="error">{formatApiError(q.error)}</p>}
        {ready && q.isSuccess && !q.isFetching && !scoped && <p role="alert" className="error">{cs
          ? 'Odpověď nepatří zvolené branchi nebo revizi.' : 'Response does not belong to selected Branch or revision.'}</p>}
        {data && <>
          <p role="status">{cs ? 'Celkový počet odpovídajících hráčů' : 'Total matching players'}:
            {' '}<strong>{data.total.toLocaleString(language === 'cs' ? 'cs-CZ' : 'en-US')}</strong>
            {' · '}{cs ? 'Zobrazeno' : 'Showing'} {data.players.length}
            {data.ranking_week_ordinal != null ? ` · ${cs ? 'Publikace žebříčku · index týdne' : 'Ranking publication · week index'} ${data.ranking_week_ordinal}` : ''}
          </p>
          {data.players.length>0&&<section aria-label={cs?'Přehled načtené stránky':'Loaded page overview'}>
            <h4>{cs?'Ranking na této stránce':'Ranking on this page'}</h4>
            <div className="grid">{rankingCounts.map(item=><div key={item.value} className="section-subtle">
              <p>{item.value==='ranked'?(cs?'V rankingu':'Ranked'):
                item.value==='unranked'?(cs?'Mimo ranking':'Unranked'):(cs?'Nepublikováno':'Unpublished')}</p>
              <strong>{item.count} / {data.players.length}</strong>
            </div>)}</div>
            <p className="status">{cs?'Počty platí pouze pro načtenou stránku, nikoli celý Run.':
              'Counts cover this loaded page only, not the entire Run.'}</p>
          </section>}
          <div className="table-responsive">
            <table>
              <thead><tr>
                <th>{cs ? 'Jméno / profil' : 'Name / profile'}</th>
                <th>{cs ? 'Země' : 'Country'}</th>
                <th>{cs ? 'Věk' : 'Age'}</th>
                <th>Status</th><th>OVR</th><th>Potential OVR</th><th>Ranking / NR</th>
              </tr></thead>
              <tbody>{data.players.map(player=><tr key={player.player_id}>
                <td><Link to={`/admin/runs/${encodeURIComponent(runId)}/people/${encodeURIComponent(player.player_id)}`}>
                  {player.display_name}
                </Link><small className="status"> · {player.player_id}</small></td>
                <td>{player.country_code}</td><td>{availability(player.age)}</td>
                <td>{player.status ?? '—'}</td><td>{availability(player.ovr)}</td>
                <td>{availability(player.potential_ovr)}</td><td>{ranking(player)}</td>
              </tr>)}</tbody>
            </table>
          </div>
          {data.total === 0 && <p className="status">{cs
            ? 'Žádní hráči v tomto uloženém stavu nebo výběru. Žádná legacy data nedoplňujeme.'
            : 'No players in this saved scope or filter. Legacy data is never substituted.'}</p>}
          <div className="actions">
            <button type="button" disabled={page===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>
              {cs ? '← Předchozí' : '← Previous'}</button>
            <span>{cs ? 'Strana' : 'Page'} {page+1} / {Math.max(1,Math.ceil(data.total/PAGE_SIZE))}</span>
            <button type="button" disabled={!data.has_more} onClick={()=>setPage(p=>p+1)}>
              {cs ? 'Další →' : 'Next →'}</button>
          </div>
        </>}
        <p className="status">{cs
          ? '— = hodnota není v autoritativním snapshotu dostupná. NR používáme jen po publikování rankingu. Starší 1–99 schopnosti nejsou OVR na škále 0–200.'
          : '— = unavailable in the authoritative snapshot. NR appears only after a ranking publication. Legacy 1–99 ability is not 0–200 OVR.'}</p>
      </>
    }
    <p><Link to={`/admin/runs/${encodeURIComponent(runId)}/players/legacy`}>
      {cs ? 'Diagnostický legacy Run Explorer →' : 'Legacy Run Explorer diagnostics →'}</Link></p>
  </section>
}
