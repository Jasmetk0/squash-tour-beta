import type { RunHomeRankingChanges, RunHomeRankingChange } from '../api/types'
import { seasonLabel } from './runHomeModel'

type Props = { data: RunHomeRankingChanges; locale: 'cs' | 'en' }

function weekText(ordinal: number): string {
  return seasonLabel(Math.floor(ordinal / 61)) + ' · W' + (ordinal % 61 + 1)
}

function movementText(change: RunHomeRankingChange, locale: 'cs' | 'en'): string {
  const before = change.previous_rank
  const after = change.current_rank
  if (change.movement === 'entered') return locale === 'cs' ? 'Nově v pořadí' : 'Newly ranked'
  if (change.movement === 'exited') return locale === 'cs' ? 'Opustil pořadí' : 'Exited ranking'
  if (change.movement === 'points_only') return locale === 'cs' ? 'Stejná pozice' : 'Unchanged position'
  return '#' + before + ' → #' + after + ' (' + (change.rank_delta! > 0 ? '+' : '') + change.rank_delta + ')'
}

export function RunHomeRankingPanel({ data, locale }: Props): JSX.Element {
  const cs = locale === 'cs'
  return <section className="run-home-ranking" aria-label="Saved weekly ranking changes">
    <h4>{cs ? 'Změny žebříčku · publikované týdny' : 'Ranking movement · published weeks'}</h4>
    {data.status === 'unpublished' && <p className="status">{cs
      ? 'V této branchi zatím není uložená publikace Official Rankingu.'
      : 'This Branch has no saved Official Ranking publication yet.'}</p>}
    {data.status === 'first_publication' && <p className="status">{cs
      ? 'Existuje jen první publikovaný ranking. Posun lze určit až po další týdenní publikaci.'
      : 'Only the first ranking publication exists; movement needs a second published week.'}
      {data.current_week_ordinal != null ? ' · ' + weekText(data.current_week_ordinal) : ''}</p>}
    {data.status === 'ready' && <>
      <p className="status">{weekText(data.previous_week_ordinal!)} → {weekText(data.current_week_ordinal!)}
        {' · '}{data.moved_count} {cs ? 'změn pořadí' : 'rank moves'}
        {' · '}{data.entered_count} {cs ? 'nových' : 'entrants'}
        {' · '}{data.exited_count} {cs ? 'odchodů' : 'exits'}
        {' · '}{data.points_only_count} {cs ? 'změn bodů bez posunu' : 'points-only changes'}
      </p>
      {data.total_change_count === 0 && <p className="status">{cs
        ? 'Mezi těmito dvěma publikacemi se pořadí ani body nezměnily.'
        : 'No rank or point changes between these two saved publications.'}</p>}
      {data.changes.length > 0 && <ul className="run-home-feed">
        {data.changes.map(change => <li key={change.player_id}>
          <span><strong>{change.player_id}</strong>
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
