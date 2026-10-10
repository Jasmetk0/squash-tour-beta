import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  getAuthoritativeSimulationPosition,
  getBranchWorkingDraft,
  getPendingAuthoritativeFullSimulations,
  getRunContainer,
  getRunPackageState,
  listSavedRevisionHistory,
} from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { CurrentContextStrip, MetadataList, SectionCard } from '../components/RunScopedUi'
import { RunInitialWorldSetupPanel } from '../components/RunInitialWorldSetupPanel'
import { RunInitialRankingSetupPanel } from '../components/RunInitialRankingSetupPanel'
import { RunInitialRankingPublicationPanel } from '../components/RunInitialRankingPublicationPanel'
import { RunFirstTournamentPanel } from '../components/RunFirstTournamentPanel'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { RunHomeProgress } from './RunHomeProgress'
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
    unknown: 'neznámý'
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
    unknown: 'unknown'
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
  const revisionsQuery = useQuery({
    queryKey: ['run-home-revisions', runId, branchId],
    queryFn: () => listSavedRevisionHistory(runId, branchId!, { limit: 4 }),
    enabled: ready,
    retry: false
  })

  const run = containerQuery.data?.run_id === runId ? containerQuery.data : null
  const draft = draftQuery.data?.run_id === runId && draftQuery.data.branch_id === branchId ? draftQuery.data : null
  const position = positionQuery.data?.run_id === runId && positionQuery.data.branch_id === branchId ? positionQuery.data : null
  const pending = pendingQuery.data?.run_id === runId && pendingQuery.data.branch_id === branchId ? pendingQuery.data : null
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
          {emptyRun && <p>{l.initial}</p>}
          {packageQuery.isSuccess && ownedPackages === null && <p>{l.initial}</p>}
          {noConfirmedPosition && ownedPackages !== null && <p>{l.notPositioned}</p>}
          {positionQuery.isPending && <p role="status">{l.loading}</p>}
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
        ? 'Zobrazeny jsou skutečné uložené revize a checkpointy. Výsledky zápasů, změny rankingu a rekordy zatím nemají kompletní kanonický Home read model.'
        : 'Actual saved revisions and checkpoints only. Match results, ranking changes and records do not yet have a complete canonical Home read model.'}</p>
      {!ready && <p className="status">{l.missing}</p>}
      {ready && revisionsQuery.isPending && <p role="status">{l.loading}</p>}
      {ready && revisionsQuery.isError && <Unavailable message={formatApiError(revisionsQuery.error)} />}
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
