import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  getAuthoritativeSimulationPosition,
  getAuthoritativeFullSimulationHistory,
  getBranchWorkingDraft,
  getPendingAuthoritativeFullSimulations,
  getRunContainer,
  getRunPackageState,
  getRunHomeActivity,
  getRunHomeRankingChanges,
  listSavedRevisionHistory,
} from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { CurrentContextStrip, MetadataList, SectionCard } from '../components/RunScopedUi'
import { RunPackageSetupPanel } from '../components/RunPackageSetupPanel'
import { RunInitialWorldSetupPanel } from '../components/RunInitialWorldSetupPanel'
import { RunInitialRankingSetupPanel } from '../components/RunInitialRankingSetupPanel'
import { RunInitialRankingPublicationPanel } from '../components/RunInitialRankingPublicationPanel'
import { RunFirstTournamentPanel } from '../components/RunFirstTournamentPanel'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { RunHomeProgress } from './RunHomeProgress'
import { RunHomeRankingPanel } from './RunHomeRankingPanel'
import { seasonOrdinal, weekOrdinal } from './runHomeModel'

const NEXT = {
  cs: {
    subtitle: 'Přehled vybrané branche z kanonických uložených a simulačních dat.',
    present: 'Aktuální čas', past: 'Historický checkpoint',
    missing: 'Nedostupné', loading: 'Načítání…',
    initial: 'Prázdný Run je platný. Připrav zdrojové kopie, hráče a ranking, potom první turnaj.',
    next: 'Další postup', attention: 'Vyžaduje pozornost',
    activity: 'Dění ve světě', prep: 'Příprava prvního turnaje',
    noSport: 'Pro tuto branch zatím není k dispozici ověřená sportovní projekce nadcházejících událostí. Nezobrazujeme obsah legacy Runu jako aktuální stav.',
    noEvents: 'Zatím nejsou zaznamenané další události této branche.',
    noIssues: 'Načtená data nehlásí žádný aktuální blokátor. Nejde o úplnou validaci Runu.',
    noAttention: 'Nelze ověřit všechny zdroje upozornění.',
    continue: 'Otevřít Simulation', manage: 'Otevřít Run Management',
    history: 'Historie a revize', noPast: 'Historické výsledky a stavy ostatních částí zatím nejsou pro tento checkpoint projektovány. Zobrazeny jsou pouze uložené lokátory.',
    back: 'Vrátit se do současnosti', notPositioned: 'Branch zatím nemá uloženou pozici simulace.',
    draft: 'Working Draft (volba Viewer branche)', draftDirty: 'Neuložené změny',
    draftClean: 'Čistý draft', draftUnknown: 'Stav draftu nedostupný',
    otherDrafts: 'Další editační drafty nejsou tímto ukazatelem pokryté.',
    recentRevisions: 'Nedávné uložené revize', recorded: 'Uložené checkpointy',
    noHistorical: 'Vybraný checkpoint není dostupný nebo nepatří této branchi.',
    setup: 'Příprava obsahu Runu', saved: 'Uložená revize',
    waiting: 'Pozastavené/čekající plné simulace',
    inspection: 'Stav aktuálního simulačního slotu', noChanges: 'Bez přepnutí Viewer branche',
    unknown: 'neznámý',
    upcomingEvents: 'Nadcházející turnaje · uložený kalendář',
    publishedResults: 'Publikované výsledky · uložené revize',
    noCalendar: 'Zatím není uložený žádný Calendar Package.',
    noPosition: 'Kalendář existuje, ale branch zatím nemá určený týden.',
    noUpcoming: 'V uloženém kalendáři nejsou žádné další neodehrané turnaje od aktuálního týdne.',
    noResults: 'V uložené revizi zatím nejsou publikované výsledky turnajů.',
    rankingUnsupported: 'Změny žebříčku zatím nemají ověřenou projekci pro tuto branch.'
  },
  en: {
    subtitle: 'Selected Branch overview from canonical saved and simulation data.',
    present: 'Present', past: 'Historical checkpoint',
    missing: 'Unavailable', loading: 'Loading…',
    initial: 'An empty Run is valid. Copy source content, create players and ranking, then start the first tournament.',
    next: 'Next steps', attention: 'Needs attention',
    activity: 'World activity', prep: 'First tournament preparation',
    noSport: 'No verified upcoming sporting-event projection is available for this Branch yet. Legacy Run content is not substituted as current Branch data.',
    noEvents: 'No additional Branch activity has been recorded yet.',
    noIssues: 'Loaded feeds report no current blockers. This is not complete Run validation.',
    noAttention: 'Not every attention feed can be verified.',
    continue: 'Open Simulation', manage: 'Open Run Management',
    history: 'History & revisions', noPast: 'Historical results and other state have not yet been projected for this checkpoint. Only recorded locators are displayed.',
    back: 'Return to Present', notPositioned: 'This Branch has no saved simulation position yet.',
    draft: 'Working Draft (Viewer Branch selection)', draftDirty: 'Unsaved changes',
    draftClean: 'Clean draft', draftUnknown: 'Draft status unavailable',
    otherDrafts: 'This indicator does not cover other editing drafts.',
    recentRevisions: 'Recent saved revisions', recorded: 'Recorded checkpoints',
    noHistorical: 'The selected checkpoint is unavailable or belongs to another Branch.',
    setup: 'Run content preparation', saved: 'Saved revision',
    waiting: 'Pending/paused full simulations',
    inspection: 'Current simulation slot', noChanges: 'No Viewer Branch selection pending',
    unknown: 'unknown',
    upcomingEvents: 'Upcoming tournaments · saved calendar',
    publishedResults: 'Published results · saved revisions',
    noCalendar: 'No Calendar Package has been saved yet.',
    noPosition: 'The calendar exists but this Branch has no positioned week.',
    noUpcoming: 'No further unplayed tournaments from the current week are in the saved calendar.',
    noResults: 'No published tournament results are present in the saved revision.',
    rankingUnsupported: 'Ranking changes have no verified Branch-scoped projection yet.'
  }
}

function Unavailable({ message }: { message: string }): JSX.Element {
  return <p className="error" role="alert">{message}</p>
}

export function RunPage(): JSX.Element {
  const { runId = '' } = useParams()
  const { language } = useLanguage()
  const l = NEXT[language]
  const { selectedBranch, selectedBranchId, viewerBranchId, isLoading: branchLoading, error: branchError } = useAdminBranch()
  const time = useAdminTime()
  const branchId = selectedBranch?.run_id === runId ? selectedBranch.branch_id : null
  const present = time.mode === 'present'
  const ready = Boolean(runId && branchId && present && !branchLoading && !branchError)

  const containerQuery = useQuery({
    queryKey: ['run-container', runId],
    queryFn: () => getRunContainer(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['branch-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId!),
    enabled: ready,
    retry: false
  })
  const packageQuery = useQuery({
    queryKey: ['run-package-state', runId, branchId],
    queryFn: () => getRunPackageState(runId, branchId!),
    enabled: ready,
    retry: false
  })
  const positionQuery = useQuery({
    queryKey: ['authoritative-simulation-position', runId, branchId],
    queryFn: () => getAuthoritativeSimulationPosition(runId, branchId!),
    enabled: ready,
    retry: false
  })
  const pendingQuery = useQuery({
    queryKey: ['authoritative-pending-full-simulations', runId, branchId],
    queryFn: () => getPendingAuthoritativeFullSimulations(runId, branchId!),
    enabled: ready,
    retry: false
  })
  const simulationHistoryQuery = useQuery({
    queryKey: ['authoritative-full-simulation-history', runId, branchId],
    queryFn: () => getAuthoritativeFullSimulationHistory(runId, branchId!),
    enabled: ready,
    retry: false
  })
  const homeActivityQuery = useQuery({
    queryKey: ['run-home-activity', runId, branchId, selectedBranch?.saved_head_revision_id],
    queryFn: () => getRunHomeActivity(runId, branchId!),
    enabled: ready && Boolean(selectedBranch?.saved_head_revision_id),
    retry: false
  })
  const rankingChangesQuery = useQuery({
    queryKey: ['run-home-ranking-changes', runId, branchId, selectedBranch?.saved_head_revision_id],
    queryFn: () => getRunHomeRankingChanges(runId, branchId!),
    enabled: ready && Boolean(selectedBranch?.saved_head_revision_id),
    retry: false
  })
  const revisionsQuery = useQuery({
    queryKey: ['run-home-revisions', runId, branchId],
    queryFn: () => listSavedRevisionHistory(runId, branchId!, { limit: 4 }),
    enabled: ready,
    retry: false
  })

  const homeActivity = homeActivityQuery.data?.run_id === runId
    && homeActivityQuery.data.branch_id === branchId
    && homeActivityQuery.data.saved_revision_id === selectedBranch?.saved_head_revision_id
    ? homeActivityQuery.data : null
  const homeActivityMismatch = homeActivityQuery.isSuccess && !homeActivity
  const rankingChanges = rankingChangesQuery.data?.run_id === runId
    && rankingChangesQuery.data.branch_id === branchId
    && rankingChangesQuery.data.saved_revision_id === selectedBranch?.saved_head_revision_id
    ? rankingChangesQuery.data : null
  const rankingChangesMismatch = rankingChangesQuery.isSuccess && !rankingChanges
  const run = containerQuery.data?.run_id === runId ? containerQuery.data : null
  const draft = draftQuery.data?.run_id === runId && draftQuery.data.branch_id === branchId ? draftQuery.data : null
  const position = positionQuery.data?.run_id === runId && positionQuery.data.branch_id === branchId ? positionQuery.data : null
  const pending = pendingQuery.data?.run_id === runId && pendingQuery.data.branch_id === branchId ? pendingQuery.data : null
  const simulationHistory = simulationHistoryQuery.data?.run_id === runId && simulationHistoryQuery.data.branch_id === branchId
    ? simulationHistoryQuery.data.items : null
  const revisions = revisionsQuery.data?.run_id === runId && revisionsQuery.data.branch_id === branchId
    ? revisionsQuery.data.saved_revisions : null
  const ownedPackages = packageQuery.data?.state ?? null
  const emptyRun = ready && packageQuery.isSuccess && ownedPackages === null && positionQuery.isError && isApiNotFound(positionQuery.error)
  const base = '/admin/runs/' + encodeURIComponent(runId)
  const statusErrors = [
    branchError,
    time.error,
    containerQuery.error ? formatApiError(containerQuery.error) : null,
    draftQuery.error ? formatApiError(draftQuery.error) : null,
    packageQuery.error ? formatApiError(packageQuery.error) : null,
    positionQuery.error && !isApiNotFound(positionQuery.error) ? formatApiError(positionQuery.error) : null,
    pendingQuery.error && !isApiNotFound(pendingQuery.error) ? formatApiError(pendingQuery.error) : null,
    revisionsQuery.error ? formatApiError(revisionsQuery.error) : null,
    homeActivityQuery.error ? formatApiError(homeActivityQuery.error) : null,
    homeActivityMismatch ? 'Saved Home activity identity does not match selected Branch HEAD.' : null,
    rankingChangesQuery.error ? formatApiError(rankingChangesQuery.error) : null,
    rankingChangesMismatch ? 'Saved ranking changes identity does not match selected Branch HEAD.' : null,
    simulationHistoryQuery.error && !isApiNotFound(simulationHistoryQuery.error) ? formatApiError(simulationHistoryQuery.error) : null,
  ].filter((value): value is string => Boolean(value))
  const blockers = position?.transition_blockers ?? []
  const pendingCount = pending?.operations.length ?? 0
  const draftStatus = !ready || draftQuery.isPending ? l.loading
    : draftQuery.isError || !draft ? l.draftUnknown
      : draft.status === 'dirty' ? l.draftDirty + ' (' + draft.change_count + ')' : l.draftClean

  if (!present) {
    const checkpoint = time.selectedCheckpoint
    const validCheckpoint = Boolean(checkpoint && checkpoint.run_id === runId && checkpoint.branch_id === branchId)
    return <section className="panel run-home">
      <div className="page-intro"><h2>{l.past}</h2><p className="subtitle">{l.noPast}</p></div>
      <CurrentContextStrip items={[
        { label: 'Run', value: run?.display_name || runId },
        { label: 'Branch', value: selectedBranch?.display_name || branchId || l.missing },
        { label: 'Time', value: l.past }
      ]} />
      {!validCheckpoint && <Unavailable message={time.checkpointsError ?? l.noHistorical} />}
      <RunHomeProgress season={validCheckpoint ? checkpoint!.season : null} week={validCheckpoint ? checkpoint!.week : null}
        loading={time.checkpointsLoading} unavailable={!validCheckpoint} historical locale={language} />
      {validCheckpoint && <SectionCard title={l.past}><MetadataList items={[
        { label: 'Checkpoint', value: checkpoint!.checkpoint_id },
        { label: 'Sequence', value: checkpoint!.sequence },
        { label: 'Kind', value: checkpoint!.kind },
        { label: 'Event', value: checkpoint!.event_id ?? '—' },
        { label: 'Command', value: checkpoint!.command_kind }
      ]}/></SectionCard>}
      <button type="button" onClick={time.selectPresent}>{l.back}</button>
    </section>
  }

  const setupAllowed = Boolean(run && run.storage_kind === 'custom_local' && !run.read_only && selectedBranch?.run_id === runId)
  const verified = Boolean(ready && run && time.isAvailable && !time.error)
  const noConfirmedPosition = ready && positionQuery.isError && isApiNotFound(positionQuery.error)

  return <section className="panel run-home">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · ADMIN</p>
      <h2>{run?.display_name || runId}</h2>
      <p className="subtitle">{l.subtitle}</p>
    </div>
    <CurrentContextStrip items={[
      { label: 'Run', value: runId },
      { label: 'Branch', value: selectedBranch?.display_name ?? (branchLoading ? l.loading : l.missing) },
      { label: 'Time', value: l.present },
      { label: l.draft, value: draftStatus },
      { label: l.saved, value: selectedBranch?.saved_head_revision_id ? '✓' : l.missing }
    ]}/>
    <p className="status">{l.otherDrafts}</p>
    {containerQuery.isPending && <p role="status">{l.loading}</p>}
    {containerQuery.isError && <Unavailable message={formatApiError(containerQuery.error)} />}
    {branchError && <Unavailable message={branchError} />}
    {time.error && <Unavailable message={time.error} />}
    <RunHomeProgress season={time.presentSeason} week={time.presentWeek}
      loading={branchLoading || time.isLoading}
      unavailable={!verified} historical={false} locale={language}/>

    <div className="run-home-columns">
      <SectionCard title={l.next}>
        {!verified && <p className="status">{branchLoading || containerQuery.isPending || time.isLoading ? l.loading : l.missing}</p>}
        {verified && <>
          {packageQuery.isPending && <p role="status">{l.loading}</p>}
          {packageQuery.isError && <Unavailable message={formatApiError(packageQuery.error)} />}
          {packageQuery.isSuccess && ownedPackages === null && <p>{l.initial}</p>}
          {noConfirmedPosition && ownedPackages !== null && <p>{l.notPositioned}</p>}
          {positionQuery.isPending && <p role="status">{l.loading}</p>}
          {homeActivity && homeActivity.calendar_status === 'ready' && homeActivity.upcoming.length > 0 && <div>
            <h4>{l.upcomingEvents}</h4>
            <ul className="run-home-feed" aria-label="Upcoming saved tournaments">
              {homeActivity.upcoming.map(event => <li key={event.event_id}>
                <span><strong>{event.event_name}</strong><small>{event.season} · W{event.week} · {event.category}</small></span>
                <Link to={base + '/manage'}>{language === 'cs' ? 'Balíčky Runu' : 'Run packages'} →</Link>
              </li>)}
            </ul>
          </div>}
          {homeActivity && homeActivity.calendar_status === 'unpositioned' && <p className="status">{l.noPosition}</p>}
          {homeActivity && homeActivity.calendar_status === 'empty' && ownedPackages !== null && <p className="status">{l.noCalendar}</p>}
          {homeActivity && homeActivity.calendar_status === 'ready' && homeActivity.upcoming.length === 0 && <p className="status">{l.noUpcoming}</p>}
          {homeActivityQuery.isPending && ready && selectedBranch?.saved_head_revision_id && <p role="status">{l.loading}</p>}
          {homeActivityQuery.isError && <Unavailable message={formatApiError(homeActivityQuery.error)}/>}
          {homeActivityMismatch && <Unavailable message="Saved Home activity identity mismatch"/>}
          {position && <div className="run-home-status-block">
            <p><strong>{l.inspection}:</strong> {position.current_slot_kind
              ? position.current_slot_kind + (position.current_slot_id ? ' · ' + position.current_slot_id : '')
              : l.notPositioned}</p>
            {position.eligible_match_ids.length > 0 && <p>{language === 'cs' ? 'Hratelné zápasy' : 'Eligible matches'}: {position.eligible_match_ids.length}</p>}
            {position.unresolved_group_ids.length > 0 && <p>{language === 'cs' ? 'Nevyřešené skupiny' : 'Unresolved groups'}: {position.unresolved_group_ids.length}</p>}
            {position.week_ready_for_transition && <p>{language === 'cs' ? 'Týden je připravený k přechodu.' : 'Week is ready for transition.'}</p>}
          </div>}
          {positionQuery.isError && !isApiNotFound(positionQuery.error) && <Unavailable message={formatApiError(positionQuery.error)} />}
          {positionQuery.isSuccess && !position && <Unavailable message="Simulation position identity mismatch" />}
          {pending && pendingCount > 0 && <p>{l.waiting}: <strong>{pendingCount}</strong></p>}
          {pendingQuery.isPending && <p role="status">{l.loading}</p>}
          {pendingQuery.isError && !isApiNotFound(pendingQuery.error) && <Unavailable message={formatApiError(pendingQuery.error)} />}
          {positionQuery.isError && isApiNotFound(positionQuery.error) && !packageQuery.isSuccess && <p className="status">{l.noSport}</p>}
        </>}
        <div className="actions"><Link className="button-link" to={base + '/simulate'}>{l.continue} →</Link>
          <Link to={base + '/manage'}>{l.manage} →</Link></div>
      </SectionCard>
      <SectionCard title={l.attention}>
        {!ready && <p className="status">{l.missing}</p>}
        {statusErrors.map((message, i) => <Unavailable key={i} message={message}/>)}
        {ready && draftQuery.isSuccess && draft?.status === 'dirty' && <p className="error">{l.draftDirty}: {draft.change_count} · <Link to={base + '/branches'}>{l.history} →</Link></p>}
        {blockers.map((blocker, i) => <p key={i} className="error">{blocker} · <Link to={base + '/simulate'}>{l.continue} →</Link></p>)}
        {position && position.blocked_match_ids.length > 0 && <p className="error">{language === 'cs' ? 'Blokované zápasy' : 'Blocked matches'}: {position.blocked_match_ids.length} · <Link to={base + '/simulate'}>{l.continue} →</Link></p>}
        {pending && pendingCount > 0 && <p>{l.waiting}: {pendingCount} · <Link to={base + '/simulate'}>{l.continue} →</Link></p>}
        {ready && statusErrors.length === 0 && blockers.length === 0 && position?.blocked_match_ids.length === 0 && !draftQuery.isPending && draft?.status !== 'dirty' && pendingQuery.isSuccess && pendingCount === 0
          ? <p className="status">{l.noIssues}</p>
          : statusErrors.length === 0 && ready && !position && !emptyRun ? <p className="status">{l.noAttention}</p> : null}
        <Link to={base + '/diagnostics'}>{language === 'cs' ? 'Otevřít diagnostiku' : 'Open diagnostics'} →</Link>
      </SectionCard>
    </div>
    <SectionCard title={l.activity}>
      <p className="status">{language === 'cs'
        ? 'Čerpáme z uložené revize vybrané branche. Detail jednotlivých zápasů zatím není součástí této projekce.'
        : 'Reads the selected Branch Saved Revision. Individual match scores are outside this projection.'}</p>
      {homeActivity && <section className="run-home-results">
        <h4>{l.publishedResults}</h4>
        {homeActivity.result_status === 'empty' && <p className="status">{l.noResults}</p>}
        {homeActivity.result_status === 'ready' && <ul className="run-home-feed" aria-label="Published Branch tournament results">
          {homeActivity.recent_results.map(result => <li key={result.event_id}>
            <span><strong>{result.event_name}</strong><small>{result.season} · W{result.week} ·
              {language === 'cs' ? ' Vítěz' : ' Champion'}: {result.champion_player_id}</small></span>
            <Link to={base + '/simulate'}>{l.continue} →</Link>
          </li>)}
        </ul>}

      </section>}
      {rankingChanges && <RunHomeRankingPanel data={rankingChanges} locale={language}/>}
      {rankingChangesQuery.isPending && ready && selectedBranch?.saved_head_revision_id && <p role="status">{l.loading}</p>}
      {rankingChangesQuery.isError && <Unavailable message={formatApiError(rankingChangesQuery.error)}/>}
      {rankingChangesMismatch && <Unavailable message="Saved ranking changes identity mismatch"/>}
      {homeActivityQuery.isPending && ready && <p role="status">{l.loading}</p>}
      {homeActivityQuery.isError && <Unavailable message={formatApiError(homeActivityQuery.error)}/>}
      {homeActivityMismatch && <Unavailable message="Saved Home activity identity mismatch"/>}
      {!ready && <p className="status">{l.missing}</p>}
      {ready && revisionsQuery.isPending && <p role="status">{l.loading}</p>}
      {ready && revisionsQuery.isError && <Unavailable message={formatApiError(revisionsQuery.error)} />}
      {ready && simulationHistoryQuery.isPending && <p role="status">{l.loading}</p>}
      {ready && simulationHistoryQuery.isError && !isApiNotFound(simulationHistoryQuery.error) &&
        <Unavailable message={formatApiError(simulationHistoryQuery.error)} />}
      {ready && simulationHistory && simulationHistory.length > 0 && <div className="run-home-status-block">
        <h4>{language === 'cs' ? 'Poslední plná simulace' : 'Latest full simulation'}</h4>
        {(() => {
          const last = simulationHistory[simulationHistory.length - 1]
          return <p>{last.status} · {last.completed_season_count} {language === 'cs' ? 'dokončených sezón' : 'completed seasons'}
            {' · '}{last.final_completed_week_count} {language === 'cs' ? 'závěrečných týdnů' : 'final weeks'}
            {' · '}<Link to={base + '/simulate'}>{l.continue} →</Link></p>
        })()}
      </div>}
      {ready && revisions && <div className="run-home-columns">
        <div><h4>{l.recentRevisions}</h4>
          {revisions.length === 0 ? <p className="status">{l.noEvents}</p>
            : <ul className="run-home-feed">{[...revisions].reverse().slice(0, 3).map(revision =>
              <li key={revision.revision_id}><strong>{revision.kind}</strong><small>#{revision.sequence} · {revision.created_at ?? '—'}</small></li>)}</ul>}</div>
        <div><h4>{l.recorded}</h4>
          {time.checkpointsLoading && <p role="status">{l.loading}</p>}
          {time.checkpointsError && <Unavailable message={time.checkpointsError}/>}
          {!time.checkpointsLoading && !time.checkpointsError && time.checkpoints.length === 0 && <p className="status">{l.noEvents}</p>}
          <ul className="run-home-feed">{time.checkpoints.slice(0, 3).map(checkpoint =>
            <li key={checkpoint.checkpoint_id}><strong>{checkpoint.command_kind}</strong>
              <small>{checkpoint.kind} · #{checkpoint.sequence}</small></li>)}</ul>
        </div>
      </div>}
      <Link to={base + '/branches'}>{l.history} →</Link>
    </SectionCard>

    {setupAllowed && <section className="run-home-setup" aria-label="Run content preparation">
      <h3>{l.setup}</h3>
      <p className="status">{language === 'cs'
        ? 'Existující nástroje k přípravě hráčů, rankingu a prvního turnaje. Ruční Save a potvrzovací kroky se nemění.'
        : 'Existing player, ranking and first-tournament preparation. Manual Save and confirmations are unchanged.'}</p>
      <RunPackageSetupPanel run={run!} branch={selectedBranch} />
      <RunInitialWorldSetupPanel run={run!} branch={selectedBranch} />
      <RunInitialRankingSetupPanel run={run!} branch={selectedBranch} />
      <RunInitialRankingPublicationPanel run={run!} branch={selectedBranch} />
      <RunFirstTournamentPanel run={run!} branch={selectedBranch} />
    </section>}
    <p className="status">{viewerBranchId && branchId !== viewerBranchId
      ? (language === 'cs' ? 'Viewer ukazuje jinou uloženou branch. Tato stránka nemění Viewer Branch.' : 'Viewer is displaying another saved Branch. This page does not change it.')
      : ''}</p>
  </section>
}
