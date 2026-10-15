import { useQueryClient } from '@tanstack/react-query'
import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { createEmptyRunContainer } from '../api/client'
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
    failure: 'Run se nepodařilo vytvořit', identity: 'Server vrátil neočekávanou identitu nebo vlastnictví Runu.',
    mismatch: 'Uložený kalendář neodpovídá prověřenému zadání. Zkontroluj přehled Runů před dalším pokusem.'
  } : {
    title: 'Create Run', subtitle: 'Start a separate world and add independent package copies later.',
    section: 'New Run', name: 'Unique Run name', custom: 'Choose calendar and range',
    defaultNote: 'A new Run starts empty with its own Timeline 1, initial Saved Revision and clean Working Draft. The default FAX calendar has 61 weeks, starts in Year Week 37 of 2000 and contains 50 seasons.',
    create: 'Create isolated Run', creating: 'Creating Run…', back: 'Back to Runs',
    failure: 'Could not create Run', identity: 'The server returned an unexpected Run identity or ownership.',
    mismatch: 'The saved calendar does not match the reviewed request. Check the Run inventory before trying again.'
  }
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [custom, setCustom] = useState(false)
  const [review, setReview] = useState<ReviewedCreationCalendar | null>(null)

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault()
    const displayName = name.trim()
    if (!displayName || pending || (custom && !review)) return
    const reviewed = custom ? review : null
    setPending(true)
    setError(null)
    try {
      const created = reviewed ? await createEmptyRunContainer(displayName, reviewed.input)
        : await createEmptyRunContainer(displayName)
      if (!created.run_id || created.display_name !== displayName || created.read_only || created.storage_kind !== 'custom_local') {
        throw new Error(t.identity)
      }
      if (reviewed && !sameCreationCalendar(created.metadata_json?.run_calendar, expectedCreationCalendar(reviewed.input))) {
        throw new Error(t.mismatch)
      }
      writeLastRunId(created.run_id)
      rememberProductRun(created.run_id)
      await queryClient.invalidateQueries({ queryKey: ['canonical-run-containers'] })
      navigate(`/admin/runs/${encodeURIComponent(created.run_id)}`)
    } catch (cause) {
      setError(`${t.failure}: ${formatApiError(cause)}`)
    } finally {
      setPending(false)
    }
  }

  return <section className="panel">
    <PageIntro title={t.title} subtitle={t.subtitle} />
    <SectionCard title={t.section}>
      <form onSubmit={event => { void submit(event) }}>
        <label htmlFor="new-run-name">{t.name}</label>
        <input id="new-run-name" value={name} maxLength={256} required disabled={pending}
          autoComplete="off" onChange={event => setName(event.target.value)} />
        <label className="checkbox-label"><input type="checkbox" checked={custom} disabled={pending} onChange={event => {
          setCustom(event.target.checked); setReview(null); setError(null)
        }} />{t.custom}</label>
        {custom ? <RunCalendarCreationForm disabled={pending} onReview={setReview} />
          : <p className="status">{t.defaultNote}</p>}
        {error && <p role="alert" className="error">{error}</p>}
        <button type="submit" disabled={pending || !name.trim() || (custom && !review)}>{pending ? t.creating : t.create}</button>
        {' '}<Link to="/admin/runs">{t.back}</Link>
      </form>
    </SectionCard>
  </section>
}
