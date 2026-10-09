import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import {
  getBranchWorkingDraft, getCanonicalTournamentPreparation, getRunOwnedCalendar, getRunPackageState
} from '../api/client'
import type { RunBranch, RunContainer } from '../api/types'
import {
  firstRunCalendarWeek, isRunCalendarProjection, runCalendarPackageIds
} from '../api/runFirstTournament'
import { formatApiError } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

export function RunFirstTournamentPanel({ run, branch }: {
  run: RunContainer; branch: RunBranch | null
}): JSX.Element {
  const runId = run.run_id
  const branchId = branch?.run_id === runId ? branch.branch_id : ''
  const head = branch?.run_id === runId ? branch.saved_head_revision_id : null
  const validBranch = Boolean(branchId && head && branch?.status === 'active' && !branch.read_only)
  const [calendarSelection, setCalendarSelection] = useState('')
  const [eventSelection, setEventSelection] = useState('')

  const packagesQuery = useQuery({
    queryKey: ['run-package-state', runId, branchId],
    queryFn: () => getRunPackageState(runId, branchId),
    enabled: validBranch,
    retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId),
    enabled: validBranch,
    retry: false
  })
  const savedCalendarScope = Boolean(validBranch &&
    draftQuery.data?.run_id === runId &&
    draftQuery.data?.branch_id === branchId &&
    draftQuery.data?.base_saved_revision_id === head &&
    draftQuery.data?.status === 'clean')
  const packageState = packagesQuery.data?.state
  const calendarIds = runCalendarPackageIds(
    packageState?.run_id === runId && packageState?.branch_id === branchId ? packageState : null
  )
  const calendarId = calendarIds.includes(calendarSelection)
    ? calendarSelection : (calendarIds.includes('calendar-2000-2001') ? 'calendar-2000-2001' : calendarIds[0] ?? '')
  const calendarQuery = useQuery({
    queryKey: ['run-calendar', runId, branchId, calendarId],
    queryFn: () => getRunOwnedCalendar(runId, branchId, calendarId),
    enabled: savedCalendarScope && Boolean(calendarId),
    retry: false
  })
  const calendar = calendarQuery.data && isRunCalendarProjection(calendarQuery.data, runId, branchId, calendarId) &&
    calendarQuery.data.run_package_state_fingerprint === packagesQuery.data?.fingerprint
    ? calendarQuery.data : null
  const firstEvents = firstRunCalendarWeek(calendar?.calendar.events ?? [])
  const eventId = firstEvents.some(event => event.event_id === eventSelection)
    ? eventSelection : (firstEvents[0]?.event_id ?? '')
  const preparationQuery = useQuery({
    queryKey: ['canonical-tournament-preparation', runId, branchId, eventId],
    queryFn: () => getCanonicalTournamentPreparation(runId, branchId, eventId),
    enabled: savedCalendarScope && Boolean(calendar && eventId),
    retry: false
  })
  const preparation = preparationQuery.data?.run_id === runId &&
    preparationQuery.data?.branch_id === branchId &&
    preparationQuery.data?.event_id === eventId &&
    preparationQuery.data?.schema_version === 'canonical_tournament_preparation_state.v1' &&
    preparationQuery.data?.authority_source === 'run_owned_db_authorities.v1'
    ? preparationQuery.data : null

  return <SectionCard title="First tournament — canonical Run Calendar">
    <p className="status">Discover the earliest scheduled event from the saved Run-owned Calendar, not a legacy Simulation Run. The tournament readiness comes from real Run/Branch database authorities; no applications, Draw or results are auto-generated.</p>
    {!validBranch && <p role="status">Select a writable Active Admin Branch with a Saved Revision.</p>}
    {packagesQuery.error && <p role="alert" className="error">Run Package snapshot unavailable: {formatApiError(packagesQuery.error)}</p>}
    {draftQuery.error && <p role="alert" className="error">Working Draft unavailable: {formatApiError(draftQuery.error)}</p>}
    {validBranch && draftQuery.isSuccess && !savedCalendarScope && <p role="status">Save the current Working Draft before preparing a tournament from its Calendar Package.</p>}
    {calendarIds.length === 0 && packagesQuery.isSuccess && <p>No Calendar Package is applied. Review and save the 2000/01 Calendar source above first.</p>}
    {calendarIds.length > 1 && <label>Run Calendar Package{' '}
      <select aria-label="First-tournament Calendar Package" value={calendarId}
        onChange={event => { setCalendarSelection(event.target.value); setEventSelection('') }}>
        {calendarIds.map(id => <option key={id} value={id}>{id}</option>)}
      </select>
    </label>}
    {calendarQuery.error && <p role="alert" className="error">Run Calendar unavailable: {formatApiError(calendarQuery.error)}</p>}
    {calendarQuery.isSuccess && !calendar && <p role="alert" className="error">Run-owned Calendar identity, season, content or Package fingerprint could not be verified.</p>}
    {calendar && <p>Season: {calendar.season} · Calendar events: {calendar.calendar.events.length} · Source: {calendar.package_id}.</p>}
    {calendar && firstEvents.length === 0 && <p>No events in the applied 2000/01 Calendar. Nothing can be prepared automatically.</p>}
    {firstEvents.length > 0 && <section aria-label="First tournament selection">
      <h4>First scheduled week: {firstEvents[0].season_week}</h4>
      <label>Event in first week{' '}
        <select aria-label="First scheduled tournament" value={eventId}
          onChange={event => setEventSelection(event.target.value)}>
          {firstEvents.map(event =>
            <option key={event.event_id} value={event.event_id}>
              {event.event_name || event.event_id} ({event.event_id})
            </option>
          )}
        </select>
      </label>
      {preparationQuery.isLoading && <p role="status">Checking actual tournament preparation…</p>}
      {preparationQuery.error && <p role="alert" className="error">Tournament readiness unavailable: {formatApiError(preparationQuery.error)}</p>}
      {preparationQuery.isSuccess && !preparation && <p role="alert" className="error">Canonical tournament preparation identity or authority could not be verified.</p>}
      {preparation && <>
        <p>Engine phase: <strong>{preparation.phase}</strong> · Next: <strong>{preparation.next_required_action}</strong>.</p>
        {preparation.blockers.length > 0 && <p>Engine blockers: {preparation.blockers.join(', ')}.</p>}
        {preparation.next_required_action === 'build_entry_field' && (preparation.valid_submission_count ?? 0) === 0 &&
          <p className="status">No verified applications yet. The existing event workflow will not invent participants; its application-validation gate still needs resolution.</p>}
        <Link to={`/admin/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(eventId)}?branch=${encodeURIComponent(branchId)}&calendar=${encodeURIComponent(calendarId)}`}>
          Open first Run-owned tournament preparation
        </Link>
      </>}
    </section>}
  </SectionCard>
}
