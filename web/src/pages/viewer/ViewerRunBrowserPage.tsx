import { useEffect, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { listRunContainers } from '../../api/client'
import { ViewerRunSelector } from '../../components/ViewerRunSelector'
import { ViewerShellPage } from '../../components/viewer/ViewerShellPage'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerMetadataList } from '../../components/viewer/ViewerLandingComponents'
import { useLanguage, type Language } from '../../i18n/LanguageContext'
import {
  buildRunBrowserContextLinks,
  buildRunBrowserMetadataItems,
  buildRunBrowserPrimaryLinks,
  normalizeRunBrowserRuns
} from '../../viewer/runBrowserDisplay'
import { useActiveViewerProductRunId } from '../../viewer/useActiveViewerProductRunId'
import { filterViewerRuns, parseViewerRunPage, RUN_BROWSER_PAGE_SIZE } from './viewerRunBrowserBrowse'

const QUERY_KEY = 'runQuery'
const PAGE_KEY = 'runPage'

const messages = {
  title: ['Prohlížeč Runů', 'Run Browser'],
  kicker: ['Runy pouze pro čtení', 'Read-only Viewer runs'],
  description: ['Procházej dostupné Runy a jejich veřejné odkazy. Vyhledávání nemění aktivní Run ani uložená data.',
    'Browse available Runs and their Viewer links. Search does not change the active Run or saved data.'],
  activePanel: ['Aktivní Run', 'Active run'],
  activeId: ['Aktuální ID aktivního Viewer Runu:', 'Current active Viewer run id:'],
  noActive: ['Není vybraný žádný aktivní Viewer Run.', 'No active Viewer run selected.'],
  available: ['Dostupné Runy', 'Available runs'],
  loading: ['Načítám dostupné Runy…', 'Loading available runs…'],
  unavailable: ['Metadata Runů jsou dočasně nedostupná.', 'Run metadata is temporarily unavailable.'],
  invalidCatalog: ['Seznam Runů z API má neplatný formát. Výsledky se nezobrazují.', 'Run list has an invalid API format. No results are displayed.'],
  none: ['Zatím nejsou dostupné žádné Viewer Runy.', 'No Viewer runs are available yet.'],
  queryLabel: ['Hledat podle názvu nebo ID Runu', 'Search by Run name or ID'],
  queryPlaceholder: ['Název nebo ID Runu', 'Run name or ID'],
  search: ['Hledat', 'Search'],
  clear: ['Vymazat filtr', 'Clear filter'],
  noMatches: ['Žádný Run neodpovídá hledání.', 'No Runs match this search.'],
  invalidPage: ['Požadovaná stránka neexistuje. Vyber platnou stránku.', 'Requested page does not exist. Choose a valid page.'],
  ambiguousLink: ['Odkaz obsahuje nejednoznačné filtry. Odešli hledání nebo vymaž filtr.', 'The link has ambiguous filters. Submit the search or clear the filter.'],
  firstPage: ['První stránka', 'First page'],
  pagination: ['Stránkování Runů', 'Run pagination'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  page: ['Stránka', 'Page'],
  of: ['z', 'of'],
  showing: ['Zobrazeno', 'Showing'],
  activeBadge: ['Aktivní Viewer Run', 'Active Viewer run'],
  availableBadge: ['Dostupný Viewer Run', 'Available Viewer run'],
  selected: ['Právě vybraný pro stránky aktivního Viewer Runu.', 'Currently selected for active-run Viewer pages.'],
  entry: ['Hlavní odkazy', 'Run entry points'],
  history: ['Kontext a historie', 'Context and history'],
} as const

const fieldTranslations: Record<string, string> = {
  'Product Run ID': 'ID Product Runu',
  'Status': 'Stav',
  'Storage kind': 'Typ úložiště',
  'Read-only': 'Pouze pro čtení',
  'World ID': 'ID světa',
  'Timeline': 'Časový rozsah',
  'Official Branch ID': 'ID Viewer Branch',
  'Mapped SimulationRuns': 'Propojené SimulationRuny',
}
const linkTranslations: Record<string, string> = {
  'Season calendar': 'Sezonní kalendář',
  'Tournaments': 'Turnaje',
  'Rankings': 'Žebříčky',
  'Race': 'Race',
  'Players': 'Hráči',
  'Countries': 'Země',
  'History': 'Historie',
  'Finals': 'Finále',
}

function words(language: Language): Record<keyof typeof messages, string> {
  const index = language === 'cs' ? 0 : 1
  return Object.fromEntries(Object.entries(messages).map(([key, value]) =>
    [key, value[index]])) as Record<keyof typeof messages, string>
}

export function ViewerRunBrowserPage(): JSX.Element {
  const { language } = useLanguage()
  const t = words(language)
  const activeRunId = useActiveViewerProductRunId()
  const [params, setParams] = useSearchParams()
  const query = params.get(QUERY_KEY) ?? ''
  const ambiguousQuery = params.getAll(QUERY_KEY).length > 1
  const ambiguousPage = params.getAll(PAGE_KEY).length > 1
  const [draft, setDraft] = useState(query)
  useEffect(() => setDraft(query), [query])
  const runsQuery = useQuery({
    queryKey: ['viewer-run-selector-runs'],
    queryFn: listRunContainers,
    retry: false,
  })
  const invalidCatalog = runsQuery.isSuccess && !Array.isArray(runsQuery.data?.run_containers)
  const runs = invalidCatalog ? [] : normalizeRunBrowserRuns(runsQuery.data?.run_containers)
  const filtered = filterViewerRuns(runs, query)
  const count = Math.ceil(filtered.length / RUN_BROWSER_PAGE_SIZE)
  const page = ambiguousQuery || ambiguousPage ? null : parseViewerRunPage(params.get(PAGE_KEY), count)
  const pageRuns = page === null ? [] : filtered.slice(
    (page - 1) * RUN_BROWSER_PAGE_SIZE, page * RUN_BROWSER_PAGE_SIZE,
  )
  const ready = runsQuery.isSuccess && !runsQuery.isFetching && !invalidCatalog

  function updateUrl(nextQuery: string, nextPage: number | null): void {
    setParams(previous => {
      const next = new URLSearchParams(previous)
      if (nextQuery) next.set(QUERY_KEY, nextQuery)
      else next.delete(QUERY_KEY)
      if (nextPage !== null && nextPage > 1) next.set(PAGE_KEY, String(nextPage))
      else next.delete(PAGE_KEY)
      return next
    })
  }
  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    updateUrl(draft.trim(), null)
  }
  function clear(): void {
    setDraft('')
    updateUrl('', null)
  }

  const local = language === 'cs'
  const translateLink = (link: { label: string; to: string }) => ({
    ...link, label: local ? linkTranslations[link.label] ?? link.label : link.label,
  })

  return (
    <ViewerShellPage
      title={t.title}
      kicker={t.kicker}
      description={t.description}
    >
      <ViewerRunSelector />

      <section className="viewer-active-run-panel" aria-label={t.activePanel}>
        <span className="eyebrow">{t.activePanel}</span>
        <h3>{t.activePanel}</h3>
        {activeRunId ? (
          <p className="status">{t.activeId} <strong>{activeRunId}</strong></p>
        ) : (
          <ViewerEmptyState>{t.noActive}</ViewerEmptyState>
        )}
      </section>

      <section className="viewer-active-run-card" aria-label={t.available}>
        <span className="eyebrow">{t.title}</span>
        <h3>{t.available}</h3>
        <form className="stacked-form" onSubmit={submit} role="search" aria-label={t.queryLabel}>
          <label>{t.queryLabel}
            <input type="search" value={draft} placeholder={t.queryPlaceholder}
              onChange={event => setDraft(event.target.value)} />
          </label>
          <div className="actions">
            <button type="submit">{t.search}</button>{' '}
            <button type="button" onClick={clear} disabled={!draft && !query && !ambiguousQuery && !ambiguousPage}>{t.clear}</button>
          </div>
        </form>
        {runsQuery.isPending || runsQuery.isFetching ? <p className="status" role="status">{t.loading}</p> : null}
        {runsQuery.isError ? <ViewerEmptyState>{t.unavailable}</ViewerEmptyState> : null}
        {invalidCatalog ? <p className="error" role="alert">{t.invalidCatalog}</p> : null}
        {ready && !ambiguousQuery && !ambiguousPage && runs.length === 0 ? <ViewerEmptyState>{t.none}</ViewerEmptyState> : null}
        {ready && !ambiguousQuery && !ambiguousPage && runs.length > 0 && filtered.length === 0 ? <ViewerEmptyState>{t.noMatches}</ViewerEmptyState> : null}
        {ready && (ambiguousQuery || ambiguousPage) ? <p role="alert">{t.ambiguousLink}</p> : null}
        {ready && !ambiguousQuery && !ambiguousPage && filtered.length > 0 && page === null ? (
          <div role="alert">
            <p>{t.invalidPage}</p>
            <button type="button" onClick={() => updateUrl(query, null)}>{t.firstPage}</button>
          </div>
        ) : null}
        {ready && page !== null && pageRuns.length > 0 ? (
          <>
            <p className="status">{t.showing} {(page - 1) * RUN_BROWSER_PAGE_SIZE + 1}–{(page - 1) * RUN_BROWSER_PAGE_SIZE + pageRuns.length} {t.of} {filtered.length}</p>
            <div className="viewer-run-browser-list">
              {pageRuns.map((run, runIndex) => {
                const fields = buildRunBrowserMetadataItems(run).map(field => ({
                  ...field, label: local ? fieldTranslations[field.label] ?? field.label : field.label,
                }))
                const isActiveRun = activeRunId === run.run_id
                return (
                  <article className="viewer-active-run-card" key={`${run.run_id}:${runIndex}`} aria-label={`Run ${run.run_id}`}>
                    <span className="eyebrow">{isActiveRun ? t.activeBadge : t.availableBadge}</span>
                    <h4>{run.run_id}</h4>
                    {isActiveRun ? <p className="status">{t.selected}</p> : null}
                    <ViewerMetadataList ariaLabel={`Run ${run.run_id} metadata`} items={fields} />
                    <div className="viewer-run-browser-links" aria-label={`Run ${run.run_id} primary links`}>
                      <h5>{t.entry}</h5>
                      <ViewerActiveRunLinks layout="grid" links={buildRunBrowserPrimaryLinks(run.run_id).map(translateLink)} />
                    </div>
                    <div className="viewer-run-browser-links" aria-label={`Run ${run.run_id} context links`}>
                      <h5>{t.history}</h5>
                      <ViewerActiveRunLinks layout="grid" links={buildRunBrowserContextLinks(run.run_id).map(translateLink)} />
                    </div>
                  </article>
                )
              })}
            </div>
            {count > 1 ? (
              <nav className="viewer-active-run-actions" aria-label={t.pagination}>
                <button type="button" disabled={page === 1}
                  onClick={() => updateUrl(query, page - 1)}>{t.previous}</button>{' '}
                <span>{t.page} {page} {t.of} {count}</span>{' '}
                <button type="button" disabled={page === count}
                  onClick={() => updateUrl(query, page + 1)}>{t.next}</button>
              </nav>
            ) : null}
          </>
        ) : null}
      </section>
    </ViewerShellPage>
  )
}
