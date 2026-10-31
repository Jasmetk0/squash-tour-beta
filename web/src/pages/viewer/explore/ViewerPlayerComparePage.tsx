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
    return <ViewerShellPage title="Player Comparison" description="Read-only player comparison using the active Viewer run.">
      <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
    </ViewerShellPage>
  }
  const players = playersQuery.data?.players ?? []
  return (
    <ViewerShellPage
      title="Player Comparison"
      description={routeKind === 'h2h'
        ? 'Read-only player attribute comparison, not an authoritative historical H2H record.'
        : 'Read-only player comparison using existing active-run player fields only.'}
    >
      <ViewerLandingGrid>
        <ViewerSectionCard title={l.inputTitle} kicker="Active Viewer run" variant="hero">
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
          {playersQuery.isLoading ? <p className="status">Loading active run player metadata…</p> : null}
          {playersQuery.isError ? <ViewerEmptyState>Player discovery sample is temporarily unavailable.</ViewerEmptyState> : null}
          <ViewerMetadataList items={[
            {label: 'Active run ID', value: activeRunId},
            {label: 'Total player count', value: playersQuery.isLoading ? 'Loading…' : playersQuery.data?.total ?? '—'},
            {label: 'Discovery sample size', value: playersQuery.isLoading ? 'Loading…' : players.length}
          ]} />
          {!playersQuery.isLoading && !playersQuery.isError && players.length === 0
            ? <ViewerEmptyState>No discovery sample is available for this run yet.</ViewerEmptyState> : null}
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
              <ViewerSamplePlayersList players={players} label="Sample active run players for comparison links" runId={activeRunId} />
            </>
          ) : null}
        </ViewerSectionCard>
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player A" player={playerA} />
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player B" player={playerB} />
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
