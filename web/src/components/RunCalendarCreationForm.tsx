import { useEffect, useRef, useState } from 'react'
import { previewRunCalendarCreation } from '../api/client'
import type { RunCalendarCreationInput, RunCalendarCreationPreview } from '../api/runCalendarCreation'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

export type ReviewedCreationCalendar = { input: RunCalendarCreationInput; preview: RunCalendarCreationPreview }

const copy = {
  cs: {
    title: 'Kalendář nového Runu', preset: 'Předvolba kalendáře', custom: 'Vlastní',
    weeks: 'Týdnů v roce i sezoně', offset: 'Season Week 1 odpovídá Year Week', year: 'Počáteční rok',
    horizon: 'Konec zadat pomocí', countMode: 'Počtu sezon', lastMode: 'Poslední sezony',
    count: 'Počet sezon', last: 'Rok začátku poslední sezony', preview: 'Prověřit kalendář', pending: 'Prověřuji…',
    first: 'První sezona', final: 'Poslední sezona', calendarYear: 'rok', week: 'týden',
    note: 'Předvolba mění pouze kalendář. Země, hráče a balíčky přidáš samostatně.',
    limit: 'Tento kalendář lze uložit a používat pro plánování. Sportovní simulace pro něj zatím není dostupná.',
    supported: 'Kalendář podporuje současná simulace. Sportovní obsah přidáš až po vytvoření Runu.',
    reviewNote: 'Změna nastavení vyžaduje nový náhled. Prohlídka nic nevytváří.'
  },
  en: {
    title: 'New Run calendar', preset: 'Calendar preset', custom: 'Custom',
    weeks: 'Weeks per year and season', offset: 'Season Week 1 equals Year Week', year: 'Start year',
    horizon: 'Specify the end using', countMode: 'Season count', lastMode: 'Last season',
    count: 'Number of seasons', last: 'Starting year of last season', preview: 'Review calendar', pending: 'Reviewing…',
    first: 'First season', final: 'Last season', calendarYear: 'year', week: 'week',
    note: 'The preset changes only the calendar. Countries, players and packages are added separately.',
    limit: 'This calendar can be saved and used for planning. Sporting simulation is not available for it yet.',
    supported: 'The current simulation supports this calendar. Add sporting content after creating the Run.',
    reviewNote: 'Changing settings requires a new preview. Inspection creates nothing.'
  }
}

const integer = (value: string): number | null => /^\d+$/.test(value) && Number.isSafeInteger(Number(value))
  && Number(value) <= 2147483647 ? Number(value) : null

export function RunCalendarCreationForm({ disabled, onReview }: {
  disabled: boolean; onReview: (review: ReviewedCreationCalendar | null) => void
}): JSX.Element {
  const { language } = useLanguage(); const t = copy[language]
  const [weeks, setWeeks] = useState('61'); const [offset, setOffset] = useState('37')
  const [year, setYear] = useState('2000'); const [count, setCount] = useState('50')
  const [last, setLast] = useState('2049'); const [mode, setMode] = useState('count')
  const [preset, setPreset] = useState('fax'); const [pending, setPending] = useState(false)
  const [review, setReview] = useState<RunCalendarCreationPreview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const generation = useRef(0); const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  function changed(): void { generation.current++; setReview(null); setError(null); onReview(null) }
  const w = integer(weeks), o = integer(offset), y = integer(year), n = integer(count), end = integer(last)
  const valid = w !== null && w > 0 && o !== null && o > 0 && o <= w && y !== null
    && n !== null && n > 0 && end !== null && end >= y && end === y + n - 1
    && Number.isSafeInteger(w * n)
  async function inspect(): Promise<void> {
    if (!valid || w === null || o === null || y === null || n === null || end === null || pending) return
    const input: RunCalendarCreationInput = {
      weeks_per_year: w, season_start_year_week: o, start_year: y,
      ...(mode === 'count' ? {season_count: n} : {last_season_start_year: end})
    }
    const version = generation.current
    setPending(true); setError(null)
    try {
      const result = await previewRunCalendarCreation(input)
      if (mounted.current && version === generation.current) { setReview(result); onReview({input, preview: result}) }
    } catch (cause) {
      if (mounted.current && version === generation.current) setError(formatApiError(cause))
    } finally { if (mounted.current) setPending(false) }
  }
  function updateYear(value: string): void {
    changed(); setYear(value)
    const start = integer(value)
    if (mode === 'count') setLast(start !== null && n !== null ? String(start + n - 1) : '')
    else setCount(start !== null && end !== null && end >= start ? String(end - start + 1) : '')
  }
  return <fieldset className="run-calendar-creation" disabled={disabled}>
    <legend>{t.title}</legend>
    <p className="status">{t.note}</p>
    <div className="form-grid">
      <label>{t.preset}<select aria-label={t.preset} value={preset} onChange={e => {
        changed(); setPreset(e.target.value)
        if (e.target.value === 'fax') { setWeeks('61'); setOffset('37') }
        if (e.target.value === 'earth') { setWeeks('52'); setOffset('1') }
      }}><option value="fax">FAX · 61</option><option value="earth">Earth · 52</option><option value="custom">{t.custom}</option></select></label>
      <label>{t.weeks}<input type="number" min="1" step="1" value={weeks} onChange={e => {changed(); setWeeks(e.target.value); setPreset('custom')}} /></label>
      <label>{t.offset}<input type="number" min="1" step="1" value={offset} onChange={e => {changed(); setOffset(e.target.value); setPreset('custom')}} /></label>
      <label>{t.year}<input type="number" min="0" step="1" value={year} onChange={e => updateYear(e.target.value)} /></label>
      <label>{t.horizon}<select aria-label={t.horizon} value={mode} onChange={e => {changed(); setMode(e.target.value)}}><option value="count">{t.countMode}</option><option value="last">{t.lastMode}</option></select></label>
      {mode === 'count' ? <label>{t.count}<input type="number" min="1" step="1" value={count} onChange={e => {
        changed(); setCount(e.target.value); const total = integer(e.target.value)
        setLast(y !== null && total !== null && total > 0 ? String(y + total - 1) : '')
      }} /></label> : <label>{t.last}<input type="number" min={y ?? 0} step="1" value={last} onChange={e => {
        changed(); setLast(e.target.value); const target = integer(e.target.value)
        setCount(y !== null && target !== null && target >= y ? String(target - y + 1) : '')
      }} /></label>}
    </div>
    <p className="status">{t.reviewNote}</p>
    <button type="button" disabled={!valid || pending || disabled} onClick={() => { void inspect() }}>{pending ? t.pending : t.preview}</button>
    {error && <p role="alert" className="error">{error}</p>}
    {review && <div role="status">
      <p>{t.first}: <strong>{review.first_week.season_label}</strong> · {t.calendarYear} {review.first_week.calendar_year}, {t.week} {review.first_week.year_week}</p>
      <p>{t.final}: <strong>{review.last_week.season_label}</strong> · {t.calendarYear} {review.last_week.calendar_year}, {t.week} {review.last_week.year_week}</p>
      <p>{review.sporting_calendar_supported ? t.supported : t.limit}</p>
    </div>}
  </fieldset>
}
