/** Real player identities, only from the selected Branch's immutable Saved HEAD.
 * Not a synthetic intake forecast; a World data-year selector never time-travels this roster.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { getSavedPlayersInventory } from '../api/client'
import type { SavedPlayersInventory, SavedInventoryPlayer } from '../api/types'
import { formatApiError } from '../utils/apiErrors'
import {countryRosterReturnPath,readCountryRosterPermalink,writeCountryRosterPermalink}
  from './countrySavedRosterPermalink'

const PAGE_SIZE = 25

/** Strictly bounded, one-based navigation. Never request an invalid server offset. */
function validatedPage(raw: string, pages: number): number | null {
  if (!Number.isSafeInteger(pages) || pages < 1 || pages > 1_000_000 ||
      !/^[1-9]\d{0,6}$/.test(raw)) return null
  const value = Number(raw)
  return value <= pages ? value - 1 : null
}

type Props = {
  runId: string
  branchId: string
  savedHead: string | null
  countryCode: string
  selectedWorldYear: number
  language: 'cs' | 'en'
}

function validCountryInventory(
  data: SavedPlayersInventory | undefined,
  runId: string, branchId: string, savedHead: string,
  countryCode: string, search: string, statusFilter: string,
  rankingFilter: string, includePrepared: boolean, offset: number
): data is SavedPlayersInventory {
  return Boolean(data &&
    data.schema_version === 'saved_players_inventory.v1' &&
    data.run_id === runId &&
    data.branch_id === branchId &&
    data.saved_revision_id === savedHead &&
    data.source === 'selected_branch_saved_revision' &&
    data.time_context === 'present' &&
    data.country_code === countryCode &&
    data.search === search &&
    data.status_filter === statusFilter &&
    (data.ranking_status_filter ?? "") === rankingFilter &&
    data.include_prepared === includePrepared &&
    data.offset === offset &&
    data.limit === PAGE_SIZE &&
    Number.isSafeInteger(data.total) && data.total >= 0 &&
    data.has_more === (offset + PAGE_SIZE < data.total) &&
    Array.isArray(data.players) && data.players.length <= PAGE_SIZE &&
    new Set(data.players.map(p => p.player_id)).size === data.players.length &&
    data.players.every(p => p.country_code === countryCode && Boolean(p.player_id) &&
      (!rankingFilter || p.ranking_status === rankingFilter))
  )
}

function ranking(player: SavedInventoryPlayer, cs: boolean): string {
  if (player.ranking_status === 'unpublished') return cs ? 'Nepublikováno' : 'Unpublished'
  return player.ranking_status === 'ranked' && player.rank != null
    ? '#'+player.rank : 'NR'
}

/** A different Saved Run/Branch/HEAD/country cannot inherit the old search or cursor. */
export function RunWorldCountrySavedPlayers(props: Props): JSX.Element {
  const { runId, branchId, savedHead, countryCode } = props
  const [params] = useSearchParams()
  // React Router can change only the search string while keeping the same
  // Country component mounted (browser Back, copied bookmark, in-app links).
  // Mount the view for the URL's exact roster selection as well as its Saved
  // source, so stale draft state, page or future opt-in never overrides it.
  const rosterLocationKey = JSON.stringify([
    runId, branchId, savedHead, countryCode,
    ...['spScope', 'spSearch', 'spStatus', 'spRanking', 'spPrepared', 'spPage']
      .map(param => params.getAll(param)),
  ])
  return <ScopedCountryRoster key={rosterLocationKey} {...props} />
}
function ScopedCountryRoster({
  runId, branchId, savedHead, countryCode, selectedWorldYear, language
}: Props): JSX.Element {
  const cs = language === 'cs'
  const [urlParams, setUrlParams] = useSearchParams()
  const sourceKey = JSON.stringify([runId, branchId, savedHead, countryCode])
  // Only the exact immutable source may restore a bookmarked roster view.
  const initialView = readCountryRosterPermalink(urlParams,sourceKey)
  const [includePrepared, setIncludePrepared] = useState(initialView.includePrepared)
  const [draft, setDraft] = useState({ search: initialView.search, status: initialView.status,
    ranking: initialView.ranking ?? '' })
  const [filters, setFilters] = useState({ search: initialView.search, status: initialView.status,
    ranking: initialView.ranking ?? '' })
  const pageKey = JSON.stringify([sourceKey, filters.search, filters.status, filters.ranking, includePrepared])
  const [pageSelection, setPageSelection] = useState({ sourceKey: pageKey, page: initialView.page })
  const [pageInput, setPageInput] = useState({ sourceKey: pageKey,
    value: String(initialView.page + 1) })
  // Changes to source, search, exact status or prepared visibility reset the cursor
  // in the same render: never request offset 25 from a new filtered result.
  const page = pageSelection.sourceKey === pageKey ? pageSelection.page : 0
  const jump = pageInput.sourceKey === pageKey ? pageInput.value : '1'
  const syncUrl = (search: string, status: string,
    ranking: typeof filters.ranking, prepared: boolean, nextPage: number) => {
    setUrlParams(writeCountryRosterPermalink(urlParams,sourceKey,{
      search,status,ranking:ranking || undefined,includePrepared:prepared,page:nextPage,
    }),{replace:true})
  }
  const movePage = (next: number) => {
    setPageSelection({ sourceKey: pageKey, page: next })
    setPageInput({ sourceKey: pageKey, value: String(next + 1) })
    syncUrl(filters.search,filters.status,filters.ranking,includePrepared,next)
  }
  const applyFilters = (next: typeof filters) => {
    setFilters(next)
    const nextKey = JSON.stringify([sourceKey, next.search, next.status, next.ranking, includePrepared])
    setPageSelection({ sourceKey: nextKey, page: 0 })
    setPageInput({ sourceKey: nextKey, value: '1' })
    syncUrl(next.search,next.status,next.ranking,includePrepared,0)
  }
  const offset = page * PAGE_SIZE
  const enabled = Boolean(runId && branchId && savedHead && countryCode)
  const q = useQuery({
    queryKey: [
      'run-world-country-saved-roster',runId,branchId,savedHead,
      countryCode,filters.search,filters.status,filters.ranking,includePrepared,offset
    ],
    queryFn:()=>getSavedPlayersInventory(runId,branchId,savedHead!,{
      search:filters.search,country_code:countryCode,status_filter:filters.status,
      ranking_status_filter:filters.ranking,
      include_prepared:includePrepared,offset,limit:PAGE_SIZE
    }),
    enabled,
    retry:false
  })
  const correct = savedHead != null && validCountryInventory(
    q.data,runId,branchId,savedHead,countryCode,
    filters.search,filters.status,filters.ranking,includePrepared,offset
  )
  const data = correct && !q.isFetching ? q.data : null
  const pageCount = data ? Math.ceil(data.total/PAGE_SIZE) : 0
  const outOfRange = Boolean(data && page > 0 && offset >= data.total)
  const targetPage = validatedPage(jump, pageCount)
  const returnToCountry = countryRosterReturnPath(runId,countryCode,
    writeCountryRosterPermalink(urlParams,sourceKey,{
      search:filters.search,status:filters.status,ranking:filters.ranking||undefined,includePrepared,page,
    }))
  return <section className="section-subtle run-world-country-roster"
    aria-label="Run World canonical country players">
    <h4>{cs ? 'Uložení hráči země' : 'Saved country players'}</h4>
    <p className="status">{cs
      ? 'Toto je aktuální inventář skutečně uložené revize vybrané branche, nikoli historický soupis z roku '
      : 'This is the current selected Branch Saved Revision roster, NOT a historical roster for World year '}
      <strong>{selectedWorldYear}</strong>.
      {' '}{cs ? 'Náhled nic nezapisuje.' : 'The view never writes.'}</p>
    {savedHead
      ? <p className="status">Saved Revision: <code>{savedHead}</code></p>
      : <p role="alert">{cs
        ? 'Není dostupná autoritativní uložená revize. Žádní hráči se nedoplňují z legacy dat.'
        : 'No authoritative Saved Revision is available. Legacy players are never substituted.'}</p>}
    <form className="actions" aria-label="Country roster filters" onSubmit={e=>{
      e.preventDefault()
      applyFilters({search:draft.search.trim(),status:draft.status.trim(),ranking:draft.ranking})
    }}>
      <label>{cs ? 'Hledat jméno nebo ID' : 'Find name or player ID'}{' '}
        <input aria-label="Country roster search" type="search" maxLength={120}
          placeholder={cs ? 'Jméno / ID hráče' : 'Player name / ID'}
          value={draft.search} onChange={e=>setDraft(prev=>({...prev,search:e.target.value}))}/>
      </label>
      <label>{cs ? 'Přesný status' : 'Exact status'}{' '}
        <input aria-label="Country roster status" type="text" maxLength={80}
          placeholder={cs ? 'Např. active' : 'e.g. active'}
          value={draft.status} onChange={e=>setDraft(prev=>({...prev,status:e.target.value}))}/>
      </label>
      <label>{cs ? 'Žebříček' : 'Ranking publication'}{' '}
        <select aria-label="Country roster ranking status"
          value={draft.ranking}
          onChange={e=>setDraft(prev=>({...prev,
            ranking:e.target.value as typeof prev.ranking}))}>
          <option value="">{cs?'Všechny stavy':'All states'}</option>
          <option value="ranked">{cs?'V žebříčku':'Ranked'}</option>
          <option value="unranked">{cs?'Mimo žebříček':'Unranked'}</option>
          <option value="unpublished">{cs?'Dosud nepublikováno':'Unpublished'}</option>
        </select>
      </label>
      <button type="submit">{cs ? 'Použít filtry' : 'Apply filters'}</button>
      <button type="button" onClick={()=>{
        setDraft({search:'',status:'',ranking:''})
        applyFilters({search:'',status:'',ranking:''})
      }}>{cs ? 'Vymazat filtry' : 'Clear filters'}</button>
    </form>
    {(filters.search || filters.status || filters.ranking) && <p role="status">{cs
      ? 'Filtry se uplatní na celou uloženou soupisku před stránkováním.'
      : 'Filters apply to the full Saved roster before pagination.'}
      {filters.search && <> · {cs?'Hledání':'Search'}: <strong>{filters.search}</strong></>}
      {filters.status && <> · Status: <strong>{filters.status}</strong></>}
      {filters.ranking && <> · {cs?'Žebříček':'Ranking'}: <strong>{filters.ranking}</strong></>}
    </p>}
    <label>
      <input type="checkbox" checked={includePrepared}
        onChange={e=>{
          setIncludePrepared(e.target.checked)
          const nextKey = JSON.stringify([sourceKey, filters.search,
            filters.status, filters.ranking, e.target.checked])
          setPageSelection({ sourceKey: nextKey, page: 0 })
          setPageInput({ sourceKey: nextKey, value: '1' })
          syncUrl(filters.search,filters.status,filters.ranking,e.target.checked,0)
        }} />
      {' '}{cs
        ? 'Výslovně zobrazit také uložené připravené prospekty (mohou být z budoucnosti)'
        : 'Explicitly include saved prepared prospects (may contain future identities)'}
    </label>
    {enabled && (q.isPending || q.isFetching) && <p role="status">{cs
      ? 'Načítám ověřené hráče…' : 'Loading verified saved players…'}</p>}
    {enabled && q.error && <p role="alert">{formatApiError(q.error)}</p>}
    {enabled && q.isSuccess && !q.isFetching && !correct && <p role="alert">{cs
      ? 'Odpověď nesouhlasí s Runem, branchí, uloženou revizí nebo zemí. Nezobrazí se.'
      : 'Response scope does not match the Run, Branch, Saved Revision or country. Players are hidden.'}</p>}
    {data && <>
      <p role="status">{cs ? 'Hráčů v uloženém inventáři země' : 'Saved players in this country'}:
        {' '}<strong>{data.total.toLocaleString(cs?'cs-CZ':'en-US')}</strong>
        {' '}· {cs?'Zobrazeno':'Showing'} {data.players.length}
        {!outOfRange && data.total>0 && <>
          {' '}· {cs?'Položky':'Rows'} {offset+1}–{offset+data.players.length}
          {' '}{cs?'z':'of'} {data.total.toLocaleString(cs?'cs-CZ':'en-US')}
        </>}
      </p>
      {outOfRange && <p role="alert">{cs
        ? 'Zvolená stránka již v tomto uloženém výběru neexistuje.'
        : 'The selected page no longer exists in this Saved result.'}{' '}
        <button type="button" onClick={()=>movePage(0)}>
          {cs?'První platná stránka':'First valid page'}</button>{' '}
        <button type="button" onClick={()=>movePage(Math.max(0,pageCount-1))}>
          {cs?'Poslední platná stránka':'Last valid page'}</button></p>}
      {!outOfRange && <div className="table-responsive"><table aria-label="Saved country roster">
        <thead><tr><th>{cs?'Hráč':'Player'}</th><th>{cs?'Věk':'Age'}</th>
          <th>Status</th><th>OVR</th><th>Potential OVR</th><th>Ranking / NR</th>
        </tr></thead>
        <tbody>{data.players.map(player=><tr key={player.player_id}>
          <td><Link to={'/admin/runs/'+encodeURIComponent(runId)+'/people/'+
            encodeURIComponent(player.player_id)+'?'+new URLSearchParams({
              fromCountry:returnToCountry,
            }).toString()}>
            {player.display_name}</Link> <small>· {player.player_id}</small></td>
          <td>{player.age??'—'}</td>
          <td>{player.status??'—'}</td><td>{player.ovr??'—'}</td>
          <td>{player.potential_ovr??'—'}</td><td>{ranking(player,cs)}</td>
        </tr>)}</tbody></table></div>}
      {data.total===0 && <p role="status">{cs
        ? 'Tato země nemá v uloženém inventáři odpovídající hráče. Nejde o odhad talentů.'
        : 'No saved player identities match this country. This is not a talent forecast.'}</p>}
      <div className="actions" aria-label="Country roster pagination">
        <button type="button" disabled={page===0||q.isFetching} onClick={()=>movePage(0)}>
          {cs?'První':'First'}</button>
        <button type="button" disabled={page===0||q.isFetching} onClick={()=>movePage(Math.max(0,page-1))}>
          {cs?'← Předchozí':'← Previous'}</button>
        <span aria-live="polite">{cs?'Strana':'Page'} {pageCount===0?0:page+1} / {pageCount}</span>
        <button type="button" disabled={!data.has_more||q.isFetching||outOfRange} onClick={()=>movePage(page+1)}>
          {cs?'Další →':'Next →'}</button>
        <button type="button" disabled={pageCount===0||page>=pageCount-1||q.isFetching}
          onClick={()=>movePage(pageCount-1)}>{cs?'Poslední':'Last'}</button>
        <label>{cs?'Přejít na stránku':'Go to page'}{' '}
          <input aria-label="Country roster page number" inputMode="numeric"
            value={jump} disabled={pageCount===0||q.isFetching}
            onChange={e=>setPageInput({sourceKey:pageKey,value:e.target.value})}
            style={{width:'5rem'}} />
        </label>
        <button type="button" disabled={targetPage===null||targetPage===page||outOfRange||q.isFetching}
          onClick={()=>{if(targetPage!==null)movePage(targetPage)}}>
          {cs?'Přejít':'Go'}</button>
      </div>
    </>}
    <p className="status">{cs
      ? 'Předpověď nových talentů, intake a generační potenciál jsou oddělené simulace. Počty v tomto seznamu nejsou odhadem budoucích hráčů.'
      : 'Future talent intake, generation and potential are separate simulations. This inventory does not predict future players.'}</p>
    <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/players'}>
      {cs?'Otevřít úplný uložený seznam hráčů':'Open full saved players inventory'} →
    </Link>
  </section>
}
