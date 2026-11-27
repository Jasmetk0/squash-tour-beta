import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { getViewerVisibleProspects } from '../../../api/client'
import { ViewerEmptyState, ViewerMetadataList, ViewerStatusMessage } from '../../../components/viewer/ViewerLandingComponents'
import { useLanguage, type Language } from '../../../i18n/LanguageContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useViewerOfficialRunContext } from '../../../viewer/useViewerOfficialRunContext'
import { playerViewerBranch } from './viewerPlayerDirectory'
import { verifiedVisibleProspects } from './viewerVisibleProspects'

const PAGE_SIZE = 50

const copy = {
  title: ['Mladé talenty / Next Gen', 'Prospects / Next Gen'],
  description: [
    'Zobrazeni jsou hráči zpřístupnění v uloženém světě, kteří dosud nevstoupili na Tour. Zpřístupnění běžného ročníku nastává při dosažení 15 let, nikoli při narození. Budoucí předgenerované ročníky zůstávají neveřejné.',
    'Only players made visible in the Saved world who have not entered the Tour are listed. Regular intake becomes visible at age 15, not at birth. Future pregenerated cohorts remain private.',
  ],
  noRun: ['Nejprve vyber Product Run.', 'Select a Product Run first.'],
  resolving: ['Ověřuji uloženou Viewer Branch…', 'Verifying the Saved Viewer Branch…'],
  contextError: ['Viewer Branch pro tento Product Run nelze ověřit.', 'Viewer Branch cannot be verified for this Product Run.'],
  loading: ['Načítám veřejně viditelné talenty…', 'Loading visible pre-Tour prospects…'],
  readError: ['Seznam talentů momentálně není dostupný.', 'Prospect list is temporarily unavailable.'],
  sourceError: [
    'Seznam talentů má neplatný veřejný zdroj, budoucí data nebo nesouhlasí Run či Viewer Branch. Data se nezobrazují.',
    'Prospects have an invalid public source, future data or a Run/Viewer Branch mismatch. No entries are displayed.',
  ],
  retry: ['Načíst znovu (GET)', 'Retry read (GET)'],
  refresh: ['Obnovit uložená data', 'Refresh Saved data'],
  lifecycle: ['Stav kariéry na této stránce', 'Career status on this page'],
  all: ['Všechny stavy', 'All statuses'],
  active: ['Aktivní', 'Active'],
  retiredFilter: ['Po kariéře', 'Retired'],
  summary: ['Historicky viditelné talenty', 'Historically visible prospects'],
  run: ['Product Run', 'Product Run'],
  branch: ['Viewer Branch', 'Viewer Branch'],
  week: ['Aktuální uložený týden', 'Current Saved week'],
  count: ['Viditelné talenty mimo Tour', 'Visible pre-Tour prospects'],
  range: ['Zobrazený rozsah', 'Displayed range'],
  of: ['z', 'of'],
  list: ['Seznam viditelných talentů', 'Visible prospects'],
  empty: ['V tomto uloženém týdnu nejsou viditelní žádní hráči před vstupem na Tour.', 'No pre-Tour prospects are visible in this Saved week.'],
  emptyPage: ['Tato stránka už neobsahuje žádné hráče.', 'This page contains no remaining players.'],
  firstPage: ['Přejít na první stránku', 'Go to first page'],
  age: ['věk', 'age'],
  since: ['viditelný od', 'visible since'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  pagination: ['Stránkování talentů', 'Prospect pagination'],
  page: ['Stránka', 'Page'],
  go: ['Přejít', 'Go'],
  invalidPage: ['Vyber číslo dostupné stránky.', 'Choose an available page number.'],
  filter: ['Hledat na této stránce', 'Search this page'],
  filterScope: ['Filtr prohledává jen právě načtených nejvýše 50 hráčů, nikoli celý Run.', 'The filter searches only the currently loaded page of up to 50 players, not the entire Run.'],
  noFiltered: ['Na této stránce nejsou odpovídající talenti.', 'No matching prospects on this page.'],
  filteredCount: ['Odpovídající hráči na stránce', 'Matching players on this page'],
  clearFilter: ['Vymazat hledání', 'Clear search'],
  preTour: ['Před vstupem na Tour', 'Pre-Tour'],
  retired: ['Ukončená kariéra bez vstupu na Tour', 'Retired without entering the Tour'],
  playerId: ['ID hráče', 'Player ID'],
  birthYear: ['Rok narození', 'Birth year'],
  scope: [
    'Zpřístupnění ve světě není narození ani vstup na Tour. Seznam může obsahovat také již ukončené pre-Tour kariéry. Nevyjadřuje skrytý potenciál ani budoucí kariéru hráče.',
    'Visibility in the world is neither birth nor Tour entry. The list may also include retired pre-Tour careers. It does not disclose hidden potential or predict future careers.',
  ],
} as const

type Copy = Record<keyof typeof copy, string>
function copyFor(language: Language): Copy {
  const index = language === 'cs' ? 0 : 1
  return Object.fromEntries(
    Object.entries(copy).map(([key, translations]) => [key, translations[index]]),
  ) as Copy
}

// This legacy public lifecycle read uses season-index years starting at 2000
// and 61 weeks; it does not claim a native W52/W80 Saved adapter.
function weekLabel(seasonIndex: number, week: number): string {
  const start = 2000 + seasonIndex
  return start + '/' + String((start + 1) % 100).padStart(2, '0') + ' · W' + week
}

function readProspectPage(params: URLSearchParams): number {
  const values = params.getAll('prospectPage')
  if (values.length !== 1 || !/^[1-9]\d*$/.test(values[0])) return 1
  const page = Number(values[0])
  return Number.isSafeInteger(page) && page <= Math.floor(Number.MAX_SAFE_INTEGER / PAGE_SIZE) ? page : 1
}

function PageJump({ page, totalPages, onPage, t }: {
  page: number; totalPages: number; onPage: (page: number) => void; t: Copy
}): JSX.Element {
  const [value, setValue] = useState(String(page))
  const [invalid, setInvalid] = useState(false)
  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const next = Number(value)
    if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(next) || next > totalPages) {
      setInvalid(true)
      return
    }
    setInvalid(false)
    onPage(next)
  }
  return <form onSubmit={submit} aria-label={t.pagination + ' – ' + t.go}>
    <label htmlFor="viewer-prospect-page">{t.page} (1–{totalPages})</label>
    <input id="viewer-prospect-page" type="text" inputMode="numeric" value={value}
      aria-invalid={invalid} onChange={event => { setValue(event.target.value); setInvalid(false) }} />
    <button type="submit">{t.go}</button>
    {invalid ? <p role="alert">{t.invalidPage}</p> : null}
  </form>
}

function foldSearch(value: string): string {
  return value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
}

function ProspectsForBranch({ runId, branchId, t, ignoreUrlPage }: {
  runId: string; branchId: string; t: Copy; ignoreUrlPage: boolean
}): JSX.Element {
  const [params, setParams] = useSearchParams()
  const currentPage = ignoreUrlPage ? 1 : readProspectPage(params)
  const offset = (currentPage - 1) * PAGE_SIZE
  type LifecycleFilter = 'all' | 'active' | 'retired'
  const [pageFilter, setPageFilter] = useState<{ page: number; text: string; lifecycle: LifecycleFilter }>(
    { page: currentPage, text: '', lifecycle: 'all' },
  )
  const filter = pageFilter.page === currentPage ? pageFilter.text : ''
  const lifecycle = pageFilter.page === currentPage ? pageFilter.lifecycle : 'all'
  useEffect(() => {
    setPageFilter(previous => previous.page === currentPage ? previous :
      { page: currentPage, text: '', lifecycle: 'all' })
  }, [currentPage])
  function setFilter(text: string): void {
    setPageFilter({ page: currentPage, text, lifecycle })
  }
  function setOffset(nextOffset: number): void {
    if (nextOffset === offset) return
    setParams(previous => {
      const next = new URLSearchParams(previous)
      if (nextOffset === 0) next.delete('prospectPage')
      else next.set('prospectPage', String(nextOffset / PAGE_SIZE + 1))
      return next
    })
    setPageFilter({ page: nextOffset / PAGE_SIZE + 1, text: '', lifecycle: 'all' })
  }
  const query = useQuery({
    queryKey: ['viewer-visible-pre-tour-prospects', runId, branchId, offset],
    queryFn: () => getViewerVisibleProspects(runId, { limit: PAGE_SIZE, offset }),
    retry: false,
    refetchOnWindowFocus: false,
  })

  if (query.isPending || query.isFetching)
    return <ViewerStatusMessage>{t.loading}</ViewerStatusMessage>
  if (query.isError) return <div role="alert">
    <p>{t.readError}</p>
    <button type="button" onClick={() => void query.refetch()}>{t.retry}</button>
    {offset > 0 ? <button type="button" onClick={() => setOffset(0)}>{t.firstPage}</button> : null}
  </div>

  const data = verifiedVisibleProspects(query.data, runId, branchId, PAGE_SIZE, offset)
  if (!data) return <div role="alert">
    <p>{t.sourceError}</p>
    <button type="button" onClick={() => void query.refetch()}>{t.retry}</button>
    {offset > 0 ? <button type="button" onClick={() => setOffset(0)}>{t.firstPage}</button> : null}
  </div>

  const totalPages = Math.max(1, Math.ceil(data.total / PAGE_SIZE))
  const needle = foldSearch(filter.trim())
  const visible = data.prospects.filter(prospect =>
    (lifecycle === 'all' || prospect.lifecycle_status === lifecycle) &&
    (!needle || [prospect.player_id, prospect.display_name, prospect.short_name, prospect.country_code, prospect.country_name]
      .some(value => value !== null && foldSearch(value).includes(needle))))
  const start = data.prospects.length ? data.offset + 1 : 0
  const end = data.prospects.length ? data.offset + data.prospects.length : 0
  return <>
    <article className="viewer-active-run-card viewer-active-run-card--summary" aria-label={t.summary}>
      <h3>{t.summary}</h3>
      <ViewerMetadataList items={[
        { label: t.run, value: data.run_id },
        { label: t.branch, value: data.branch_id },
        { label: t.week, value: weekLabel(data.week.season_index, data.week.week) },
        { label: t.count, value: data.total },
        { label: t.range, value: data.total === 0 ? '0' : start + '–' + end + ' ' + t.of + ' ' + data.total },
      ]} />
      <button type="button" onClick={() => void query.refetch()}>{t.refresh}</button>
    </article>

    {data.total === 0 && data.offset === 0 ? <ViewerEmptyState>{t.empty}</ViewerEmptyState> : (
      <div className="viewer-sample-list-block">
        <h3>{t.list}</h3>
        {data.prospects.length ? <>
          <label htmlFor="viewer-prospect-filter">{t.filter}</label>
          <input id="viewer-prospect-filter" type="search" value={filter}
            onChange={event => setFilter(event.target.value)} />
          <label htmlFor="viewer-prospect-lifecycle">{t.lifecycle}</label>
          <select id="viewer-prospect-lifecycle" value={lifecycle}
            onChange={event => {
              const value = event.target.value
              if (value === 'all' || value === 'active' || value === 'retired')
                setPageFilter({ page: currentPage, text: filter, lifecycle: value })
            }}>
            <option value="all">{t.all}</option>
            <option value="active">{t.active}</option>
            <option value="retired">{t.retiredFilter}</option>
          </select>
          <button type="button" disabled={!filter && lifecycle === 'all'}
            onClick={() => setPageFilter({ page: currentPage, text: '', lifecycle: 'all' })}>{t.clearFilter}</button>
          <p className="status">{t.filterScope}</p>
          <p role="status">{t.filteredCount}: {visible.length} / {data.prospects.length}</p>
          {visible.length ? <ul className="viewer-home-list viewer-sample-list" aria-label={t.list}>
          {visible.map(prospect => <li key={prospect.player_id}>
            <strong>{prospect.display_name}</strong>
            {' · '}{prospect.country_code}{prospect.country_name ? ' · ' + prospect.country_name : ''}
            {' · '}{t.age} {prospect.age}
            {' · '}{prospect.lifecycle_status === 'retired' ? t.retired : t.preTour}{' · '}{t.since} {' '}
            {weekLabel(prospect.visible_since_week.season_index, prospect.visible_since_week.week)}
            <div>{t.playerId}: {prospect.player_id}{' · '}{t.birthYear}: {prospect.birth_year}</div>
          </li>)}
        </ul> : <ViewerEmptyState>{t.noFiltered}</ViewerEmptyState>}
        </> : <ViewerEmptyState>{t.emptyPage}</ViewerEmptyState>}
        <nav className="viewer-active-run-actions" aria-label={t.pagination}>
          {data.offset > 0 && data.prospects.length === 0 ? <>
            <button type="button" onClick={() => setOffset(0)}>{t.firstPage}</button>{' '}
          </> : null}
          <button type="button" disabled={data.offset === 0} onClick={() =>
            setOffset(Math.max(0, data.offset - PAGE_SIZE))}>{t.previous}</button>{' '}
          <button type="button" disabled={data.offset + data.prospects.length >= data.total}
            onClick={() => setOffset(data.offset + PAGE_SIZE)}>{t.next}</button>
        </nav>
        {totalPages > 1 ? <PageJump key={String(currentPage) + ':' + totalPages}
          page={currentPage} totalPages={totalPages} onPage={page => setOffset((page - 1) * PAGE_SIZE)} t={t} /> : null}
        <ViewerStatusMessage>{t.scope}</ViewerStatusMessage>
      </div>
    )}
  </>
}

export function ViewerNextGenPlayersPage(): JSX.Element {
  const runId = useActiveViewerProductRunId()?.trim() ?? ''
  const { language } = useLanguage()
  const t = copyFor(language)
  const context = useViewerOfficialRunContext(runId)
  const branchId = playerViewerBranch(context.data, runId)
  const verifiedContext = Boolean(runId && branchId && !context.isPending &&
    !context.isFetching && !context.isError)
  const [params, setParams] = useSearchParams()
  const sourceKey = verifiedContext ? JSON.stringify([runId, branchId]) : null
  const priorSource = useRef<string | null>(null)
  const sourceChanged = Boolean(sourceKey && priorSource.current && sourceKey !== priorSource.current)
  useEffect(() => {
    if (!sourceKey) return
    if (sourceChanged && params.has('prospectPage')) {
      const next = new URLSearchParams(params)
      next.delete('prospectPage')
      setParams(next, { replace: true })
    }
    priorSource.current = sourceKey
  }, [sourceKey, sourceChanged, params, setParams])

  return <section className="panel viewer-shell-page">
    <div className="page-intro">
      <h2>{t.title}</h2>
      <p className="subtitle">{t.description}</p>
    </div>
    {!runId ? <ViewerEmptyState>{t.noRun}</ViewerEmptyState> :
      context.isPending || context.isFetching ? <p className="status" role="status">{t.resolving}</p> :
      !verifiedContext ? <div role="alert">
        <p>{t.contextError}</p>
        <button type="button" onClick={() => void context.refetch()}>{t.retry}</button>
      </div> : <ProspectsForBranch key={JSON.stringify([runId, branchId])}
        runId={runId} branchId={branchId ?? ''} t={t} ignoreUrlPage={sourceChanged} />
    }
  </section>
}
