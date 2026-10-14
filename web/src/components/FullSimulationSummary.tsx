import { useQuery } from '@tanstack/react-query'
import { getFullSimulationSummary } from '../api/fullSimulationSummary'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

const copy = {
  en: {title:'Stored simulation summary',loading:'Loading stored summary…',
    unavailable:'No terminal summary was recorded for this operation. Its endpoint is unavailable.',
    truth:'Frozen when this operation ended. Later Branch work does not update this summary. Save remains explicit.',
    start:'Actual start',end:'Actual end',original:'Original target',target:'Effective target',reason:'Operator reason',
    stopped:'Stopped by operator',reached:'Selected week target reached',children:'Persisted child commands',
    tournaments:'Completed tournaments owned by this operation',empty:'No completed tournament source is recorded for this operation.',
    champion:'Champion',finalist:'Finalist',saved:'Saved Revision at operation end',
    missing:'Ranking changes, watched events and notifications are unavailable in this summary.'},
  cs: {title:'Uložený souhrn simulace',loading:'Načítám uložený souhrn…',
    unavailable:'Pro tuto operaci nebyl zaznamenán závěrečný souhrn. Její koncový bod není dostupný.',
    truth:'Zachyceno při ukončení této operace. Pozdější práce ve větvi tento souhrn nemění. Save zůstává výslovný.',
    start:'Skutečný začátek',end:'Skutečný konec',original:'Původní cíl',target:'Efektivní cíl',reason:'Důvod operátora',
    stopped:'Ukončeno operátorem',reached:'Dosažen vybraný týdenní cíl',children:'Uložené dílčí příkazy',
    tournaments:'Dokončené turnaje vlastněné touto operací',empty:'Pro tuto operaci není zaznamenán zdroj dokončeného turnaje.',
    champion:'Vítěz',finalist:'Finalista',saved:'Saved Revision při ukončení operace',
    missing:'Změny rankingu, sledované události a upozornění nejsou v tomto souhrnu dostupné.'}
}

export function FullSimulationSummary({runId,branchId,commandId}:{runId:string;branchId:string;commandId:string}):JSX.Element {
  const {language} = useLanguage()
  const t = copy[language]
  const query = useQuery({queryKey:['full-simulation-summary',runId,branchId,commandId],
    queryFn:()=>getFullSimulationSummary(runId,branchId,commandId),retry:false})
  const s = query.data?.summary
  const week = (v:{season_index:number;week:number}) => `S${v.season_index} W${v.week}`
  return <section aria-label={t.title}>
    <h5>{t.title}</h5>
    {query.isPending && <p role="status">{t.loading}</p>}
    {query.error && <p role="alert">{formatApiError(query.error)}</p>}
    {query.isSuccess && !s && <p>{t.unavailable}</p>}
    {s && <>
      <p className="status">{t.truth}</p>
      <p><strong>{s.target_reached ? t.reached : t.stopped}</strong></p>
      <p>{t.reason}: {s.terminal_audit_reason}</p>
      <dl>
        <dt>{t.start}</dt><dd>{week(s.start_week)}</dd>
        <dt>{t.end}</dt><dd>{week(s.end_week)}</dd>
        <dt>{t.original}</dt><dd>{week(s.original_final_week)}</dd>
        <dt>{t.target}</dt><dd>{week(s.effective_target_week)}</dd>
        <dt>{t.children}</dt><dd>{s.persisted_child_command_count}</dd>
        <dt>{t.saved}</dt><dd><code>{s.terminal_saved_revision_id}</code></dd>
      </dl>
      <h6>{t.tournaments}</h6>
      {s.completed_tournaments.length === 0 ? <p>{t.empty}</p> : <ul>
        {s.completed_tournaments.map(item=><li key={item.edition_id}>
          <code>{item.edition_id}</code>{' · '}{week(item.completed_week)}
          {' · '}{t.champion}: <code>{item.champion_player_id ?? '—'}</code>
          {' · '}{t.finalist}: <code>{item.finalist_player_id ?? '—'}</code>
        </li>)}
      </ul>}
      <p>{t.missing}</p>
    </>}
  </section>
}
