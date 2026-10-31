/** Global, read-only Saved Branch cold-restore preview; never invokes restore/Save. */
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLanguage } from '../i18n/LanguageContext'
import {
  MAX_IMPORT_ARCHIVE_BYTES, previewSavedBranchImport,
  type SavedBranchImportPreview
} from '../api/runBranchArchiveImportPreview'
import { formatApiError } from '../utils/apiErrors'

const texts = {
  cs: {
    title: 'Kontrola importu Saved Branch', intro: 'Nejdřív nezávisle ověř soubor a případné kolize s cílovou databází. Tento náhled nic neobnovuje, neukládá ani nepřepisuje.',
    runs: 'Zpět na Runy', file: 'Soubor archivu .sqbranch', choose: 'Vybrat archiv do 128 MiB',
    invalid: 'Vyber platný neprázdný soubor .sqbranch do 128 MiB.',
    review: 'Ověřit archiv a konflikty', reviewing: 'Ověřuji archiv a původní historii…',
    clear: 'Zrušit náhled', loading: 'Ověřuji skutečný obsah přes SHA-256 a backend…',
    ready: 'Archiv je ověřený a v této chvíli nemá konflikt identit.',
    blocked: 'Import není možný: cílová databáze již obsahuje kolidující identity.',
    noCommit: 'Tato obrazovka je pouze náhled. Neobsahuje potvrzení obnovy ani žádný zápis do Runu.',
    name: 'Původní Run', selected: 'Vybraná Branch', viewer: 'Původní Viewer Branch',
    head: 'Saved HEAD', digest: 'SHA-256 archivu', size: 'Velikost',
    branches: 'Obsažené Branche', revisions: 'Uložené revize', audit: 'Události auditu',
    checkpoints: 'Checkpointy', omissions: 'Záměrně vynechané oblasti',
    unresolved: 'Nevyřešené reference balíčků', conflicts: 'Konflikty v cílové databázi',
    more: 'Další konflikty nejsou v náhledu vypsané; celkový počet:',
    limitation: 'Import v1 zachovává původní identity a neumí přepsat ani přejmenovat existující Run. Pro skutečnou obnovu je nutný samostatný výslovně potvrzený krok.'
  },
  en: {
    title: 'Saved Branch import review', intro: 'Independently validate the file and target-database collisions first. This preview never restores, saves or overwrites anything.',
    runs: 'Back to Runs', file: 'Archive .sqbranch file', choose: 'Select an archive up to 128 MiB',
    invalid: 'Select a valid nonempty .sqbranch archive up to 128 MiB.',
    review: 'Validate archive and conflicts', reviewing: 'Validating archive and original history…',
    clear: 'Clear review', loading: 'Verifying exact SHA-256 file bytes and backend history…',
    ready: 'The archive is verified and currently has no target identity conflicts.',
    blocked: 'Restore is blocked: the target already contains conflicting identities.',
    noCommit: 'This screen is preview-only. No restore confirmation or Run write is available here.',
    name: 'Original Run', selected: 'Selected Branch', viewer: 'Original Viewer Branch',
    head: 'Saved HEAD', digest: 'Archive SHA-256', size: 'Size',
    branches: 'Included Branches', revisions: 'Saved revisions', audit: 'Audit events',
    checkpoints: 'Checkpoints', omissions: 'Intentionally omitted areas',
    unresolved: 'Unresolved package references', conflicts: 'Target database conflicts',
    more: 'Additional conflicts are not shown here; total count:',
    limitation: 'Import v1 preserves original identities; it cannot overwrite or rename an existing Run. Actual restoration requires a separate explicitly confirmed action.'
  }
}

const fileAllowed = (file: File | null) => file !== null &&
  Number.isSafeInteger(file.size) && file.size > 0 &&
  file.size <= MAX_IMPORT_ARCHIVE_BYTES && /\.sqbranch$/i.test(file.name)

export function SavedBranchArchiveImportPage(): JSX.Element {
  const {language} = useLanguage()
  const l = texts[language]
  const [file,setFile] = useState<File | null>(null)
  const [reviewed,setReviewed] = useState<{file: File; preview: SavedBranchImportPreview} | null>(null)
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState<string | null>(null)
  const generation = useRef(0)
  const inFlight = useRef<AbortController | null>(null)

  useEffect(() => () => {
    generation.current += 1
    inFlight.current?.abort()
  }, [])

  const invalidate = () => {
    generation.current += 1
    inFlight.current?.abort()
    inFlight.current = null
    setReviewed(null)
    setError(null)
    setBusy(false)
  }
  const choose = (selected: File | null) => {
    invalidate()
    setFile(selected)
    if (selected && !fileAllowed(selected)) setError(l.invalid)
  }
  const preview = async () => {
    if (!fileAllowed(file) || busy) return
    const exactFile = file!
    const current = ++generation.current
    const controller = new AbortController()
    inFlight.current = controller
    setBusy(true)
    setError(null)
    setReviewed(null)
    try {
      const answer = await previewSavedBranchImport(exactFile, controller.signal)
      if (current !== generation.current || controller.signal.aborted) return
      setReviewed({file: exactFile,preview: answer})
    } catch (cause) {
      if (current === generation.current && !controller.signal.aborted) {
        setError(formatApiError(cause))
      }
    } finally {
      if (inFlight.current === controller) inFlight.current = null
      if (current === generation.current) setBusy(false)
    }
  }
  const data = reviewed?.file === file ? reviewed.preview : null
  return <section className="panel" aria-label={l.title}>
    <div className="page-intro">
      <h2>{l.title}</h2>
      <p>{l.intro}</p>
    </div>
    <p><Link to="/admin/runs">{l.runs}</Link></p>
    <p className="status">{l.noCommit}</p>
    <div className="run-home-status-block">
      <label htmlFor="saved-branch-import-file">{l.file}</label>
      <input id="saved-branch-import-file" type="file" accept=".sqbranch"
        aria-label={l.choose} disabled={busy}
        onChange={event => {
          const picked = event.currentTarget.files?.[0] ?? null
          choose(picked)
          event.currentTarget.value = ''
        }} />
      {file && <p className="status">{file.name} · {file.size.toLocaleString()} B</p>}
      <div className="actions">
        <button type="button" disabled={!fileAllowed(file) || busy}
          onClick={() => void preview()}>{busy ? l.reviewing : l.review}</button>
        {(file || data || error || busy) && <button type="button" onClick={() => {
          invalidate()
          setFile(null)
        }}>{l.clear}</button>}
      </div>
    </div>
    {busy && <p role="status">{l.loading}</p>}
    {error && <p role="alert" className="error">{error}</p>}
    {data && <section aria-label={l.title + ' result'}>
      <p role={data.can_restore ? 'status' : 'alert'}>{data.can_restore ? l.ready : l.blocked}</p>
      <dl>
        <dt>{l.name}</dt><dd>{data.display_name} · <code>{data.run_id}</code></dd>
        <dt>{l.selected}</dt><dd><code>{data.selected_branch_id}</code></dd>
        <dt>{l.viewer}</dt><dd><code>{data.viewer_branch_id}</code></dd>
        <dt>{l.head}</dt><dd><code>{data.selected_head_revision_id}</code></dd>
        <dt>{l.digest}</dt><dd><code style={{overflowWrap:'anywhere'}}>{data.archive_digest}</code></dd>
        <dt>{l.size}</dt><dd>{data.archive_size_bytes.toLocaleString()} B</dd>
        <dt>{l.branches}</dt><dd>{data.branches.length}</dd>
        <dt>{l.revisions}</dt><dd>{data.history.length}</dd>
        <dt>{l.audit}</dt><dd>{data.audit_event_count}</dd>
        <dt>{l.checkpoints}</dt><dd>{data.checkpoint_count}</dd>
        <dt>{l.unresolved}</dt><dd>{data.unresolved_package_references.length}</dd>
        <dt>{l.conflicts}</dt><dd>{data.conflicts.length}</dd>
      </dl>
      {data.conflicts.length > 0 && <ul aria-label={l.conflicts}>
        {data.conflicts.slice(0,50).map((conflict,i)=><li key={i}>
          {conflict.code} · {conflict.identity} {conflict.area ? ' · ' + conflict.area : ''}
        </li>)}
      </ul>}
      {data.conflicts.length > 50 && <p role="status">{l.more} {data.conflicts.length}</p>}
      <h3>{l.omissions}</h3>
      <ul>{data.omitted_areas.map((area,i)=><li key={i}>{area}</li>)}</ul>
      <p className="status">{l.limitation}</p>
    </section>}
  </section>
}
