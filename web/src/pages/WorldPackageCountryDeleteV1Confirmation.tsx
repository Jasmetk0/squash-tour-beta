import { SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function CountryV1DeleteConfirmation({
  code,
  name,
  saving,
  error,
  onConfirm,
  onCancel,
}: {
  code: string
  name: string
  saving: boolean
  error: unknown
  onConfirm: () => void
  onCancel: () => void
}): JSX.Element {
  return (
    <SectionCard title={`Delete ${code} — ${name}?`}>
      <p>
        This removes the Country from this Custom World source.
        <br />
        Existing Runs are not changed.
      </p>
      {error != null && <p className="error" role="alert">{formatApiError(error)}</p>}
      <button type="button" disabled={saving} onClick={onConfirm}>
        {saving ? 'Deleting…' : 'Delete country'}
      </button>{' '}
      <button type="button" disabled={saving} onClick={onCancel}>Cancel</button>
    </SectionCard>
  )
}
