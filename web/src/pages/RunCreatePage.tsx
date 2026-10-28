import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { createEmptyRunContainer, listRunContainers } from '../api/client'
import { PageIntro, SectionCard } from '../components/RunScopedUi'
import { RunCalendarCreationForm } from '../components/RunCalendarCreationForm'
import type { ReviewedCreationCalendar } from '../components/RunCalendarCreationForm'
import { expectedCreationCalendar, sameCreationCalendar } from '../api/runCalendarCreation'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { writeLastRunId } from '../viewer/activeRun'
import { rememberProductRun } from '../navigation/recentProductRuns'

/** The canonical Run creation flow: no preselected world, seed or legacy Simulation Run. */
export function RunCreatePage(): JSX.Element {
  const { language } = useLanguage()
  const t = language === 'cs' ? {
    title: 'Vytvořit Run', subtitle: 'Vytvoř samostatný svět. Nezávislé kopie balíčků přidáš později.',
    section: 'Nový Run', name: 'Jedinečný název Runu', custom: 'Zvolit kalendář a rozsah',
    defaultNote: 'Nový Run začíná prázdný s vlastní Timeline 1, první Saved Revision a čistým Working Draftem. Výchozí FAX kalendář má 61 týdnů, začíná ve 37. týdnu roku 2000 a obsahuje 50 sezon.',
    create: 'Vytvořit samostatný Run', creating: 'Vytvářím Run…', back: 'Zpět na Runy',
    failure: 'Vytvoření Runu nebylo potvrzeno. Před opakováním zkontroluj přehled Runů', identity: 'Server vrátil neočekávanou identitu nebo vlastnictví Runu. Před dalším pokusem zkontroluj přehled Runů.',
    mismatch: 'Uložený kalendář neodpovídá prověřenému zadání. Zkontroluj přehled Runů před dalším pokusem.',
    afterCreate: 'Run byl vytvořen, ale automatické pokračování selhalo. Zkontroluj již vytvořený Run; nezakládej ho znovu.',
    openCreated: 'Otevřít již vytvořený Run',
    verifyExisting: 'Zkontrolovat uložené Runy se stejným názvem',
    verifyingExisting: 'Ověřuji aktuální seznam Runů…',
    foundExisting: 'V aktuálním seznamu existuje Run s tímto názvem. Zkontroluj jej, nevytvářej další.',
    openExisting: 'Otevřít Run se stejným názvem',
    noMatching: 'Aktuální seznam neobsahuje Run s tímto názvem. Pokud první požadavek ještě dobíhá, vyčkej na jeho dokončení; případné nové vytvoření musíš spustit sám.',
    inventoryFailure: 'Seznam Runů se nepodařilo ověřit. Nové vytvoření je nadále zablokované: '
  } : {
    title: 'Create Run', subtitle: 'Start a separate world and add independent package copies later.',
    section: 'New Run', name: 'Unique Run name', custom: 'Choose calendar and range',
    defaultNote: 'A new Run starts empty with its own Timeline 1, initial Saved Revision and clean Working Draft. The default FAX calendar has 61 weeks, starts in Year Week 37 of 2000 and contains 50 seasons.',
    create: 'Create isolated Run', creating: 'Creating Run…', back: 'Back to Runs',
    failure: 'Run creation was not confirmed. Check the Run inventory before retrying', identity: 'The server returned an unexpected Run identity or ownership. Check the Run inventory before retrying.',
    mismatch: 'The saved calendar does not match the reviewed request. Check the Run inventory before trying again.',
    afterCreate: 'The Run was created, but automatic continuation failed. Inspect the existing Run; do not create it again.',
    openCreated: 'Open the created Run',
    verifyExisting: 'Check saved Runs for this name',
    verifyingExisting: 'Checking the current Run inventory…',
    foundExisting: 'A Run with this exact name exists in the current inventory. Inspect it rather than creating another.',
    openExisting: 'Open Run with this name',
    noMatching: 'No Run with this name is in the current inventory. If the first request is still completing, let it finish; only you can start a new create.',
    inventoryFailure: 'Could not verify the Run inventory. Another create remains blocked: '
  }
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [pending, setPending] = useState(false)
  const [createdRunId, setCreatedRunId] = useState<string | null>(null)
  const [unverifiedName, setUnverifiedName] = useState<string | null>(null)
  const [foundExistingRunId, setFoundExistingRunId] = useState<string | null>(null)
  const [checkingInventory, setCheckingInventory] = useState(false)
  const [inventoryMessage, setInventoryMessage] = useState<string | null>(null)
  // React state alone cannot fence two submit events in the same render turn.
  const submissionInFlight = useRef(false)
  const inventoryCheckInFlight = useRef(false)
  const retryBlockedName = useRef<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [custom, setCustom] = useState(false)
  const [review, setReview] = useState<ReviewedCreationCalendar | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const displayName = name.trim()
    if (!displayName || createdRunId || foundExistingRunId || inventoryCheckInFlight.current
      || retryBlockedName.current === displayName || submissionInFlight.current || (custom && !review)) return
    const reviewed = custom ? review : null
    submissionInFlight.current = true
    setPending(true)
    setError(null)
    let confirmedRunId: string | null = null
    try {
      const created = reviewed ? await createEmptyRunContainer(displayName, reviewed.input)
        : await createEmptyRunContainer(displayName)
      if (typeof created.run_id !== 'string' || !created.run_id.trim()
        || created.run_id.trim() !== created.run_id
        || created.display_name !== displayName || created.read_only || created.storage_kind !== 'custom_local') {
        throw new Error(t.identity)
      }
      // The validated identity exists even if its returned calendar does not
      // match the reviewed request. Never offer a duplicate create in that case.
      confirmedRunId = created.run_id
      setCreatedRunId(created.run_id)
      if (reviewed && !sameCreationCalendar(created.metadata_json?.run_calendar, expectedCreationCalendar(reviewed.input))) {
        throw new Error(t.mismatch)
      }
      // Only the server create response is authoritative. Browser hints/cache refresh
      // must not turn a successful create into an apparent failure and a duplicate retry.
      writeLastRunId(created.run_id)
      rememberProductRun(created.run_id)
      try {
        void queryClient.invalidateQueries({ queryKey: ['canonical-run-containers'] }).catch(() => undefined)
      } catch {
        // The inventory can be refreshed separately; the created Run still exists.
      }
      navigate(`/admin/runs/${encodeURIComponent(created.run_id)}`)
    } catch (cause) {
      if (!confirmedRunId) {
        // A rejected POST may still have committed on the server. Do not allow
        // a blind repeat until the operator inspects a fresh server inventory.
        retryBlockedName.current = displayName
        setUnverifiedName(displayName)
        setInventoryMessage(null)
      }
      setError(confirmedRunId ? `${t.afterCreate} (${formatApiError(cause)})`
        : `${t.failure}: ${formatApiError(cause)}`)
    } finally {
      // Keep the synchronous fence permanently closed after confirmed creation,
      // including before React commits the recovery-link state.
      submissionInFlight.current = confirmedRunId !== null
      setPending(false)
    }
  }

  async function verifyExistingName(): Promise<void> {
    const requestedName = unverifiedName
    if (!requestedName || inventoryCheckInFlight.current || submissionInFlight.current) return
    inventoryCheckInFlight.current = true
    setCheckingInventory(true)
    setInventoryMessage(null)
    try {
      // Read the actual server inventory; browser-local history and cached
      // React Query data are never proof that an uncertain POST did not commit.
      const inventory = await listRunContainers()
      if (!Array.isArray(inventory?.run_containers) || inventory.run_containers.some(run =>
        !run || typeof run.run_id !== 'string' || !run.run_id.trim()
        || run.run_id.trim() !== run.run_id
        || (run.display_name !== null && typeof run.display_name !== 'string')
      )) throw new Error('Invalid Run inventory')
      const matches = inventory.run_containers.filter(run => run.display_name === requestedName)
      if (matches.length > 1) {
        throw new Error('Ambiguous Run inventory')
      }
      if (matches.length === 1) {
        setFoundExistingRunId(matches[0].run_id)
        setInventoryMessage(t.foundExisting)
        // The matching Run may predate this request. Never assert it was just created.
      } else {
        // A negative point-in-time read does not guarantee a still-running POST
        // will never commit. Retrying remains a separate explicit user action.
        retryBlockedName.current = null
        setUnverifiedName(null)
        setError(null)
        setInventoryMessage(t.noMatching)
      }
    } catch (cause) {
      setInventoryMessage(t.inventoryFailure + formatApiError(cause))
    } finally {
      inventoryCheckInFlight.current = false
      setCheckingInventory(false)
    }
  }

  return <section className="panel">
    <PageIntro title={t.title} subtitle={t.subtitle} />
    <SectionCard title={t.section}>
      <form onSubmit={event => { void submit(event) }}>
        <label htmlFor="new-run-name">{t.name}</label>
        <input id="new-run-name" value={name} maxLength={256} required
          disabled={pending || checkingInventory || Boolean(unverifiedName)
            || Boolean(createdRunId) || Boolean(foundExistingRunId)}
          autoComplete="off" onChange={event => {
            setName(event.target.value)
            setError(null)
            setInventoryMessage(null)
          }} />
        <label className="checkbox-label"><input type="checkbox" checked={custom} disabled={pending || checkingInventory || Boolean(createdRunId) || Boolean(foundExistingRunId)} onChange={event => {
          setCustom(event.target.checked); setReview(null); setError(null)
        }} />{t.custom}</label>
        {custom ? <RunCalendarCreationForm disabled={pending || checkingInventory || Boolean(createdRunId) || Boolean(foundExistingRunId)} onReview={setReview} />
          : <p className="status">{t.defaultNote}</p>}
        {error && <p role="alert" className="error">{error}</p>}
        {createdRunId && <p role="status"><Link to={`/admin/runs/${encodeURIComponent(createdRunId)}`}>{t.openCreated}</Link></p>}
        {unverifiedName && !foundExistingRunId && <button type="button"
          disabled={checkingInventory} onClick={() => { void verifyExistingName() }}>
          {checkingInventory ? t.verifyingExisting : t.verifyExisting}
        </button>}
        {inventoryMessage && <p role="status">{inventoryMessage}</p>}
        {foundExistingRunId && <p><Link to={`/admin/runs/${encodeURIComponent(foundExistingRunId)}`}>{t.openExisting}</Link></p>}
        <button type="submit" disabled={pending || checkingInventory || Boolean(createdRunId)
          || Boolean(foundExistingRunId) || Boolean(unverifiedName) || !name.trim() || (custom && !review)}>{pending ? t.creating : t.create}</button>
        {' '}<Link to="/admin/runs">{t.back}</Link>
      </form>
    </SectionCard>
  </section>
}
