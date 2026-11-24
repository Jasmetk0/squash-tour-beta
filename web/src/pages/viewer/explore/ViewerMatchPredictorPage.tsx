import { useEffect, useState, type FormEvent } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { getRunPlayerDetail, listRunPlayers } from '../../../api/client'
import type { RunPlayerListItem } from '../../../api/types'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerLandingGrid, ViewerMetadataList, ViewerSectionCard } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useLanguage } from '../../../i18n/LanguageContext'
import { viewerPlayersPath, viewerTopSearchPath } from '../../../viewer/viewerRoutes'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { comparablePlayerIds, readViewerComparisonQueryParams, verifiedComparisonPlayerDetail } from './viewerComparisonDisplay'
import { buildSelectedH2HPath, ViewerComparisonPlayerCard, ViewerComparisonSummary, ViewerSamplePlayersList } from './viewerComparisonRender'

// The Match Predictor is not backed by a prediction/odds read model.
// These GETs only resolve selected players' *current legacy Run attributes*.
// A first-50 discovery sample must never decide if a deep-linked player exists.
const copy = {
  en: {
    title: 'Match Predictor',
    description: 'Read-only player input preview from the active SimulationRun; not a saved historical prediction.',
    noRun: 'No active SimulationRun is selected. Player details and predictions are unavailable.',
    inputTitle: 'Choose exact player IDs',
    active: 'Active SimulationRun',
    help: 'Enter two different player IDs. Attributes are current Run fields, not a predicted match or historical Saved H2H.',
    first: 'Player A ID', second: 'Player B ID', apply: 'Show player attributes',
    clear: 'Clear player IDs', invalid: 'Choose two different, valid player IDs.',
    pending: 'Apply the edited player IDs before loading another comparison.',
    loadingDetail: 'Loading exact player details…',
    failedDetail: 'One or both player details could not be retrieved. No comparison is shown.',
    invalidDetail: 'Exact player details do not match the requested identities or expected public fields.',
    loadingSample: 'Loading player discovery sample…',
    invalidSample: 'The active Run player discovery sample is invalid or unavailable.',
    emptySample: 'The discovery sample has no players. Exact player IDs can still be looked up.',
    choose: 'Enter two player IDs to inspect stored attributes.',
    matched: 'Exact identities verified. These attributes are not match odds or a prediction.',
    input: 'Predictor Inputs',
    firstCard: 'Player A', secondCard: 'Player B',
    summary: 'Input Comparison',
    links: 'Links',
    openPlayers: 'Open active Run players',
    openSearch: 'Open Viewer search',
    openH2H: 'Open H2H comparison',
    deferred: 'Deferred Predictor Outputs',
    deferredOne: 'There is no connected prediction read model for this Run.',
    deferredTwo: 'No match-win probability, odds or simulated result is calculated.',
    deferredThree: 'No historical Saved Branch H2H or future event is inferred from these player attributes.',
    total: 'Total players',
    sample: 'Discovery sample size',
    id: 'SimulationRun ID'
  },
  cs: {
    title: 'Prediktor zápasu',
    description: 'Čtecí náhled vstupních atributů aktivního SimulationRunu, nikoliv historická predikce.',
    noRun: 'Není vybraný aktivní SimulationRun. Detaily hráčů ani predikce nejsou dostupné.',
    inputTitle: 'Vyber přesná ID hráčů',
    active: 'Aktivní SimulationRun',
    help: 'Zadej dvě různá ID hráčů. Jde o současné atributy Runu, ne o předpověď zápasu nebo historické Saved H2H.',
    first: 'ID hráče A', second: 'ID hráče B', apply: 'Zobrazit atributy hráčů',
    clear: 'Vymazat ID hráčů', invalid: 'Zadej dvě různá platná ID hráčů.',
    pending: 'Pro načtení jiného porovnání potvrď změněná ID hráčů.',
    loadingDetail: 'Načítám přesné detaily hráčů…',
    failedDetail: 'Detail jednoho nebo obou hráčů není dostupný. Porovnání se nezobrazuje.',
    invalidDetail: 'Detaily hráčů neodpovídají požadovaným identitám nebo očekávaným polím.',
    loadingSample: 'Načítám vzorek hráčů…',
    invalidSample: 'Vzorek hráčů aktivního Runu je neplatný nebo nedostupný.',
    emptySample: 'Vzorek neobsahuje hráče. Přesná ID lze stále vyhledat.',
    choose: 'Zadej dvě ID hráčů pro zobrazení uložených atributů.',
    matched: 'Přesné identity ověřeny. Tyto atributy nejsou kurzy ani predikcí.',
    input: 'Vstupy prediktoru',
    firstCard: 'Hráč A', secondCard: 'Hráč B',
    summary: 'Porovnání vstupů',
    links: 'Odkazy',
    openPlayers: 'Otevřít hráče aktivního Runu',
    openSearch: 'Otevřít Viewer vyhledávání',
    openH2H: 'Otevřít porovnání H2H',
    deferred: 'Odložené výstupy prediktoru',
    deferredOne: 'Pro tento Run neexistuje napojený veřejný model predikcí.',
    deferredTwo: 'Neodhadujeme pravděpodobnost výhry, kurzy ani simulovaný výsledek.',
    deferredThree: 'Z atributů hráčů neodvozujeme historické Saved H2H ani budoucí události.',
    total: 'Celkový počet hráčů',
    sample: 'Velikost vzorku',
    id: 'ID SimulationRunu'
  }
} as const

const comparisonUrlKeys = ['playerA', 'playerB', 'player_a', 'player_b', 'a', 'b']

// Validate discovery rows independently from the exact player lookup.
function verifiedDiscoverySample(value: unknown, runId: string): { total: number; players: RunPlayerListItem[] } | null {
  if (!value || typeof value !== 'object') return null
  const sample = value as Record<string, unknown>
  const total = sample.total
  if (sample.run_id !== runId || typeof total !== 'number' ||
      !Number.isSafeInteger(total) || total < 0 || sample.limit !== 50 || sample.offset !== 0 ||
      !Array.isArray(sample.players) || sample.players.length > 50 || sample.players.length > total) return null
  const ids = new Set<string>()
  const players: RunPlayerListItem[] = []
  for (const row of sample.players) {
    if (!row || typeof row !== 'object' || typeof row.player_id !== 'string' ||
        !row.player_id.trim() || ids.has(row.player_id)) return null
    const player = verifiedComparisonPlayerDetail(row, row.player_id)
    if (!player) return null
    ids.add(player.player_id)
    // Suppress fields that belong to the other, richer Viewer sample schema.
    players.push({
      ...player, current_ovr: undefined, status: undefined, identity_source: undefined
    } as RunPlayerListItem)
  }
  return { total, players }
}

export function ViewerMatchPredictorPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const { language } = useLanguage()
  const t = copy[language]
  const [searchParams, setSearchParams] = useSearchParams()
  const requested = readViewerComparisonQueryParams(searchParams)
  const [draftA, setDraftA] = useState(requested.playerAParam)
  const [draftB, setDraftB] = useState(requested.playerBParam)
  useEffect(() => { setDraftA(requested.playerAParam) }, [requested.playerAParam])
  useEffect(() => { setDraftB(requested.playerBParam) }, [requested.playerBParam])

  const synced = draftA === requested.playerAParam && draftB === requested.playerBParam
  const valid = comparablePlayerIds(requested.playerAParam, requested.playerBParam)
  const enabled = Boolean(activeRunId && valid)

  // Include both the exact ID and the active legacy SimulationRun in the key.
  // Late replies to an old Run or earlier URL never become visible results.
  const left = useQuery({
    queryKey: ['viewer-match-predictor-exact-player', activeRunId, requested.playerAParam],
    queryFn: () => getRunPlayerDetail(activeRunId!, requested.playerAParam),
    enabled, retry: false,
  })
  const right = useQuery({
    queryKey: ['viewer-match-predictor-exact-player', activeRunId, requested.playerBParam],
    queryFn: () => getRunPlayerDetail(activeRunId!, requested.playerBParam),
    enabled, retry: false,
  })
  const sample = useQuery({
    queryKey: ['viewer-match-predictor-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId), retry: false,
  })

  const playerA = enabled && synced && left.isSuccess && !left.isFetching
    ? verifiedComparisonPlayerDetail(left.data, requested.playerAParam) : null
  const playerB = enabled && synced && right.isSuccess && !right.isFetching
    ? verifiedComparisonPlayerDetail(right.data, requested.playerBParam) : null
  const badDetails = enabled && synced &&
    ((left.isSuccess && !left.isFetching && !playerA) ||
      (right.isSuccess && !right.isFetching && !playerB))
  const detailError = enabled && synced && (left.isError || right.isError)
  const loadingDetails = enabled && synced && (
    left.isPending || right.isPending || left.isFetching || right.isFetching
  )

  // The sample can be absent, malformed or from a different Run. In all cases
  // this is independent from exact verified player detail GETs above.
  const verifiedSample = activeRunId && sample.isSuccess && !sample.isFetching
    ? verifiedDiscoverySample(sample.data, activeRunId) : null
  const validSample = verifiedSample !== null
  const players = verifiedSample?.players ?? []

  function changeIds(first: string, second: string): void {
    setSearchParams(previous => {
      const next = new URLSearchParams(previous)
      for (const key of comparisonUrlKeys) next.delete(key)
      if (first && second) {
        next.set('playerA', first)
        next.set('playerB', second)
      }
      return next
    })
  }
  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const first = draftA.trim(), second = draftB.trim()
    if (!comparablePlayerIds(first, second)) return
    changeIds(first, second)
  }
  function clear(): void {
    setDraftA('')
    setDraftB('')
    changeIds('', '')
  }

  if (!activeRunId) {
    return (
      <ViewerShellPage title={t.title} description={t.description}>
        <ViewerEmptyState>{t.noRun}</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  return (
    <ViewerShellPage title={t.title} description={t.description}>
      <ViewerLandingGrid>
        <ViewerSectionCard title={t.inputTitle} kicker={t.active} variant="hero">
          <p className="status">{t.help}</p>
          <form className="viewer-comparison-select" onSubmit={submit}>
            <label htmlFor="viewer-predictor-a">{t.first}</label>
            <input id="viewer-predictor-a" maxLength={256} value={draftA}
              onChange={event => setDraftA(event.target.value)} />
            <label htmlFor="viewer-predictor-b">{t.second}</label>
            <input id="viewer-predictor-b" maxLength={256} value={draftB}
              onChange={event => setDraftB(event.target.value)} />
            <div className="actions">
              <button type="submit" disabled={!comparablePlayerIds(draftA.trim(), draftB.trim())}>{t.apply}</button>
              <button type="button" onClick={clear}
                disabled={!requested.hasPlayerParams && !draftA && !draftB}>{t.clear}</button>
            </div>
          </form>
          <ViewerMetadataList ariaLabel="Match Predictor active run summary" items={[
            { label: t.id, value: activeRunId },
            { label: t.total, value: sample.isPending || sample.isFetching ? '…' : verifiedSample ? verifiedSample.total : '—' },
            { label: t.sample, value: sample.isPending || sample.isFetching ? '…' : validSample ? players.length : '—' },
          ]} />
          {sample.isPending || sample.isFetching ? <p role="status">{t.loadingSample}</p> : null}
          {sample.isError || (sample.isSuccess && !validSample && !sample.isFetching)
            ? <p role="alert">{t.invalidSample}</p> : null}
          {validSample && players.length === 0 ? <ViewerEmptyState>{t.emptySample}</ViewerEmptyState> : null}
          {!synced ? <p role="status">{t.pending}</p> : null}
          {requested.hasPlayerParams && !valid && synced ? <p role="alert">{t.invalid}</p> : null}
          {valid && loadingDetails ? <p role="status">{t.loadingDetail}</p> : null}
          {detailError ? <p role="alert">{t.failedDetail}</p> : null}
          {badDetails ? <p role="alert">{t.invalidDetail}</p> : null}
          {!requested.hasPlayerParams && synced ? (
            <>
              <ViewerEmptyState>{t.choose}</ViewerEmptyState>
              {validSample ? <ViewerSamplePlayersList players={players}
                label="Sample active run players for future predictor inputs" runId={activeRunId} /> : null}
            </>
          ) : null}
          {playerA && playerB && !loadingDetails && !detailError && !badDetails
            ? <p className="status">{t.matched}</p> : null}
        </ViewerSectionCard>
        {playerA && playerB && !loadingDetails && !detailError && !badDetails ? (
          <>
            <ViewerComparisonPlayerCard activeRunId={activeRunId} title={t.firstCard} player={playerA} />
            <ViewerComparisonPlayerCard activeRunId={activeRunId} title={t.secondCard} player={playerB} />
            <ViewerComparisonSummary playerA={playerA} playerB={playerB} title={t.summary} />
          </>
        ) : null}
        <ViewerSectionCard title={t.links} kicker="Read-only navigation">
          <ViewerActiveRunLinks links={[
            { label: t.openPlayers, to: viewerPlayersPath(activeRunId) },
            { label: t.openSearch, to: viewerTopSearchPath() },
            { label: t.openH2H, to: buildSelectedH2HPath({ playerA, playerB }) },
          ]} />
        </ViewerSectionCard>
        <ViewerSectionCard title={t.deferred} kicker="No prediction read model">
          <ul className="viewer-home-list" aria-label="Deferred Predictor Outputs">
            <li>{t.deferredOne}</li>
            <li>{t.deferredTwo}</li>
            <li>{t.deferredThree}</li>
          </ul>
        </ViewerSectionCard>
      </ViewerLandingGrid>
    </ViewerShellPage>
  )
}
