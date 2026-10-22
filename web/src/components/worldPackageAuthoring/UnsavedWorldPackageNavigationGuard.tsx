import { useBlocker } from 'react-router-dom'
import type { RefObject } from 'react'

/**
 * The production app uses a data router. This guard catches SPA links,
 * browser Back/Forward (POP) and programmatic navigate, unlike beforeunload.
 * beforeunload is separately retained by each form for hard reload/tab close.
 *
 * On a successful create the mutation may navigate before React re-renders;
 * bypassRef is set synchronously only after the server acknowledges the write.
 */
export function UnsavedWorldPackageNavigationGuard({ active, cs, bypassRef }: {
  active: boolean
  cs: boolean
  bypassRef?: RefObject<boolean>
}): JSX.Element | null {
  const blocker = useBlocker(({ currentLocation, nextLocation }) =>
    active && !bypassRef?.current &&
    (currentLocation.pathname !== nextLocation.pathname ||
      currentLocation.search !== nextLocation.search)
  )
  if (blocker.state !== 'blocked') return null

  return <div role="alertdialog" aria-label={cs ? 'Neuložené změny' : 'Unsaved World Package changes'}>
    <p>{cs
      ? 'Máte neuložené změny World Package. Opravdu chcete odejít a zahodit je?'
      : 'You have unsaved World Package changes. Leave and discard them?'}</p>
    <p><button type="button" onClick={() => blocker.reset()}>
      {cs ? 'Zůstat a pokračovat v úpravě' : 'Stay and keep editing'}
    </button>{' '}
      <button type="button" onClick={() => blocker.proceed()}>
        {cs ? 'Zahodit změny a odejít' : 'Discard and leave'}
      </button></p>
  </div>
}
