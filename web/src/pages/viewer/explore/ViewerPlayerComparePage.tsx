import { useEffect, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { getRunPlayerDetail, listRunPlayers } from '../../../api/client'
import { ViewerEmptyState, ViewerLandingGrid, ViewerMetadataList, ViewerSectionCard } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useLanguage } from '../../../i18n/LanguageContext'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import {
  comparablePlayerIds, readViewerComparisonQueryParams,
  verifiedComparisonPlayerDetail
} from './viewerComparisonDisplay'
import { ViewerComparisonPlayerCard, ViewerComparisonSummary, ViewerPlayerComparisonLinks, ViewerSamplePlayersList } from './viewerComparisonRender'

type ViewerComparisonRouteKind = 'h2h' | 'compare'

const messages = {
  en: {
    title: 'Player Comparison',
    description: 'Read-only player comparison using existing active-run player fields only.',
    h2hDescription: 'Read-only player attribute comparison, not an authoritative historical H2H record.',
    noRunDescription: 'Read-only player comparison using the active Viewer run.',
    noRun: 'No data is available for this run yet.',
    activeRun: 'Active Viewer run', runId: 'Active run ID',
    sampleLoading: 'Loading active run player metadata…',
    sampleError: 'Player discovery sample is temporarily unavailable.',
    total: 'Total player count', sampleSize: 'Discovery sample size', loadingValue: 'Loading…',
    emptySample: 'No discovery sample is available for this run yet.',
    sampleLabel: 'Sample active run players for comparison links',
    playerA: 'Player A', playerB: 'Player B',

    inputTitle: 'Choose two players by exact ID',
    inputHelp: 'Use the original player IDs from the active Run. This compares stored player attributes, not match history or predicted odds.',
    first: 'First player ID', second: 'Second player ID', compare: 'Compare players',
    clear: 'Clear comparison', same: 'Choose two different, nonempty player IDs.',
    loading: 'Loading exact player details…', error: 'One or both player details could not be retrieved.',
    mismatch: 'The server returned incomplete or mismatched player identity data. No comparison is shown.',
    incomplete: 'Select both player IDs to compare their attributes.',
    pending: 'Apply the changed player IDs to load a new comparison.',
    scope: 'These are active-Run player fields, not a historical Saved Branch H2H result.'
  },
  cs: {
    title: 'Porovnání hráčů',
    description: 'Čtecí porovnání hráčů pouze podle existujících atributů aktivního Runu.',
    h2hDescription: 'Čtecí porovnání atributů hráčů, nikoliv autoritativní historie vzájemných zápasů.',
    noRunDescription: 'Čtecí porovnání hráčů z aktivního Viewer Runu.',
    noRun: 'Pro tento Run zatím nejsou dostupná data.',
    activeRun: 'Aktivní Viewer Run', runId: 'ID aktivního Runu',
    sampleLoading: 'Načítám údaje hráčů aktivního Runu…',
    sampleError: 'Ukázkový výběr hráčů je dočasně nedostupný.',
    total: 'Celkový počet hráčů', sampleSize: 'Velikost ukázkového výběru', loadingValue: 'Načítání…',
    emptySample: 'Pro tento Run zatím není dostupný ukázkový výběr hráčů.',
    sampleLabel: 'Ukázkový výběr hráčů aktivního Runu pro odkazy porovnání',
    playerA: 'Hráč A', playerB: 'Hráč B',

    inputTitle: 'Vybrat dva hráče podle přesného ID',
    inputHelp: 'Zadej původní ID hráčů z aktivního Runu. Porovnáváme uložené atributy, nikoliv historii vzájemných zápasů nebo kurzy.',
    first: 'ID prvního hráče', second: 'ID druhého hráče', compare: 'Porovnat hráče',
    clear: 'Vymazat porovnání', same: 'Vyber dvě různá neprázdná ID hráčů.',
    loading: 'Načítám přesné detaily hráčů…', error: 'Detail jednoho nebo obou hráčů není dostupný.',
    mismatch: 'Server vrátil neúplné údaje nebo nesprávnou identitu hráče. Porovnání se nezobrazuje.',
    incomplete: 'Pro porovnání atributů vyber oba hráče.',
    pending: 'Pro nové porovnání potvrď změněná ID hráčů.',
    scope: 'Jde o atributy aktivního Runu, nikoliv o historické vzájemné zápasy ze Saved Branch.'
  }
}

function ViewerPlayerComparisonContent({ routeKind }: { routeKind: ViewerComparisonRouteKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const { language } = useLanguage()
  const l = messages[language]
  const [searchParams, setSearchParams] = useSearchParams()
  const params = readViewerComparisonQueryParams(searchParams)
  const [draftA, setDraftA] = useState(params.playerAParam)
  const [draftB, setDraftB] = useState(params.playerBParam)
  useEffect(() => { setDraftA(params.playerAParam) }, [params.playerAParam])
  useEffect(() => { setDraftB(params.playerBParam) }, [params.playerBParam])

  const requestedValid = comparablePlayerIds(params.playerAParam, params.playerBParam)
  const selectionSynced = draftA === params.playerAParam && draftB === params.playerBParam
  const enabled = Boolean(activeRunId && requestedValid)
  // Source IDs are in the query key: no stale detail from a former Run or ID
  // can be shown while a new exact lookup is resolving.
  const left = useQuery({
    queryKey: ['viewer-comparison-exact-player', activeRunId, params.playerAParam],
    queryFn: () => getRunPlayerDetail(activeRunId!, params.playerAParam),
    enabled, retry: false
  })
  const right = useQuery({
    queryKey: ['viewer-comparison-exact-player', activeRunId, params.playerBParam],
    queryFn: () => getRunPlayerDetail(activeRunId!, params.playerBParam),
    enabled, retry: false
  })
  // The first 50 are only a *discovery sample*, never proof that a URL-selected
  // ID does not exist. Arbitrary player IDs are resolved with exact GETs above.
  const playersQuery = useQuery({
    queryKey: ['viewer-player-comparison-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId), retry: false
  })

  const playerA = enabled && selectionSynced && left.isSuccess
    ? verifiedComparisonPlayerDetail(left.data, params.playerAParam) : null
  const playerB = enabled && selectionSynced && right.isSuccess
    ? verifiedComparisonPlayerDetail(right.data, params.playerBParam) : null
  const invalidEvidence = enabled && selectionSynced &&
    ((left.isSuccess && !playerA) || (right.isSuccess && !playerB))
  const detailError = enabled && selectionSynced && (left.isError || right.isError)
  const detailLoading = enabled && selectionSynced && (left.isPending || right.isPending)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const first = draftA.trim(), second = draftB.trim()
    if (!comparablePlayerIds(first, second)) return
    setSearchParams(previous => {
      const next = new URLSearchParams(previous)
      for (const key of ['playerA', 'playerB', 'player_a', 'player_b', 'a', 'b']) next.delete(key)
      next.set('playerA', first)
      next.set('playerB', second)
      return next
    })
  }
  const clear = () => {
    setDraftA('')
    setDraftB('')
    setSearchParams(previous => {
      const next = new URLSearchParams(previous)
      for (const key of ['playerA', 'playerB', 'player_a', 'player_b', 'a', 'b']) next.delete(key)
      return next
    })
  }

  if (!activeRunId) {
    return <ViewerShellPage title={l.title} description={l.noRunDescription}>
      <ViewerEmptyState>{l.noRun}</ViewerEmptyState>
    </ViewerShellPage>
  }
  const players = playersQuery.data?.players ?? []
  return (
    <ViewerShellPage
      title={l.title}
      description={routeKind === 'h2h'
        ? l.h2hDescription
        : l.description}
    >
      <ViewerLandingGrid>
        <ViewerSectionCard title={l.inputTitle} kicker={l.activeRun} variant="hero">
          <p className="status">{l.inputHelp}</p>
          <form onSubmit={submit} className="viewer-comparison-select">
            <label htmlFor="viewer-comparison-a">{l.first}</label>
            <input id="viewer-comparison-a" value={draftA} maxLength={256}
              onChange={event => setDraftA(event.target.value)} />
            <label htmlFor="viewer-comparison-b">{l.second}</label>
            <input id="viewer-comparison-b" value={draftB} maxLength={256}
              onChange={event => setDraftB(event.target.value)} />
            <div className="actions">
              <button type="submit"
                disabled={!comparablePlayerIds(draftA.trim(), draftB.trim())}>{l.compare}</button>
              <button type="button" onClick={clear}
                disabled={!params.hasPlayerParams && !draftA && !draftB}>{l.clear}</button>
            </div>
          </form>
          <p className="status">{l.scope}</p>
          {playersQuery.isLoading ? <p className="status">{l.sampleLoading}</p> : null}
          {playersQuery.isError ? <ViewerEmptyState>{l.sampleError}</ViewerEmptyState> : null}
          <ViewerMetadataList items={[
            {label: l.runId, value: activeRunId},
            {label: l.total, value: playersQuery.isLoading ? l.loadingValue : playersQuery.data?.total ?? '—'},
            {label: l.sampleSize, value: playersQuery.isLoading ? l.loadingValue : players.length}
          ]} />
          {!playersQuery.isLoading && !playersQuery.isError && players.length === 0
            ? <ViewerEmptyState>{l.emptySample}</ViewerEmptyState> : null}
          {!selectionSynced ? <p role="status">{l.pending}</p> : null}
          {params.hasPlayerParams && !requestedValid && selectionSynced
            ? <p role="alert">{l.same}</p> : null}
          {params.hasPlayerParams && requestedValid && detailLoading
            ? <p role="status">{l.loading}</p> : null}
          {detailError ? <p role="alert">{l.error}</p> : null}
          {invalidEvidence ? <p role="alert">{l.mismatch}</p> : null}
          {!params.hasPlayerParams && selectionSynced ? (
            <>
              <ViewerEmptyState>{l.incomplete}</ViewerEmptyState>
              <ViewerSamplePlayersList players={players} label={l.sampleLabel} runId={activeRunId} />
            </>
          ) : null}
        </ViewerSectionCard>
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title={l.playerA} player={playerA} />
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title={l.playerB} player={playerB} />
        <ViewerComparisonSummary playerA={playerA} playerB={playerB} />
        <ViewerPlayerComparisonLinks activeRunId={activeRunId} players={[playerA, playerB].filter((p): p is NonNullable<typeof p> => p !== null)} />
      </ViewerLandingGrid>
    </ViewerShellPage>
  )
}

export function ViewerPlayerComparisonPage(): JSX.Element {
  return <ViewerPlayerComparisonContent routeKind="compare" />
}
export function ViewerPlayerComparePage(): JSX.Element {
  return <ViewerPlayerComparisonPage />
}
export function ViewerH2HPage(): JSX.Element {
  return <ViewerPlayerComparisonContent routeKind="h2h" />
}
