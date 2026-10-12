/** Real player identities, only from the selected Branch's immutable Saved HEAD.
 * Not a synthetic intake forecast; a World data-year selector never time-travels this roster.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getSavedPlayersInventory } from '../api/client'
import type { SavedPlayersInventory, SavedInventoryPlayer } from '../api/types'
import { formatApiError } from '../utils/apiErrors'

const PAGE_SIZE = 25

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
  countryCode: string, includePrepared: boolean, offset: number
): data is SavedPlayersInventory {
  return Boolean(data &&
    data.schema_version === 'saved_players_inventory.v1' &&
    data.run_id === runId &&
    data.branch_id === branchId &&
    data.saved_revision_id === savedHead &&
    data.source === 'selected_branch_saved_revision' &&
    data.time_context === 'present' &&
    data.country_code === countryCode &&
    data.search === '' &&
    data.status_filter === '' &&
    data.include_prepared === includePrepared &&
    data.offset === offset &&
    data.limit === PAGE_SIZE &&
    Number.isSafeInteger(data.total) && data.total >= 0 &&
    data.has_more === (offset + PAGE_SIZE < data.total) &&
    Array.isArray(data.players) && data.players.length <= PAGE_SIZE &&
    new Set(data.players.map(p => p.player_id)).size === data.players.length &&
    data.players.every(p => p.country_code === countryCode && Boolean(p.player_id))
  )
}

function ranking(player: SavedInventoryPlayer, cs: boolean): string {
  if (player.ranking_status === 'unpublished') return cs ? 'Nepublikováno' : 'Unpublished'
  return player.ranking_status === 'ranked' && player.rank != null
    ? '#'+player.rank : 'NR'
}

export function RunWorldCountrySavedPlayers({
  runId, branchId, savedHead, countryCode, selectedWorldYear, language
}: Props): JSX.Element {
  const cs = language === 'cs'
  const [includePrepared, setIncludePrepared] = useState(false)
  const [page, setPage] = useState(0)
  const offset = page * PAGE_SIZE
  const enabled = Boolean(runId && branchId && savedHead && countryCode)
  const q = useQuery({
    queryKey: [
      'run-world-country-saved-roster',runId,branchId,savedHead,
      countryCode,includePrepared,offset
    ],
    queryFn:()=>getSavedPlayersInventory(runId,branchId,savedHead!,{
      search:'',country_code:countryCode,status_filter:'',
      include_prepared:includePrepared,offset,limit:PAGE_SIZE
    }),
    enabled,
    retry:false
  })
  const correct = savedHead != null && validCountryInventory(
    q.data,runId,branchId,savedHead,countryCode,includePrepared,offset
  )
  const data = correct ? q.data : null
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
    <label>
      <input type="checkbox" checked={includePrepared}
        onChange={e=>{setIncludePrepared(e.target.checked);setPage(0)}} />
      {' '}{cs
        ? 'Výslovně zobrazit také uložené připravené prospekty (mohou být z budoucnosti)'
        : 'Explicitly include saved prepared prospects (may contain future identities)'}
    </label>
    {enabled && q.isPending && <p role="status">{cs
      ? 'Načítám ověřené hráče…' : 'Loading verified saved players…'}</p>}
    {enabled && q.error && <p role="alert">{formatApiError(q.error)}</p>}
    {enabled && q.isSuccess && !correct && <p role="alert">{cs
      ? 'Odpověď nesouhlasí s Runem, branchí, uloženou revizí nebo zemí. Nezobrazí se.'
      : 'Response scope does not match the Run, Branch, Saved Revision or country. Players are hidden.'}</p>}
    {data && <>
      <p role="status">{cs ? 'Hráčů v uloženém inventáři země' : 'Saved players in this country'}:
        {' '}<strong>{data.total.toLocaleString(cs?'cs-CZ':'en-US')}</strong>
        {' '}· {cs?'Zobrazeno':'Showing'} {data.players.length}
      </p>
      <div className="table-responsive"><table aria-label="Saved country roster">
        <thead><tr><th>{cs?'Hráč':'Player'}</th><th>{cs?'Věk':'Age'}</th>
          <th>Status</th><th>OVR</th><th>Potential OVR</th><th>Ranking / NR</th>
        </tr></thead>
        <tbody>{data.players.map(player=><tr key={player.player_id}>
          <td><Link to={'/admin/runs/'+encodeURIComponent(runId)+'/people/'+encodeURIComponent(player.player_id)}>
            {player.display_name}</Link> <small>· {player.player_id}</small></td>
          <td>{player.age??'—'}</td>
          <td>{player.status??'—'}</td><td>{player.ovr??'—'}</td>
          <td>{player.potential_ovr??'—'}</td><td>{ranking(player,cs)}</td>
        </tr>)}</tbody></table></div>
      {data.total===0 && <p role="status">{cs
        ? 'Tato země nemá v uloženém inventáři odpovídající hráče. Nejde o odhad talentů.'
        : 'No saved player identities match this country. This is not a talent forecast.'}</p>}
      <div className="actions">
        <button type="button" disabled={page===0} onClick={()=>setPage(p=>Math.max(0,p-1))}>
          {cs?'← Předchozí':'← Previous'}</button>
        <span>{cs?'Strana':'Page'} {page+1} / {Math.max(1,Math.ceil(data.total/PAGE_SIZE))}</span>
        <button type="button" disabled={!data.has_more} onClick={()=>setPage(p=>p+1)}>
          {cs?'Další →':'Next →'}</button>
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
