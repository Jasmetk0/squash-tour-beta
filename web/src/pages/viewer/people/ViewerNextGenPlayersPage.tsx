import { useState } from 'react'
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
    'Zobrazeni jsou jen hráči, kteří se podle veřejné historie už narodili, ale dosud nevstoupili na Tour. Budoucí předgenerované ročníky zůstávají neveřejné.',
    'Only players already visible since their birth week, but not yet on Tour, are listed. Future pregenerated cohorts are not public.',
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
  age: ['věk', 'age'],
  since: ['viditelný od', 'visible since'],
  previous: ['Předchozí', 'Previous'],
  next: ['Další', 'Next'],
  pagination: ['Stránkování talentů', 'Prospect pagination'],
  scope: [
    'Viditelnost od narození není vstup na Tour. Tento seznam nevypovídá o skrytém potenciálu ani budoucí kariéře hráče.',
    'Birth-week visibility is not Tour entry. This list does not disclose hidden potential or predict a player's future career.',
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

function ProspectsForBranch({ runId, branchId, t }: {
  runId: string; branchId: string; t: Copy
}): JSX.Element {
  const [offset, setOffset] = useState(0)
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
  </div>

  const data = verifiedVisibleProspects(query.data, runId, branchId, PAGE_SIZE, offset)
  if (!data) return <div role="alert">
    <p>{t.sourceError}</p>
    <button type="button" onClick={() => void query.refetch()}>{t.retry}</button>
  </div>

  const start = data.prospects.length ? data.offset + 1 : 0
  const end = data.offset + data.prospects.length
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
    </article>

    {data.total === 0 ? <ViewerEmptyState>{t.empty}</ViewerEmptyState> : (
      <div className="viewer-sample-list-block">
        <h3>{t.list}</h3>
        {data.prospects.length ? <ul className="viewer-home-list viewer-sample-list" aria-label={t.list}>
          {data.prospects.map(prospect => <li key={prospect.player_id}>
            <strong>{prospect.display_name}</strong>
            {' · '}{prospect.country_code}
            {' · '}{t.age} {prospect.age}
            {' · pre-Tour · '}{t.since} {' '}
            {weekLabel(prospect.visible_since_week.season_index, prospect.visible_since_week.week)}
          </li>)}
        </ul> : <ViewerEmptyState>{t.emptyPage}</ViewerEmptyState>}
        <nav className="viewer-active-run-actions" aria-label={t.pagination}>
          <button type="button" disabled={data.offset === 0} onClick={() =>
            setOffset(Math.max(0, data.offset - PAGE_SIZE))}>{t.previous}</button>{' '}
          <button type="button" disabled={data.offset + data.prospects.length >= data.total}
            onClick={() => setOffset(data.offset + PAGE_SIZE)}>{t.next}</button>
        </nav>
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
  const verifiedContext = Boolean(branchId && !context.isPending &&
    !context.isFetching && !context.isError)

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
        runId={runId} branchId={branchId ?? ''} t={t} />
    }
  </section>
}
