import { useEffect, useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { getWorldPackage, getWorldPackageGeography, replaceWorldPackageTimezoneAreas } from '../../api/client'
import type { WorldPackage, WorldPackageGeography } from '../../api/types'
import { useLanguage } from '../../i18n/LanguageContext'
import { formatApiError } from '../../utils/apiErrors'
import { isFingerprintConflict, timezoneAreaChanges, validateTimezoneAreas } from './review'
import type { AuthoredTimezoneArea, ReviewChange, TimezoneAreaDraft } from './review'

type Snapshot = { worldId: string; fingerprint: string; areas: AuthoredTimezoneArea[] }
type Write = Snapshot
type Review = { command: Write; changes: ReviewChange[] }

function copyAreas(areas: AuthoredTimezoneArea[]): TimezoneAreaDraft[] {
  return areas.map(({ code, name }) => ({ code, name }))
}

export function TimezoneAreaEditor({ pkg, geography, onDirtyChange }: {
  pkg: WorldPackage
  geography: WorldPackageGeography
  onDirtyChange?: (dirty: boolean) => void
}): JSX.Element | null {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const queryClient = useQueryClient()
  const routeRef = useRef(pkg.world_id)
  routeRef.current = pkg.world_id
  const [snapshot, setSnapshot] = useState<Snapshot>(() => ({
    worldId: pkg.world_id, fingerprint: pkg.fingerprint, areas: geography.timezone_areas
  }))
  const [areas, setAreas] = useState<TimezoneAreaDraft[]>(() => copyAreas(geography.timezone_areas))
  const [review, setReview] = useState<Review | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [success, setSuccess] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const editable = pkg.type === 'custom' && pkg.source === 'custom_config' && pkg.editable &&
    geography.world_id === pkg.world_id
  const currentDraft = areas.map((area, position) => ({ ...area, position }))
  const dirty = timezoneAreaChanges(snapshot.areas, currentDraft).length > 0
  const stale = snapshot.fingerprint !== pkg.fingerprint || snapshot.worldId !== pkg.world_id

  useEffect(() => {
    onDirtyChange?.(dirty)
    return () => onDirtyChange?.(false)
  }, [dirty, onDirtyChange])

  useEffect(() => {
    if (!dirty) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [dirty])

  const mutation = useMutation({
    mutationFn: (command: Write) =>
      replaceWorldPackageTimezoneAreas(command.worldId, command.areas, command.fingerprint),
    onSuccess: async (response, command) => {
      // Refresh exactly the submitted package, even when the user has navigated elsewhere.
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['world-package-geography', command.worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package', command.worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-validation', command.worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-packages'] })
      ])
      if (routeRef.current !== command.worldId) return
      if (response.world_id !== command.worldId) {
        setError(new Error(cs ? 'Odpověď patří jinému World Package.' : 'Response belongs to another World Package.'))
        return
      }
      const refreshed = queryClient.getQueryData<WorldPackage>(['world-package', command.worldId])
      const freshGeography = queryClient.getQueryData<WorldPackageGeography>(['world-package-geography', command.worldId])
      const coherent = Boolean(refreshed && freshGeography &&
        refreshed.world_id === command.worldId && freshGeography.world_id === command.worldId &&
        JSON.stringify(freshGeography.timezone_areas) === JSON.stringify(response.timezone_areas))
      if (!coherent || !refreshed || !freshGeography) {
        setReview(null)
        setError(new Error(cs
          ? 'Zápis byl potvrzen, ale aktuální verzi časových oblastí nelze bezpečně spojit s fingerprintem. Načtěte data znovu.'
          : 'The write returned but the current Timezone Areas could not be matched to the refreshed fingerprint. Reload current data.'))
        return
      }
      const saved = { worldId: command.worldId, fingerprint: refreshed.fingerprint, areas: freshGeography.timezone_areas }
      setSnapshot(saved)
      setAreas(copyAreas(saved.areas))
      setReview(null)
      setError(null)
      setSuccess(cs ? 'Časové oblasti byly uloženy. Další změny vyžadují novou kontrolu.' :
        'Timezone Areas saved. Further changes require a new review.')
    },
    onError: (failure, command) => {
      if (routeRef.current === command.worldId) { setError(failure); setSuccess('') }
    }
  })

  async function reload(): Promise<void> {
    if (mutation.isPending || refreshing) return
    if (!window.confirm(cs ? 'Načíst aktuální balíček a zahodit rozpracované časové oblasti?' :
      'Reload the World Package and discard unsaved Timezone Areas?')) return
    const worldId = pkg.world_id
    setRefreshing(true)
    try {
      const [freshPackage, freshGeography] = await Promise.all([
        queryClient.fetchQuery({queryKey:['world-package', worldId], queryFn: () => getWorldPackage(worldId), staleTime: 0}),
        queryClient.fetchQuery({queryKey:['world-package-geography', worldId], queryFn: () => getWorldPackageGeography(worldId), staleTime: 0})
      ])
      if (routeRef.current !== worldId) return
      if (freshPackage.world_id !== worldId || freshGeography.world_id !== worldId) {
        throw new Error(cs ? 'Načtená data nepatří tomuto balíčku.' : 'The loaded data belongs to another package.')
      }
      setSnapshot({worldId, fingerprint: freshPackage.fingerprint, areas: freshGeography.timezone_areas})
      setAreas(copyAreas(freshGeography.timezone_areas))
      setReview(null)
      setError(null)
      setSuccess('')
    } catch (failure) {
      if (routeRef.current === worldId) setError(failure)
    } finally {
      if (routeRef.current === worldId) setRefreshing(false)
    }
  }

  function prepareReview(): void {
    if (!editable || mutation.isPending || refreshing) return
    if (stale) { setError({status:409}); return }
    try {
      const parsed = validateTimezoneAreas(areas, cs)
      const changes = timezoneAreaChanges(snapshot.areas, parsed)
      setReview({command:{worldId: snapshot.worldId, fingerprint: snapshot.fingerprint, areas: parsed}, changes})
      setError(null); setSuccess('')
    } catch (failure) { setError(failure) }
  }

  function confirm(): void {
    if (!review || !editable || mutation.isPending || refreshing) return
    if (review.command.worldId !== pkg.world_id || review.command.fingerprint !== pkg.fingerprint) {
      setError({status:409})
      return
    }
    setError(null)
    mutation.mutate(review.command)
  }

  if (!editable) return null
  const busy = mutation.isPending || refreshing
  const update = (position: number, field: keyof TimezoneAreaDraft, value: string) => {
    setAreas(current => current.map((area, index) => index === position ? {...area, [field]: value} : area))
    setError(null); setSuccess('')
  }
  const move = (index: number, direction: -1 | 1) => {
    setAreas(current => {
      const target = index + direction
      if (target < 0 || target >= current.length) return current
      const copy = [...current]
      ;[copy[index],copy[target]] = [copy[target],copy[index]]
      return copy
    })
    setError(null); setSuccess('')
  }

  return <div aria-label="Timezone Area editor">
    <p className="status">{cs
      ? 'Upravujete pouze vlastní kopii. Pořadí tvoří uzavřený kruh; první a poslední oblast spolu sousedí.'
      : 'Only your custom copy can be edited. This is a circular order: the first and last areas are adjacent.'}</p>
    {success && <p className="status" role="status">{success}</p>}
    {stale && <p className="error" role="alert">{cs
      ? 'World Package se mezitím změnil. Před dalším zápisem je nutné znovu načíst aktuální fingerprint a zkontrolovat úpravy.'
      : 'The World Package changed. Reload to use its current fingerprint; any unsaved draft requires a new review.'}</p>}
    {error != null && <p className="error" role="alert">
      {isFingerprintConflict(error)
        ? (cs ? 'Konflikt změn: žádný zápis se neopakoval. Načtěte aktuální data a znovu je zkontrolujte.' :
          'Conflict: no write was retried. Reload current data and review the changes again.')
        : formatApiError(error)}
    </p>}
    {(isFingerprintConflict(error) || stale) && <button type="button" disabled={busy} onClick={() => void reload()}>
      {refreshing ? (cs ? 'Načítám…' : 'Reloading…') : (cs ? 'Načíst aktuální data' : 'Reload current data')}
    </button>}
    {review ? <div aria-label="Review Timezone Areas">
      <p><strong>World Package:</strong> <code>{review.command.worldId}</code></p>
      <p><strong>{cs ? 'Očekávaný fingerprint' : 'Expected fingerprint'}:</strong> <code>{review.command.fingerprint}</code></p>
      <p>{cs ? 'Pozice jsou počítané od nuly v API; níže je lidské pořadí.' :
        'API positions are zero-based; the display below uses human-friendly positions.'}</p>
      {review.changes.length === 0
        ? <p role="status">{cs ? 'Žádné změny k uložení.' : 'No changes to save.'}</p>
        : <table><thead><tr><th>{cs ? 'Pozice' : 'Position'}</th><th>{cs ? 'Původní' : 'Before'}</th><th>{cs ? 'Nová' : 'After'}</th></tr></thead>
          <tbody>{review.changes.map(change => <tr key={change.field}>
            <td>{change.field}</td><td>{change.before}</td><td>{change.after}</td>
          </tr>)}</tbody></table>}
      <p><button type="button" disabled={busy} onClick={() => setReview(null)}>{cs ? 'Zpět k úpravě' : 'Back to editing'}</button>{' '}
        <button type="button" disabled={busy || stale || review.changes.length === 0} onClick={confirm}>
          {busy ? (cs ? 'Ukládám…' : 'Saving…') : (cs ? 'Potvrdit a uložit' : 'Confirm and save')}
        </button></p>
    </div> : <>
      <fieldset disabled={busy || stale}><legend>{cs ? 'Upravit časové oblasti' : 'Edit Timezone Areas'}</legend>
        <table><thead><tr><th>{cs ? 'Pozice' : 'Position'}</th><th>{cs ? 'Kód' : 'Code'}</th><th>{cs ? 'Název' : 'Name'}</th><th>{cs ? 'Akce' : 'Action'}</th></tr></thead>
          <tbody>{areas.map((area, index) => <tr key={index}>
            <td>{index + 1}</td>
            <td><input aria-label={`Timezone Area code ${index}`} value={area.code} onChange={event => update(index, 'code', event.target.value)} /></td>
            <td><input aria-label={`Timezone Area name ${index}`} value={area.name} onChange={event => update(index, 'name', event.target.value)} /></td>
            <td><button type="button" disabled={index === 0} onClick={() => move(index, -1)}>{cs ? 'Nahoru' : 'Move Up'}</button>{' '}
              <button type="button" disabled={index === areas.length - 1} onClick={() => move(index, 1)}>{cs ? 'Dolů' : 'Move Down'}</button>{' '}
              <button type="button" onClick={() => {setAreas(current => current.filter((_, position) => position !== index));setError(null);setSuccess('')}}>{cs ? 'Odebrat' : 'Remove'}</button></td>
          </tr>)}</tbody></table>
        <p><button type="button" onClick={() => {setAreas(current => [...current,{code:'',name:''}]);setError(null);setSuccess('')}}>{cs ? '+ Přidat časovou oblast' : 'Add Timezone Area'}</button>{' '}
          <button type="button" disabled={!dirty} onClick={prepareReview}>{cs ? 'Zkontrolovat změny' : 'Review Timezone Areas'}</button>{' '}
          <button type="button" disabled={!dirty} onClick={() => {
            if (!window.confirm(cs ? 'Zahodit rozpracované změny časových oblastí?' : 'Discard unsaved Timezone Area changes?')) return
            setAreas(copyAreas(snapshot.areas));setError(null);setReview(null);setSuccess('')
          }}>{cs ? 'Zahodit změny' : 'Discard edits'}</button></p>
      </fieldset>
    </>}
  </div>
}
