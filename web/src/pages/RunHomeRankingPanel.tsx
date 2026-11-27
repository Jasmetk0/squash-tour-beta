import { useState } from 'react'
import { HomePlayerIdentityLink } from './HomePlayerIdentityLink'
import type { SavedHomePlayerIdentity } from '../api/types'
import type { RunHomeRankingChanges, RunHomeRankingChange } from '../api/types'
import { runHomeClock, runHomeSeasonLabel } from './RunHomeProgress'
import type { HomeClock } from './RunHomeProgress'

type Props = { data: RunHomeRankingChanges; locale: 'cs' | 'en'; runId?: string; identities?: Record<string, SavedHomePlayerIdentity>; clock?: HomeClock | null }

function weekText(ordinal: number, clock: HomeClock | null): string {
  if (!clock || !Number.isSafeInteger(ordinal) || ordinal < 0 ||
    !Number.isSafeInteger(clock.weeks_per_year * clock.season_count) ||
    ordinal >= clock.weeks_per_year * clock.season_count) return '—'
  return runHomeSeasonLabel(clock, Math.floor(ordinal / clock.weeks_per_year))
    + ' · W' + (ordinal % clock.weeks_per_year + 1)
}

function movementText(change: RunHomeRankingChange, locale: 'cs' | 'en'): string {
  const before = change.previous_rank
  const after = change.current_rank
  if (change.movement === 'entered') return locale === 'cs' ? 'Nově v pořadí' : 'Newly ranked'
  if (change.movement === 'exited') return locale === 'cs' ? 'Opustil pořadí' : 'Exited ranking'
  if (change.movement === 'points_only') return locale === 'cs' ? 'Stejná pozice' : 'Unchanged position'
  return '#' + before + ' → #' + after + ' (' + (change.rank_delta! > 0 ? '+' : '') + change.rank_delta + ')'
}

export function RunHomeRankingPanel(props:Props):JSX.Element {
  const d=props.data
  return <RankingReview key={JSON.stringify([d.run_id,d.branch_id,d.saved_revision_id,d.previous_week_ordinal,d.current_week_ordinal])} {...props}/>
}

function RankingReview({
  data, locale, runId = data.run_id, identities = {}, clock = runHomeClock({})
}: Props): JSX.Element {
  const cs = locale === 'cs'
  const [filter,setFilter]=useState<'all'|RunHomeRankingChange['movement']>('all')
  const options=[{value:'all',label:cs?'Všechny záznamy':'All records'},
    {value:'up',label:cs?'Vzestup':'Moved up'},{value:'down',label:cs?'Pokles':'Moved down'},
    {value:'entered',label:cs?'Nově zařazení':'Entered'},{value:'exited',label:cs?'Vyřazení':'Exited'},
    {value:'points_only',label:cs?'Pouze body':'Points only'}] as const
  const rows=data.changes.filter(change=>filter==='all'||change.movement===filter)
  const categories=[{label:cs?'Posuny v pořadí':'Rank movement',count:data.moved_count},
    {label:cs?'Nově v rankingu':'New ranking entries',count:data.entered_count},
    {label:cs?'Odchody z rankingu':'Ranking exits',count:data.exited_count},
    {label:cs?'Změny pouze bodů':'Points-only movement',count:data.points_only_count}]
  const validCounts=categories.every(c=>Number.isSafeInteger(c.count)&&c.count>=0)
    &&Number.isSafeInteger(data.total_change_count)&&data.total_change_count>0
    &&categories.reduce((n,c)=>n+c.count,0)===data.total_change_count
  return <section className="run-home-ranking" aria-label={cs ? 'Uložené týdenní změny žebříčku' : 'Saved weekly ranking changes'}>
    <h4>{cs ? 'Změny žebříčku · publikované týdny' : 'Ranking movement · published weeks'}</h4>
    {!clock && data.status !== 'unpublished' && <p role="status">{cs
      ? 'Kalendář Runu není ověřen; časové lokátory žebříčku se neodvozují.'
      : 'Run calendar is unavailable; ranking week labels are not inferred.'}</p>}
    {data.status === 'unpublished' && <p className="status">{cs
      ? 'V této branchi zatím není uložená publikace Official Rankingu.'
      : 'This Branch has no saved Official Ranking publication yet.'}</p>}
    {data.status === 'first_publication' && <p className="status">{cs
      ? 'Existuje jen první publikovaný ranking. Posun lze určit až po další týdenní publikaci.'
      : 'Only the first ranking publication exists; movement needs a second published week.'}
      {data.current_week_ordinal != null ? ' · ' + weekText(data.current_week_ordinal, clock) : ''}</p>}
    {data.status === 'ready' && <>
      <p className="status">{weekText(data.previous_week_ordinal!, clock)} → {weekText(data.current_week_ordinal!, clock)}
        {' · '}{data.moved_count} {cs ? 'změn pořadí' : 'rank moves'}
        {' · '}{data.entered_count} {cs ? 'nových' : 'entrants'}
        {' · '}{data.exited_count} {cs ? 'odchodů' : 'exits'}
        {' · '}{data.points_only_count} {cs ? 'změn bodů bez posunu' : 'points-only changes'}
      </p>
      {data.total_change_count === 0 && <p className="status">{cs
        ? 'Mezi těmito dvěma publikacemi se pořadí ani body nezměnily.'
        : 'No rank or point changes between these two saved publications.'}</p>}
      {validCounts&&<section aria-label={cs?'Rozdělení všech evidovaných změn':'All recorded changes by category'}>
        <h5>{cs?'Rozdělení změn':'Change breakdown'}</h5>
        {categories.map(category=><div key={category.label}>
          <label>{category.label}: {category.count} / {data.total_change_count}
            <meter min={0} max={data.total_change_count} value={category.count}
              aria-label={category.label}/></label>
        </div>)}
        <p className="status">{cs?'Souhrn celé dvojice publikací; seznam níže může být omezený.':
          'Summary of the complete publication pair; the list below may be limited.'}</p>
      </section>}
      {data.changes.length>0&&<div data-run-navigation-readonly>
        <label>{cs?'Filtrovat dostupné záznamy':'Filter available records'}
          <select value={filter} onChange={e=>setFilter(e.target.value as typeof filter)}>
            {options.map(option=><option key={option.value} value={option.value}>{option.label}</option>)}
          </select></label>
        <p className="status">{cs?'Odpovídající načtené záznamy':'Matching loaded records'}: {rows.length} / {data.changes.length}</p>
        {rows.length===0&&<p>{cs?'V načteném výběru nejsou odpovídající záznamy.':
          'No matching records in the loaded selection.'}</p>}
      </div>}
      {rows.length > 0 && <ul className="run-home-feed">
        {rows.map(change => <li key={change.player_id}>
          <span><strong><HomePlayerIdentityLink runId={runId} playerId={change.player_id} identity={identities[change.player_id]}/></strong>
            <small>{movementText(change, locale)}
              {change.points_delta != null && ' · ' + (change.points_delta > 0 ? '+' : '') + change.points_delta + (cs ? ' b.' : ' pts')}
            </small>
          </span>
          <span className="run-home-ranking__movement" data-movement={change.movement}>
            {change.movement === 'up' ? '↑' :
              change.movement === 'down' ? '↓' :
                change.movement === 'entered' ? '+' :
                  change.movement === 'exited' ? '−' : '•'}
          </span>
        </li>)}
      </ul>}
      {data.total_change_count > data.changes.length && <p className="status">{cs
        ? 'Zobrazeno ' + data.changes.length + ' z ' + data.total_change_count + ' změn.'
        : 'Showing ' + data.changes.length + ' of ' + data.total_change_count + ' changes.'}</p>}
    </>}
    <p className="status">{cs
      ? 'Zdroj: dvě po sobě jdoucí uložené týdenní publikace vybrané branche. Nově zařazení a vyřazení se nepočítají jako skok v pořadí.'
      : 'Source: consecutive saved weekly publications of the selected Branch. Entrants and exits are not counted as rank movement.'}</p>
  </section>
}
