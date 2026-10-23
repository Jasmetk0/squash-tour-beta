import type { FormEvent, ReactNode } from 'react'
import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { cloneWorldPackage, createWorldPackageCountry, deleteWorldPackageCountry, getWorldPackage, getWorldPackageCountries, getWorldPackageCountry, getWorldPackageGeography, getWorldPackageValidation, listWorldPackages, replaceWorldPackageTimezoneAreas, updateWorldPackageCountry, updateWorldPackageCountryPopulation } from '../api/client'
import type { CountryRecord, WorldPackage, WorldPackageClonePayload, WorldPackageCloneResponse, WorldPackageCountryCreatePayload, WorldPackageCountryDetail, WorldPackageCountryUpdateResponse, WorldPackageCountryPopulationUpdatePayload, WorldPackageCountryUpdatePayload, WorldPackageGeography, WorldPackageValidation } from '../api/types'
import { SectionCard } from '../components/RunScopedUi'
import { TimezoneAreaEditor } from '../components/worldPackageAuthoring/TimezoneAreaEditor'
import { UnsavedWorldPackageNavigationGuard } from '../components/worldPackageAuthoring/UnsavedWorldPackageNavigationGuard'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { fieldChanges, isFingerprintConflict, parseInteger, parsePopulations, parseRating, populationChanges, requiredName } from '../components/worldPackageAuthoring/review'
import type { ReviewChange } from '../components/worldPackageAuthoring/review'

function yesNo(value: boolean, yes: string, no: string): string {
  return value ? yes : no
}

function usageLabel(value: number | null, cs = false): string {
  return value === null ? (cs ? 'Využití zatím není sledováno' : 'Usage not tracked yet') : String(value)
}

function shortFingerprint(fingerprint: string): string {
  if (fingerprint.length <= 16) return fingerprint
  return `${fingerprint.slice(0, 8)}…${fingerprint.slice(-8)}`
}

function PackageTable({ packages, cs }: { packages: WorldPackage[], cs: boolean }): JSX.Element {
  if (packages.length === 0) {
    return <p className="status">{cs ? 'Registr zatím nevrátil žádné World Packages.' : 'No World Packages were returned by the registry.'}</p>
  }

  return (
    <div className="table-responsive"><table aria-label="World packages table">
      <thead>
        <tr>
          <th>{cs ? 'Název' : 'Name'}</th>
          <th>World ID</th>
          <th>{cs ? 'Typ' : 'Type'}</th>
          <th>{cs ? 'Stav' : 'Status'}</th>
          <th>{cs ? 'Ověření' : 'Validation'}</th>
          <th>{cs ? 'Režim balíčku' : 'Package mode'}</th>
          <th>{cs ? 'Země' : 'Countries'}</th>
          <th>{cs ? 'Kontinenty' : 'Continents'}</th>
          <th>{cs ? 'Regiony' : 'Regions'}</th>
          <th>{cs ? 'Cestovní regiony' : 'Travel Regions'}</th><th>{cs ? 'Časové oblasti' : 'Timezone Areas'}</th>
          <th>{cs ? 'Použito v Runech' : 'Used by Runs'}</th>
          <th>{cs ? 'Verze' : 'Version'}</th>
          <th>Fingerprint</th>
          <th>{cs ? 'Akce' : 'Actions'}</th>
        </tr>
      </thead>
      <tbody>
        {packages.map((pkg) => (
          <tr key={pkg.world_id}>
            <td>{pkg.name}</td>
            <td><code>{pkg.world_id}</code></td>
            <td>{pkg.type === 'custom' ? (cs ? 'Vlastní' : 'Custom') : (cs ? 'Vestavěný' : 'Built-in')}</td>
            <td>{pkg.status === 'archived' ? (cs ? 'Archivovaný' : 'Archived') : (cs ? 'Aktivní' : 'Active')}</td>
            <td>{pkg.validation_status === 'valid'
              ? (cs ? 'Ověřeno' : 'Valid')
              : (cs ? 'Neověřeno' : 'Unknown')}</td>
            <td>{yesNo(pkg.editable, cs ? 'Upravitelný zdroj' : 'Editable source', cs ? 'Jen pro čtení' : 'Read-only')}</td>
            <td>{pkg.country_count}</td>
            <td>{pkg.continent_count}</td>
            <td>{pkg.region_count}</td>
            <td>{pkg.travel_region_count}</td><td>{pkg.timezone_area_count}</td>
            <td>{usageLabel(pkg.used_by_run_count, cs)}</td>
            <td>{pkg.version}</td>
            <td><code title={pkg.fingerprint}>{shortFingerprint(pkg.fingerprint)}</code></td>
            <td><Link to={`/admin/world/library/${encodeURIComponent(pkg.world_id)}`}>{cs ? 'Otevřít World Package' : 'Open World Package'}</Link></td>
          </tr>
        ))}
      </tbody>
    </table></div>
  )
}

export function WorldLibraryPage(): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const packagesQuery = useQuery({ queryKey: ['world-packages'], queryFn: listWorldPackages, retry: false })
  const [search, setSearch] = useState('')
  const [packageType, setPackageType] = useState<'all' | 'built_in' | 'custom'>('all')
  const [packageStatus, setPackageStatus] = useState<'all' | 'active' | 'archived'>('all')
  const [validationStatus, setValidationStatus] = useState<'all' | 'valid' | 'unknown'>('all')
  const [editableOnly, setEditableOnly] = useState(false)
  const [sortBy, setSortBy] = useState<'registry' | 'name' | 'countries'>('registry')
  const packages = packagesQuery.data?.packages ?? []
  const normalizedSearch = search.trim().toLocaleLowerCase()
  const hasFilters = search !== '' || packageType !== 'all' || packageStatus !== 'all' ||
    validationStatus !== 'all' || editableOnly || sortBy !== 'registry'
  const visiblePackages = packages.filter(pkg =>
    (packageType === 'all' || (packageType === 'custom' ? pkg.type === 'custom' : pkg.type === 'official')) &&
    (packageStatus === 'all' || pkg.status === packageStatus) &&
    (validationStatus === 'all' || pkg.validation_status === validationStatus) &&
    (!editableOnly || pkg.editable) &&
    (normalizedSearch === '' || `${pkg.name} ${pkg.world_id}`.toLocaleLowerCase().includes(normalizedSearch))
  )
  if (sortBy !== 'registry') {
    visiblePackages.sort((a, b) => sortBy === 'countries'
      ? b.country_count - a.country_count || a.world_id.localeCompare(b.world_id)
      : a.name.localeCompare(b.name) || a.world_id.localeCompare(b.world_id))
  }
  const resetFilters = () => {
    setSearch('')
    setPackageType('all')
    setPackageStatus('all')
    setValidationStatus('all')
    setEditableOnly(false)
    setSortBy('registry')
  }

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>World Packages</h2>
        <p className="subtitle">{cs ? 'Registr dostupných zdrojů světa pro Squash Engine.' : 'Registry of available world sources for Squash Engine.'}</p>
      </div>
      <p>{cs
        ? 'World Packages jsou opakovaně použitelné zdroje světa. Run může vzniknout i prázdný; podporovaný zdroj lze později zkopírovat bez změny originálu.'
        : 'World Packages are reusable world sources. A Run can start empty; a supported source may be copied in later without altering the original.'}
        {' '}{cs ? 'Vlastní zdroje jsou uloženy v ' : 'Custom sources are stored under '}
        <code>config/world_packages/custom/</code>.
      </p>
      <p><Link to="/admin/world">{cs ? 'Zpět na přehled světů' : 'Back to World hub'}</Link></p>

      <SectionCard title={cs ? 'Dostupné World Packages' : 'Available World Packages'}>
        {packagesQuery.isLoading && <p className="status">{cs ? 'Načítám World Packages…' : 'Loading World Packages...'}</p>}
        {packagesQuery.error && <p className="error">{cs ? 'Nepodařilo se načíst World Packages: ' : 'Failed to load World Packages: '}{formatApiError(packagesQuery.error)}</p>}
        {packagesQuery.data && <>
          <div className="form-grid">
            <label>
              {cs ? 'Hledat World Package' : 'Search World Packages'}
              <input type="search" value={search} onChange={event => setSearch(event.target.value)}
                placeholder={cs ? 'Název nebo World ID' : 'Name or World ID'} />
            </label>
            <label>
              {cs ? 'Typ World Package' : 'World Package type'}
              <select value={packageType} onChange={event => setPackageType(event.target.value as typeof packageType)}>
                <option value="all">{cs ? 'Všechny typy' : 'All types'}</option>
                <option value="built_in">{cs ? 'Vestavěné' : 'Built-in'}</option>
                <option value="custom">{cs ? 'Vlastní' : 'Custom'}</option>
              </select>
            </label>
            <label>
              {cs ? 'Stav World Package' : 'World Package status'}
              <select value={packageStatus} onChange={event => setPackageStatus(event.target.value as typeof packageStatus)}>
                <option value="all">{cs ? 'Všechny stavy' : 'All statuses'}</option>
                <option value="active">{cs ? 'Aktivní' : 'Active'}</option>
                <option value="archived">{cs ? 'Archivované' : 'Archived'}</option>
              </select>
            </label>
            <label>
              {cs ? 'Ověření World Package' : 'World Package validation'}
              <select value={validationStatus} onChange={event => setValidationStatus(event.target.value as typeof validationStatus)}>
                <option value="all">{cs ? 'Všechny stavy ověření' : 'All validation states'}</option>
                <option value="valid">{cs ? 'Ověřené' : 'Valid'}</option>
                <option value="unknown">{cs ? 'Neověřené' : 'Unknown'}</option>
              </select>
            </label>
            <label>
              {cs ? 'Seřadit World Packages' : 'Sort World Packages'}
              <select value={sortBy} onChange={event => setSortBy(event.target.value as typeof sortBy)}>
                <option value="registry">{cs ? 'Pořadí registru' : 'Registry order'}</option>
                <option value="name">{cs ? 'Podle názvu (A–Z)' : 'Name (A–Z)'}</option>
                <option value="countries">{cs ? 'Podle počtu zemí (sestupně)' : 'Country count (descending)'}</option>
              </select>
            </label>
          </div>
          <label><input type="checkbox" checked={editableOnly}
            onChange={event => setEditableOnly(event.target.checked)} />
            {' '}{cs ? 'Pouze upravitelné zdroje' : 'Editable sources only'}
          </label>
          <p className="status">{cs
            ? 'Neověřeno znamená, že registr nepotvrdil výsledek validace; nejde automaticky o chybu.'
            : 'Unknown validation means the registry has not confirmed a result; it does not necessarily indicate an error.'}</p>
          <button type="button" disabled={!hasFilters} onClick={resetFilters}>
            {cs ? 'Vymazat filtry a řazení' : 'Clear filters and sorting'}
          </button>
          <p role="status">{cs
            ? `Zobrazeno ${visiblePackages.length} z ${packages.length} World Packages`
            : `Showing ${visiblePackages.length} of ${packages.length} World Packages`}</p>
          {packages.length > 0 && visiblePackages.length === 0
            ? <p className="status">{cs
              ? 'Žádné World Packages neodpovídají hledání nebo filtrům.'
              : 'No World Packages match your search or filters.'}</p>
            : <PackageTable packages={visiblePackages} cs={cs} />}
        </>}
      </SectionCard>
    </section>
  )
}

function DetailRow({ label, value }: { label: string, value: ReactNode }): JSX.Element {
  return <p><strong>{label}:</strong> {value}</p>
}


function CloneResultCard({ result }: { result: WorldPackageCloneResponse }): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  return (
    <div className={result.ok ? 'status' : 'error'} aria-label={cs ? 'Výsledek kopírování' : 'Clone result'}>
      {result.ok && result.dry_run && <p><strong>{cs ? 'Pouze náhled:' : 'Preview only:'}</strong> {cs ? 'Žádné soubory nebyly zapsány.' : 'no files were written.'}</p>}
      {result.ok && !result.dry_run && <p><strong>{cs ? 'Úspěch:' : 'Success:'}</strong> {cs ? 'Vlastní World Package byl vytvořen.' : 'Custom World package created.'}</p>}
      {!result.ok && <p><strong>{cs
        ? (result.dry_run ? 'Náhled se nezdařil:' : 'Kopírování se nezdařilo:')
        : (result.dry_run ? 'Preview failed:' : 'Clone failed:')}</strong> {cs ? 'Vytvoření kopie nebylo potvrzeno.' : 'The clone was not confirmed as created.'}</p>}
      <DetailRow label={cs ? 'Cílová cesta' : 'Target path'} value={<code>{result.target_path}</code>} />
      <DetailRow label={cs ? 'ID zdrojového světa' : 'Source world ID'} value={<code>{result.source_world_id}</code>} />
      <DetailRow label={cs ? 'Nové ID světa' : 'New world ID'} value={<code>{result.new_world_id}</code>} />
      <DetailRow label={cs ? 'Pouze náhled' : 'Dry run'} value={result.dry_run ? (cs ? 'Ano' : 'Yes') : (cs ? 'Ne' : 'No')} />
      <p><strong>{result.dry_run ? (cs ? 'Soubory uvedené v náhledu:' : 'Files listed in preview:') : (cs ? 'Vytvořené soubory:' : 'Created files:')}</strong></p>
      {result.created_files.length > 0 ? <ul>
        {result.created_files.map((file) => <li key={file}><code>{file}</code></li>)}
      </ul> : <p>{cs ? 'Žádné soubory nejsou uvedeny.' : 'No files listed.'}</p>}
      {result.errors.length > 0 && (
        <>
          <p><strong>{cs ? 'Chyby kopírování:' : 'Clone errors:'}</strong></p>
          <ul>
            {result.errors.map((error, index) => <li key={(error.field ?? 'root') + '-' + index}>{error.field ? error.field + ': ' : ''}{error.message}</li>)}
          </ul>
        </>
      )}
      {result.package && (
        <div aria-label={cs ? 'Souhrn balíčku po kopírování' : 'Clone package summary'}>
          <h4>{result.dry_run ? (cs ? 'Náhled balíčku' : 'Package preview') : result.ok ? (cs ? 'Vytvořený balíček' : 'Created package') : (cs ? 'Údaje balíčku' : 'Package details')}</h4>
          <DetailRow label="World ID" value={<code>{result.package.world_id}</code>} />
          <DetailRow label={cs ? 'Typ' : 'Type'} value={result.package.type} />
          <DetailRow label={cs ? 'Zdroj' : 'Source'} value={result.package.source} />
          <DetailRow label={cs ? 'Počty' : 'Counts'} value={<>
            {cs ? 'Země' : 'Countries'}: {result.package.country_count} · {cs ? 'Kontinenty' : 'Continents'}: {result.package.continent_count} · {cs ? 'Regiony' : 'Regions'}: {result.package.region_count} · {cs ? 'Cestovní regiony' : 'Travel regions'}: {result.package.travel_region_count}
          </>} />
          <DetailRow label={cs ? 'Otisk' : 'Fingerprint'} value={<code title={result.package.fingerprint}>{shortFingerprint(result.package.fingerprint)}</code>} />
        </div>
      )}
      {result.validation && (
        <div aria-label={cs ? 'Souhrn validace kopie' : 'Clone validation summary'}>
          <h4>{cs ? 'Validace' : 'Validation'}</h4>
          <DetailRow label={cs ? 'Stav' : 'Status'} value={result.validation.status} />
          <DetailRow label={cs ? 'Chyby' : 'Errors'} value={result.validation.error_count} />
          <DetailRow label={cs ? 'Varování' : 'Warnings'} value={result.validation.warning_count} />
          <DetailRow label={cs ? 'Informace' : 'Info'} value={result.validation.info_count} />
        </div>
      )}
      {result.ok && !result.dry_run && <p><Link to={'/admin/world/library/' + encodeURIComponent(result.new_world_id)}>{cs ? 'Otevřít detail nového vlastního World Package' : 'Open new Custom World detail'}</Link></p>}
    </div>
  )
}

function CloneBuiltInWorldSection({ source, onDirtyChange }: { source: WorldPackage; onDirtyChange: (dirty: boolean) => void }): JSX.Element {
  const queryClient = useQueryClient()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const sourceRef = useRef(source.world_id)
  sourceRef.current = source.world_id
  const locationKey = useLocation().key
  const activeLocationKey = useRef(locationKey)
  activeLocationKey.current = locationKey
  const mounted = useRef(false)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const [newWorldId, setNewWorldId] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState(`Custom world cloned from ${source.name}.`)
  const [result, setResult] = useState<WorldPackageCloneResponse | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const [review, setReview] = useState<{ sourceWorldId: string; sourceFingerprint: string; locationKey: string; payload: WorldPackageClonePayload } | null>(null)
  useEffect(() => {
    setNewWorldId(''); setName(''); setDescription(`Custom world cloned from ${source.name}.`)
    setResult(null); setApiError(null); setReview(null)
  }, [source.world_id, source.name])
  const cloneHasDraft = Boolean(newWorldId || name || description !== `Custom world cloned from ${source.name}.` || review)
  useUnsavedWorldPackageWarning(cloneHasDraft)
  useEffect(() => { onDirtyChange(cloneHasDraft); return () => onDirtyChange(false) }, [cloneHasDraft, onDirtyChange])
  const mutation = useMutation({
    mutationFn: (command: { sourceWorldId: string; sourceFingerprint: string; locationKey: string; payload: WorldPackageClonePayload }) => cloneWorldPackage(command.sourceWorldId, command.payload),
    onSuccess: (response, command) => {
      if (response.ok && !response.dry_run) {
        void queryClient.invalidateQueries({ queryKey: ['world-packages'] })
        void queryClient.invalidateQueries({ queryKey: ['world-package', response.new_world_id] })
        void queryClient.invalidateQueries({ queryKey: ['world-package-validation', response.new_world_id] })
      }
      if (!mounted.current || sourceRef.current !== command.sourceWorldId || activeLocationKey.current !== command.locationKey) return
      if (response.source_world_id !== command.sourceWorldId || response.new_world_id !== command.payload.new_world_id || response.dry_run !== command.payload.dry_run) {
        setApiError(cs ? 'Odpověď nepatří kontrolované kopii.' : 'The response does not match the reviewed clone.')
        return
      }
      setResult(response)
      setApiError(null)
      if (response.ok && !response.dry_run) {
        setReview(null); setNewWorldId(''); setName(''); setDescription(`Custom world cloned from ${source.name}.`)
      }
    },
    onError: (error, command) => {
      if (!mounted.current || sourceRef.current !== command.sourceWorldId || activeLocationKey.current !== command.locationKey) return
      setResult(null)
      setApiError(formatApiError(error))
    }
  })
  function prepare(dryRun: boolean): void {
    if (mutation.isPending) return
    const id = newWorldId.trim()
    if (!/^[a-z0-9][a-z0-9_]{2,63}$/.test(id)) {
      setApiError(cs ? 'ID musí začínat malým písmenem nebo číslicí (3–64 znaků, dále také podtržítko).' : 'World ID must start with a lowercase letter or digit (3–64 characters, then underscores also allowed).')
      return
    }
    if (!name.trim()) {
      setApiError(cs ? 'Název vlastní kopie je povinný.' : 'A name is required for the custom copy.')
      return
    }
    const payload: WorldPackageClonePayload = {
      new_world_id: id, name: name.trim(), description: description.trim() || null, dry_run: dryRun
    }
    setResult(null); setApiError(null)
    if (dryRun) {
      setReview(null)
      mutation.mutate({ sourceWorldId: source.world_id, sourceFingerprint: source.fingerprint, locationKey, payload })
    } else {
      setReview({sourceWorldId: source.world_id, sourceFingerprint: source.fingerprint, locationKey, payload})
    }
  }
  const confirm = () => {
    if (!review || mutation.isPending) return
    if (review.sourceWorldId !== source.world_id || review.sourceFingerprint !== source.fingerprint ||
        review.locationKey !== locationKey) {
      setApiError(cs ? 'Zdroj World Package se změnil. Návrh zkontrolujte znovu.' :
        'The source World Package changed. Review the clone again.')
      return
    }
    mutation.mutate(review)
  }
  return <SectionCard title={cs ? 'Vytvořit vlastní kopii World Package' : 'Clone Built-in World'}>
    <p>{cs ? 'Nezávislá vlastní kopie vestavěného zdroje' : 'Create an independent Custom World from'} <strong>{source.name}</strong>. {cs ? 'Originál ani existující Runy se nezmění.' : 'The original and existing Runs are never changed.'}</p>
    <p className="status">{cs ? 'Kopie zachová úplný obsah včetně historických zdrojových dat.' : 'The clone preserves the complete package tree, including historical evidence.'}</p>
    {review ? <div aria-label={cs ? 'Kontrola vytvoření kopie World Package' : 'Review World Package clone'}>
      <p><strong>{cs ? 'Zdroj' : 'Source'}:</strong> <code>{review.sourceWorldId}</code> · <strong>{cs ? 'Fingerprint zdroje' : 'Source fingerprint'}:</strong> <code>{review.sourceFingerprint}</code> · <strong>{cs ? 'Nová kopie' : 'New copy'}:</strong> <code>{review.payload.new_world_id}</code></p>
      <p><strong>{cs ? 'Název' : 'Name'}:</strong> {review.payload.name}</p>
      <p><strong>{cs ? 'Popis' : 'Description'}:</strong> {review.payload.description ?? '—'}</p>
      {review.sourceFingerprint !== source.fingerprint && <p role="alert" className="error">
        {cs ? 'Zdrojový balíček se změnil. Vraťte se k formuláři a zkontrolujte nové podklady.' :
          'The source World Package changed. Return to the form and review its current data.'}
      </p>}
      <p>{cs ? 'Zkontrolujte zdroj a cíl. Vytvoření vyžaduje výslovné potvrzení.' : 'Check the source and destination. The write needs explicit confirmation.'}</p>
      <button type="button" disabled={mutation.isPending} onClick={() => setReview(null)}>{cs ? 'Zpět k formuláři' : 'Back to form'}</button>{' '}
      <button type="button" disabled={mutation.isPending || review.sourceFingerprint !== source.fingerprint || review.locationKey !== locationKey} onClick={confirm}>{cs ? 'Potvrdit vytvoření kopie' : 'Confirm custom copy'}</button>
    </div> : <form onSubmit={event => {event.preventDefault(); prepare(false)}}>
      <fieldset disabled={mutation.isPending}>
        <label>{cs ? 'Nové World ID' : 'New World ID'}
          <input value={newWorldId} onChange={event => { setNewWorldId(event.target.value); setResult(null); setApiError(null) }} placeholder="my_custom_world" />
        </label>
        <p className="status">{cs ? '3–64 znaků; na začátku malé písmeno nebo číslice, potom i podtržítko.' : '3–64 characters; start with a lowercase letter or digit, underscores allowed thereafter.'}</p>
        <label>{cs ? 'Název' : 'Name'}<input value={name} onChange={event => { setName(event.target.value); setResult(null); setApiError(null) }} placeholder="My Custom World" /></label>
        <label>{cs ? 'Popis' : 'Description'}<textarea value={description} onChange={event => { setDescription(event.target.value); setResult(null); setApiError(null) }} /></label>
        <div className="actions">
          <button type="button" onClick={() => prepare(true)}>{cs ? 'Náhled kopírování' : 'Preview clone'}</button>
          <button type="submit">{cs ? 'Zkontrolovat vytvoření kopie' : 'Review custom copy'}</button>
        </div>
      </fieldset>
    </form>}
    {apiError && <p className="error" role="alert">{cs ? 'Kopírování se nezdařilo: ' : 'Clone request failed: '}{apiError}</p>}
    {result && <CloneResultCard result={result} />}
  </SectionCard>
}

function ValidationSection({ validation }: { validation: WorldPackageValidation }): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState<'all' | 'error' | 'warning' | 'info'>('all')
  const [order, setOrder] = useState<'severity' | 'source'>('severity')
  const normalizedSearch = search.trim().toLocaleLowerCase()
  const visibleChecks = validation.checks.filter(check =>
    (severity === 'all' || check.severity === severity) &&
    (normalizedSearch === '' ||
      [check.code, check.message, check.path, check.field]
        .some(value => value?.toLocaleLowerCase().includes(normalizedSearch)))
  )
  if (order === 'severity') {
    const priority = { error: 0, warning: 1, info: 2 }
    visibleChecks.sort((a, b) => priority[a.severity] - priority[b.severity])
  }
  const severityLabel = (value: 'error' | 'warning' | 'info'): string =>
    value === 'error' ? (cs ? 'Chyba' : 'Error') :
      value === 'warning' ? (cs ? 'Varování' : 'Warning') : (cs ? 'Informace' : 'Info')
  const checkStatusLabel = (value: 'passed' | 'warning' | 'failed'): string =>
    value === 'passed' ? (cs ? 'Prošlo' : 'Passed') :
      value === 'failed' ? (cs ? 'Selhalo' : 'Failed') : (cs ? 'Varování' : 'Warning')
  const overallLabel = validation.status === 'valid' ? (cs ? 'Platné' : 'Valid') :
    validation.status === 'warnings' ? (cs ? 'Varování' : 'Warnings') : (cs ? 'Chyby' : 'Errors')
  return (
    <SectionCard title={cs ? 'Ověření World Package' : 'World Package Validation'}>
      <DetailRow label={cs ? 'Celkový stav' : 'Overall status'} value={overallLabel} />
      <DetailRow label={cs ? 'Chyby' : 'Errors'} value={validation.error_count} />
      <DetailRow label={cs ? 'Varování' : 'Warnings'} value={validation.warning_count} />
      <DetailRow label={cs ? 'Informace' : 'Info'} value={validation.info_count} />
      <div className="form-grid">
        <label>{cs ? 'Hledat validační kontroly' : 'Search validation checks'}
          <input type="search" value={search} onChange={event => setSearch(event.target.value)}
            placeholder={cs ? 'Kód, zpráva, cesta nebo pole' : 'Code, message, path or field'} />
        </label>
        <label>{cs ? 'Závažnost kontroly' : 'Validation severity'}
          <select value={severity} onChange={event => setSeverity(event.target.value as typeof severity)}>
            <option value="all">{cs ? 'Všechny závažnosti' : 'All severities'}</option>
            <option value="error">{cs ? 'Chyby' : 'Errors'}</option>
            <option value="warning">{cs ? 'Varování' : 'Warnings'}</option>
            <option value="info">{cs ? 'Informace' : 'Info'}</option>
          </select>
        </label>
        <label>{cs ? 'Pořadí kontrol' : 'Validation order'}
          <select value={order} onChange={event => setOrder(event.target.value as typeof order)}>
            <option value="severity">{cs ? 'Nejdříve chyby' : 'Errors first'}</option>
            <option value="source">{cs ? 'Původní pořadí' : 'Source order'}</option>
          </select>
        </label>
      </div>
      <button type="button" disabled={!search && severity === 'all' && order === 'severity'}
        onClick={() => { setSearch(''); setSeverity('all'); setOrder('severity') }}>
        {cs ? 'Vymazat filtry kontrol' : 'Clear validation filters'}
      </button>
      <p role="status">{cs
        ? `Zobrazeno ${visibleChecks.length} z ${validation.checks.length} validačních kontrol`
        : `Showing ${visibleChecks.length} of ${validation.checks.length} validation checks`}</p>
      {validation.checks.length === 0
        ? <p className="status">{cs
          ? 'Tento World Package nevrátil žádné validační kontroly.'
          : 'No validation checks were returned for this World Package.'}</p>
        : visibleChecks.length === 0
          ? <p className="status">{cs
            ? 'Žádné validační kontroly neodpovídají filtrům.'
            : 'No validation checks match your filters.'}</p>
          : <div className="table-responsive"><table aria-label={cs ? 'Validační kontroly World Package' : 'World package validation checks'}>
            <thead>
              <tr>
                <th>{cs ? 'Kód' : 'Code'}</th>
                <th>{cs ? 'Závažnost' : 'Severity'}</th>
                <th>{cs ? 'Stav' : 'Status'}</th>
                <th>{cs ? 'Zpráva' : 'Message'}</th>
                <th>{cs ? 'Cesta' : 'Path'}</th>
                <th>{cs ? 'Pole' : 'Field'}</th>
              </tr>
            </thead>
            <tbody>
              {visibleChecks.map((check, index) => (
                <tr key={`${check.code}-${check.path ?? 'package'}-${check.field ?? 'root'}-${index}`}>
                  <td><code>{check.code}</code></td>
                  <td>{severityLabel(check.severity)}</td>
                  <td>{checkStatusLabel(check.status)}</td>
                  <td>{check.message}</td>
                  <td>{check.path ? <code>{check.path}</code> : '—'}</td>
                  <td>{check.field ? <code>{check.field}</code> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table></div>}
    </SectionCard>
  )
}

function GeographySection({ geography, pkg, onDirtyChange }: {
  geography: WorldPackageGeography; pkg: WorldPackage; onDirtyChange: (dirty: boolean) => void
}): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const editable = pkg.type === 'custom' && pkg.source === 'custom_config' && pkg.editable
  return <SectionCard title={cs ? 'Geografie' : 'Geography'}>
    <h4>{cs ? 'Kontinenty' : 'Continents'}</h4>
    <table><thead><tr><th>Code</th><th>Name</th></tr></thead><tbody>{geography.continents.map(item =>
      <tr key={item.code}><td><code>{item.code}</code></td><td>{item.name}</td></tr>)}</tbody></table>
    <h4>{cs ? 'Regiony' : 'Regions'}</h4>
    <table><thead><tr><th>Code</th><th>Name</th><th>Continent</th></tr></thead>
      <tbody>{geography.regions.map(item =>
        <tr key={item.code}><td><code>{item.code}</code></td><td>{item.name}</td>
          <td>{geography.continents.find(continent => continent.code === item.continent_code)?.name ?? '—'}</td></tr>)}</tbody>
    </table>
    <h4>{cs ? 'Cestovní regiony' : 'Travel Regions'}</h4>
    <table><thead><tr><th>Code</th><th>Name</th><th>Description</th></tr></thead>
      <tbody>{geography.travel_regions.map(item =>
        <tr key={item.code}><td><code>{item.code}</code></td><td>{item.name}</td><td>{item.description ?? '—'}</td></tr>)}</tbody>
    </table>
    <h4>{cs ? 'Časové oblasti' : 'Timezone Areas'}</h4>
    {!editable && !geography.timezone_areas_authored &&
      <p className="status">{cs ? 'Tento balíček zatím nemá vlastní časové oblasti.' : 'Unavailable — this package has not authored Timezone Areas.'}</p>}
    {!editable && geography.timezone_areas_authored &&
      <table><thead><tr><th>Position</th><th>Code</th><th>Name</th></tr></thead>
        <tbody>{geography.timezone_areas.map(item => <tr key={item.code}><td>{item.position}</td>
          <td><code>{item.code}</code></td><td>{item.name}</td></tr>)}</tbody></table>}
    {editable && <TimezoneAreaEditor pkg={pkg} geography={geography} onDirtyChange={onDirtyChange} />}
  </SectionCard>
}

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

function hasPopulationHistory(country: CountryRecord): boolean {
  return Object.values(country.population_by_year ?? {}).some(value => value !== null && value !== undefined)
}

function formatPopulationYears(populationByYear: CountryRecord['population_by_year'], cs: boolean): string {
  if (!populationByYear) return '—'
  const years = Object.entries(populationByYear)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([year]) => year)
    .sort((left, right) => Number(left) - Number(right))
  if (years.length === 0) return '—'
  return cs
    ? `${years.length} ${years.length === 1 ? 'rok' : years.length >= 2 && years.length <= 4 ? 'roky' : 'let'}: ${years.join(', ')}`
    : `${years.length} ${years.length === 1 ? 'year' : 'years'}: ${years.join(', ')}`
}

function CountryCell({ value }: { value: ReactNode }): JSX.Element {
  return <td>{value === null || value === undefined || value === '' ? '—' : value}</td>
}

function PackageCountriesTable({ countries, worldId, cs }: { countries: CountryRecord[], worldId: string, cs: boolean }): JSX.Element {
  return (
    <div className="table-responsive"><table aria-label={cs ? 'Země ve World Package' : 'World Package countries table'}>
      <thead>
        <tr>
          <th>{cs ? 'Kód' : 'Code'}</th>
          <th>{cs ? 'Název' : 'Name'}</th>
          <th>Region</th>
          <th>{cs ? 'Populace' : 'Population'}</th>
          <th>{cs ? 'Historie populace' : 'Population coverage'}</th>
          <th>{cs ? 'Rozloha km²' : 'Area km²'}</th>
          <th>{cs ? 'Cestovní region' : 'Travel Region'}</th>
          <th>{cs ? 'Časová oblast' : 'Timezone Area'}</th>
          <th>{cs ? 'Popularita squashe' : 'Squash Popularity'}</th>
          <th>{cs ? 'Dostupnost squashe' : 'Squash Access'}</th>
          <th>{cs ? 'Kvalita rozvoje' : 'Development Quality'}</th>
          <th>{cs ? 'Kvalita soutěží' : 'Competition Quality'}</th>
          <th>{cs ? 'Podpora elity' : 'Elite Support'}</th>
          <th>{cs ? 'Tradice squashe' : 'Squash Tradition'}</th>
          <th>{cs ? 'Akce' : 'Action'}</th>
        </tr>
      </thead>
      <tbody>
        {countries.map((country) => (
          <tr key={country.code}>
            <CountryCell value={<code>{country.code}</code>} />
            <CountryCell value={country.name} />
            <CountryCell value={country.region} />
            <CountryCell value={country.population.toLocaleString()} />
            <CountryCell value={formatPopulationYears(country.population_by_year, cs)} />
            <CountryCell value={formatNumber(country.area_km2)} />
            <CountryCell value={country.travel_region} />
            <CountryCell value={country.timezone_area} />
            <CountryCell value={country.squash_popularity} />
            <CountryCell value={country.squash_access} />
            <CountryCell value={country.development_quality} />
            <CountryCell value={country.competition_quality} />
            <CountryCell value={country.elite_support} />
            <CountryCell value={country.squash_tradition} />
            <td><Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(country.code)}`}>{cs ? 'Otevřít' : 'Open'}</Link></td>
          </tr>
        ))}
      </tbody>
    </table></div>
  )
}

const COUNTRY_LIST_PAGE_SIZE = 50

export function WorldPackageCountriesPage(): JSX.Element {
  const { worldId = '' } = useParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const countriesQuery = useQuery({
    queryKey: ['world-package-countries', worldId],
    queryFn: () => getWorldPackageCountries(worldId),
    enabled: Boolean(worldId),
    retry: false
  })
  const data = countriesQuery.data?.world_id === worldId ? countriesQuery.data : null
  const [search, setSearch] = useState('')
  const [region, setRegion] = useState('')
  const [missingTravelRegion, setMissingTravelRegion] = useState(false)
  const [missingTimezoneArea, setMissingTimezoneArea] = useState(false)
  const [populationHistory, setPopulationHistory] = useState<'all' | 'present' | 'missing'>('all')
  const [sortBy, setSortBy] = useState<'name' | 'code' | 'population'>('name')
  const [page, setPage] = useState(0)
  useEffect(() => {
    setSearch('')
    setRegion('')
    setMissingTravelRegion(false)
    setMissingTimezoneArea(false)
    setPopulationHistory('all')
    setSortBy('name')
    setPage(0)
  }, [worldId])
  const sourceCountries = data?.countries ?? []
  const missingTravelCount = sourceCountries.filter(country => !country.travel_region).length
  const missingTimezoneCount = sourceCountries.filter(country => !country.timezone_area).length
  const missingPopulationHistoryCount = sourceCountries.filter(country => !hasPopulationHistory(country)).length
  const regions = Array.from(new Set(sourceCountries.map(country => country.region).filter(Boolean)))
    .sort((left, right) => left.localeCompare(right))
  const normalizedSearch = search.trim().toLocaleLowerCase()
  const visibleCountries = sourceCountries
    .filter(country =>
      (region === '' || country.region === region) &&
      (!missingTravelRegion || !country.travel_region) &&
      (!missingTimezoneArea || !country.timezone_area) &&
      (populationHistory === 'all' ||
        (populationHistory === 'present' ? hasPopulationHistory(country) : !hasPopulationHistory(country))) &&
      `${country.code} ${country.name}`.toLocaleLowerCase().includes(normalizedSearch)
    )
    .sort((left, right) => sortBy === 'code'
      ? left.code.localeCompare(right.code) || left.name.localeCompare(right.name)
      : sortBy === 'population'
        ? right.population - left.population || left.code.localeCompare(right.code)
        : left.name.localeCompare(right.name) || left.code.localeCompare(right.code))
  const pageCount = Math.max(1, Math.ceil(visibleCountries.length / COUNTRY_LIST_PAGE_SIZE))
  const currentPage = Math.min(page, pageCount - 1)
  const pageCountries = visibleCountries.slice(
    currentPage * COUNTRY_LIST_PAGE_SIZE, (currentPage + 1) * COUNTRY_LIST_PAGE_SIZE
  )
  const clearFilters = () => {
    setSearch('')
    setRegion('')
    setMissingTravelRegion(false)
    setMissingTimezoneArea(false)
    setPopulationHistory('all')
    setSortBy('name')
    setPage(0)
  }

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>{cs ? 'Země ve World Package' : 'World Package Countries'}</h2>
        <p className="subtitle">{cs
          ? 'Přehled zemí z vybraného World Package.'
          : 'Assembled typed view of the countries in the selected World Package.'}</p>
      </div>
      <p><Link to={`/admin/world/library/${encodeURIComponent(worldId)}`}>{cs
        ? 'Zpět na detail World Package' : 'Back to World Package detail'}</Link></p>
      {countriesQuery.isLoading && <p className="status">{cs ? 'Načítám země…' : 'Loading package countries...'}</p>}
      {countriesQuery.error && <p className="error">{cs ? 'Nepodařilo se načíst země: ' : 'Failed to load package countries: '}{formatApiError(countriesQuery.error)}</p>}
      {countriesQuery.isSuccess && !data && <p role="alert" className="error">{cs
        ? 'Odpověď nepatří vybranému World Package.' : 'Response does not belong to the selected World Package.'}</p>}
      {data && (
        <>
          <SectionCard title={cs ? 'Balíček' : 'Package'}>
            <DetailRow label={cs ? 'Název světa' : 'World name'} value={data.world_name} />
            <DetailRow label="World ID" value={<code>{data.world_id}</code>} />
            <DetailRow label={cs ? 'Typ' : 'Type'} value={data.type} />
            <DetailRow label={cs ? 'Zdroj' : 'Source'} value={data.source} />
            <DetailRow label={cs ? 'Počet zemí' : 'Country count'} value={data.country_count} />
            <DetailRow label={cs ? 'Režim balíčku' : 'Package mode'} value={`${data.type === 'custom' ? (cs ? 'Vlastní' : 'Custom') : (cs ? 'Vestavěný' : 'Built-in')} · ${data.read_only ? (cs ? 'Jen pro čtení' : 'Read-only') : (cs ? 'Upravitelný zdroj' : 'Editable source')}`} />
          </SectionCard>
          <SectionCard title={cs ? 'Země v balíčku' : 'Package countries'}>
            <p className="status">{cs
              ? 'Tato stránka zatím nepodporuje hromadné úpravy, import ani export.'
              : 'This inspection screen does not currently provide bulk edit, import, or export actions.'}</p>
            {data.type === 'custom' && data.source === 'custom_config' && !data.read_only && <p><Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries/new`}>{cs ? '+ Přidat zemi' : '+ Add country'}</Link></p>}
            <div className="form-grid">
              <label>{cs ? 'Hledat podle názvu nebo kódu země' : 'Search by country name or code'}
                <input type="search" aria-label={cs ? 'Hledat země' : 'Search countries'} value={search}
                  onChange={event => { setSearch(event.target.value); setPage(0) }} />
              </label>
              <label>{cs ? 'Region' : 'Region'}
                <select aria-label={cs ? 'Filtrovat podle regionu' : 'Filter by region'} value={region}
                  onChange={event => { setRegion(event.target.value); setPage(0) }}>
                  <option value="">{cs ? 'Všechny regiony' : 'All regions'}</option>
                  {regions.map(value => <option key={value} value={value}>{value}</option>)}
                </select>
              </label>
              <label>{cs ? 'Historická populace' : 'Population history'}
                <select value={populationHistory}
                  onChange={event => { setPopulationHistory(event.target.value as typeof populationHistory); setPage(0) }}>
                  <option value="all">{cs ? 'Všechny země' : 'All countries'}</option>
                  <option value="present">{cs ? 'S populační řadou' : 'With population years'}</option>
                  <option value="missing">{cs ? 'Bez populační řady' : 'Without population years'}</option>
                </select>
              </label>
              <label>{cs ? 'Řazení zemí' : 'Sort countries'}
                <select value={sortBy} onChange={event => { setSortBy(event.target.value as typeof sortBy); setPage(0) }}>
                  <option value="name">{cs ? 'Název (A–Z)' : 'Name (A–Z)'}</option>
                  <option value="code">{cs ? 'Kód (A–Z)' : 'Code (A–Z)'}</option>
                  <option value="population">{cs ? 'Populace (sestupně)' : 'Population (descending)'}</option>
                </select>
              </label>
            </div>
            <div className="actions">
              <label><input type="checkbox" checked={missingTravelRegion}
                onChange={event => { setMissingTravelRegion(event.target.checked); setPage(0) }} />
                {' '}{cs ? 'Bez cestovního regionu' : 'Unassigned travel region'}
              </label>
              <label><input type="checkbox" checked={missingTimezoneArea}
                onChange={event => { setMissingTimezoneArea(event.target.checked); setPage(0) }} />
                {' '}{cs ? 'Bez časové oblasti' : 'Unassigned timezone area'}
              </label>
            </div>
            <p className="status">{cs
              ? `Nepřiřazený cestovní region: ${missingTravelCount} · Nepřiřazená časová oblast: ${missingTimezoneCount}`
              : `Unassigned travel region: ${missingTravelCount} · Unassigned timezone area: ${missingTimezoneCount}`}
              {' '}{cs ? 'Nepřiřazený údaj nemusí znamenat chybu.' : 'An unassigned value is not necessarily an error.'}</p>
            <p className="status">{cs
              ? `Bez historických populačních let: ${missingPopulationHistoryCount}`
              : `Without historical population years: ${missingPopulationHistoryCount}`}
              {' '}{cs
                ? 'Sleduje pouze vyplněné hodnoty v populační řadě; samo o sobě nejde o chybu ani potvrzení úplnosti dat.'
                : 'Counts populated year entries only; it is not itself an error or a completeness verdict.'}</p>
            <button type="button" disabled={!search && !region && !missingTravelRegion && !missingTimezoneArea && populationHistory === 'all' && sortBy === 'name'} onClick={clearFilters}>
              {cs ? 'Vymazat filtry a řazení' : 'Clear filters and sorting'}
            </button>
            <p role="status">{cs
              ? `Zobrazeno ${visibleCountries.length} z ${sourceCountries.length} zemí`
              : `Showing ${visibleCountries.length} of ${sourceCountries.length} countries`}</p>
            {visibleCountries.length === 0 ? <p className="status">{cs
              ? (sourceCountries.length === 0 ? 'Balíček neobsahuje žádné země.' : 'Žádná země neodpovídá filtrům.')
              : (sourceCountries.length === 0 ? 'This package has no countries.' : 'No countries match your filters.')}</p>
              : <>
                <PackageCountriesTable countries={pageCountries} worldId={worldId} cs={cs} />
                <div className="actions">
                  <button type="button" disabled={currentPage === 0} onClick={() => setPage(value => Math.max(0, value - 1))}>
                    {cs ? '← Předchozí' : '← Previous'}
                  </button>
                  <span>{cs ? 'Strana' : 'Page'} {currentPage + 1} / {pageCount}
                    {' · '}{currentPage * COUNTRY_LIST_PAGE_SIZE + 1}–{Math.min((currentPage + 1) * COUNTRY_LIST_PAGE_SIZE, visibleCountries.length)}
                    {' / '}{visibleCountries.length}</span>
                  <button type="button" disabled={currentPage >= pageCount - 1}
                    onClick={() => setPage(value => Math.min(pageCount - 1, value + 1))}>
                    {cs ? 'Další →' : 'Next →'}
                  </button>
                </div>
              </>}
          </SectionCard>
        </>
      )}
    </section>
  )
}

export function WorldLibraryDetailPage(): JSX.Element {
  const { worldId = '' } = useParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const [geographyDirty, setGeographyDirty] = useState(false)
  const [cloneDirty, setCloneDirty] = useState(false)
  const packageQuery = useQuery({
    queryKey: ['world-package', worldId],
    queryFn: () => getWorldPackage(worldId),
    enabled: Boolean(worldId),
    retry: false
  })
  const validationQuery = useQuery({
    queryKey: ['world-package-validation', worldId],
    queryFn: () => getWorldPackageValidation(worldId),
    enabled: Boolean(worldId),
    retry: false
  })
  const geographyQuery = useQuery({ queryKey: ['world-package-geography', worldId], queryFn: () => getWorldPackageGeography(worldId), enabled: Boolean(worldId), retry: false })
  const pkg = packageQuery.data?.world_id === worldId ? packageQuery.data : undefined

  return (
    <section className="panel">
      <UnsavedWorldPackageNavigationGuard active={geographyDirty || cloneDirty} cs={cs} />
      <div className="page-intro">
        <h2>World Package Details</h2>
        <p className="subtitle">Read-only inspection of a registered World Package.</p>
      </div>
      <p><Link to="/admin/world/library">Back to World Library</Link></p>
      {packageQuery.isLoading && <p className="status">Loading World Package...</p>}
      {packageQuery.error && <p className="error">Failed to load World Package: {formatApiError(packageQuery.error)}</p>}
      {pkg && (
        <>
          <h2>{pkg.name}</h2><p><code>{pkg.world_id}</code></p><p><strong>{pkg.type === 'custom' ? 'Custom' : 'Built-in'} · {pkg.editable ? 'Editable source' : 'Read-only'}</strong></p>
          <nav aria-label="Package sections"><a href="#overview">Overview</a> · <Link to={`/admin/world/library/${encodeURIComponent(pkg.world_id)}/countries`}>Countries</Link> · <a href="#geography">Geography</a> · <a href="#validation">Validation</a></nav>
          <div id="overview" />
          <SectionCard title="Metadata">
            <DetailRow label="Name" value={pkg.name} />
            <DetailRow label="World ID" value={<code>{pkg.world_id}</code>} />
            <DetailRow label="Description" value={pkg.description} />
            <DetailRow label="Type" value={pkg.type} />
            <DetailRow label="Status" value={pkg.status} />
            <DetailRow label="Source" value={pkg.source} />
            <DetailRow label="Version" value={pkg.version} />
            <DetailRow label="Fingerprint" value={<code>{pkg.fingerprint}</code>} />
          </SectionCard>
          <SectionCard title="Safety">
            <DetailRow label="Editable" value={yesNo(pkg.editable, 'Editable', 'Read-only')} />
            <DetailRow label="Deletable" value={yesNo(pkg.deletable, 'Deletable', 'Not deletable')} />
            <DetailRow label="Archivable" value={yesNo(pkg.archivable, 'Archivable', 'Not archivable')} />
            <p className="status">Built-in World Packages are protected repository inputs. Custom clones are independent editable sources; existing Runs keep their own saved snapshots.</p>
          </SectionCard>
          {pkg.type === 'official' && pkg.source === 'built_in' && <CloneBuiltInWorldSection key={`clone:${pkg.world_id}`} source={pkg} onDirtyChange={setCloneDirty} />}
          <SectionCard title="Contents">
            <DetailRow label="Countries" value={<><span>{pkg.country_count}</span> · <Link to={`/admin/world/library/${encodeURIComponent(pkg.world_id)}/countries`}>Open package countries</Link></>} />
            <DetailRow label="Continents" value={pkg.continent_count} />
            <DetailRow label="Regions" value={pkg.region_count} />
            <DetailRow label="Travel regions" value={pkg.travel_region_count} />
          </SectionCard>
          <SectionCard title="Usage">
            <DetailRow label="Used by runs" value={usageLabel(pkg.used_by_run_count)} />
            {pkg.used_by_run_count === null && <p className="status">Usage aggregation is not implemented yet.</p>}
          </SectionCard>
          <div id="geography" />
          {geographyQuery.isLoading && <p className="status">Loading geography...</p>}
          {geographyQuery.error && <p className="error">Failed to load geography: {formatApiError(geographyQuery.error)}</p>}
          {geographyQuery.data?.world_id === pkg.world_id &&
            <GeographySection key={`geography:${pkg.world_id}`} geography={geographyQuery.data} pkg={pkg} onDirtyChange={setGeographyDirty} />}
          <div id="validation" />
          {validationQuery.isLoading && (
            <SectionCard title="World Package Validation">
              <p className="status">Loading World Package validation...</p>
            </SectionCard>
          )}
          {validationQuery.error && (
            <SectionCard title="World Package Validation">
              <p className="error">Failed to load World Package validation: {formatApiError(validationQuery.error)}</p>
            </SectionCard>
          )}
          {validationQuery.data && validationQuery.data.world_id !== pkg.world_id &&
            <p role="alert" className="error">Validation response does not belong to this World Package.</p>}
          {validationQuery.data?.world_id === pkg.world_id &&
            <ValidationSection key={`validation:${pkg.world_id}`} validation={validationQuery.data} />}
        </>
      )}
    </section>
  )
}

export function WorldPackageCountryCreatePage(): JSX.Element {
  const { worldId = '' } = useParams()
  const navigate = useNavigate()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const queryClient = useQueryClient()
  const locationKey = useLocation().key
  const activeLocationKey = useRef(locationKey)
  activeLocationKey.current = locationKey
  const mounted = useRef(false)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const activeWorld = useRef(worldId)
  activeWorld.current = worldId
  const bypassNavigation = useRef(false)
  const packageQuery = useQuery({ queryKey: ['world-package', worldId], queryFn: () => getWorldPackage(worldId), enabled: Boolean(worldId), retry: false })
  const geographyQuery = useQuery({ queryKey: ['world-package-geography', worldId], queryFn: () => getWorldPackageGeography(worldId), enabled: Boolean(worldId), retry: false })
  const [identity, setIdentity] = useState({ code: '', name: '', notes: '', area: '' })
  const [region, setRegion] = useState('')
  const [travelRegion, setTravelRegion] = useState('')
  const [timezoneArea, setTimezoneArea] = useState('')
  const [values, setValues] = useState({ squash_popularity: '5.5', squash_access: '5.5', development_quality: '5.5', competition_quality: '5.5', elite_support: '5.5', squash_tradition: '5.5' })
  const [populations, setPopulations] = useState<Array<PopulationRow & { id: number }>>([{ id: 0, year: '2020', population: '' }])
  const [validationError, setValidationError] = useState('')
  const [requestError, setRequestError] = useState<unknown>(null)
  const [reloadError, setReloadError] = useState<unknown>(null)
  const [reloading, setReloading] = useState(false)
  const [review, setReview] = useState<{ worldId: string, payload: WorldPackageCountryCreatePayload, changes: ReviewChange[] } | null>(null)
  useEffect(() => {
    bypassNavigation.current = false
    setIdentity({ code: '', name: '', notes: '', area: '' })
    setRegion(''); setTravelRegion(''); setTimezoneArea('')
    setValues({ squash_popularity: '5.5', squash_access: '5.5', development_quality: '5.5', competition_quality: '5.5', elite_support: '5.5', squash_tradition: '5.5' })
    setPopulations([{ id: 0, year: '2020', population: '' }])
    setValidationError(''); setRequestError(null); setReloadError(null); setReview(null)
  }, [worldId])
  const dirty = Boolean(identity.code || identity.name || identity.notes || identity.area || region || travelRegion || timezoneArea || populations.some(row => row.population || row.year !== '2020') || Object.values(values).some(value => value !== '5.5') || review)
  useUnsavedWorldPackageWarning(dirty)
  const mutation = useMutation({
    mutationFn: (command: { worldId: string; locationKey: string; payload: WorldPackageCountryCreatePayload }) => createWorldPackageCountry(command.worldId, command.payload),
    onSuccess: (response, command) => {
      const matching = response.country_detail?.package?.world_id === command.worldId &&
        response.country_detail?.country?.code === command.payload.code &&
        (!response.package || response.package.world_id === command.worldId)
      if (!matching) {
        if (mounted.current && activeLocationKey.current === command.locationKey &&
            activeWorld.current === command.worldId) {
          setRequestError({status:409, responseMismatch:true, message:'Unexpected Country creation response'})
        }
        return
      }
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ['world-package-countries', command.worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package', command.worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-validation', command.worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-packages'] })
      ])
      if (mounted.current && activeLocationKey.current === command.locationKey &&
        activeWorld.current === command.worldId) {
        bypassNavigation.current = true
        navigate(`/admin/world/library/${encodeURIComponent(command.worldId)}/countries/${encodeURIComponent(command.payload.code)}`)
      }
    },
    onError: (error, command) => {
      if (mounted.current && activeLocationKey.current === command.locationKey &&
          activeWorld.current === command.worldId) setRequestError(error)
    }
  })
  const pkg = packageQuery.data
  const allowed = pkg?.world_id === worldId && pkg.type === 'custom' && pkg.source === 'custom_config' && pkg.editable
  const geography = geographyQuery.data?.world_id === worldId ? geographyQuery.data : undefined
  const setNumber = (key: keyof typeof values, value: string) => setValues(current => ({ ...current, [key]: value }))
  const sortedPopulations = [...populations].sort((left, right) => Number(left.year) - Number(right.year))
  const submit = (event: FormEvent) => {
    event.preventDefault()
    if (!pkg || !allowed || !geography || mutation.isPending || reloading) return
    try {
      const code = identity.code.trim()
      if (!/^[A-Z]{3}$/.test(code)) throw new Error(cs ? 'Kód země musí mít přesně tři velká písmena A–Z.' : 'Country code must be exactly three uppercase A–Z letters.')
      const payload: WorldPackageCountryCreatePayload = {
        code,
        name: requiredName(identity.name, cs ? 'Název' : 'Name', cs),
        notes: identity.notes.trim() ? identity.notes : null,
        area_km2: parseInteger(identity.area, cs ? 'Plocha' : 'Area', cs, 1, undefined, true),
        region: requiredName(region, 'Region', cs),
        travel_region: travelRegion || null, timezone_area: timezoneArea || null,
        rating_scale: 'country_ratings_1_10.v2',
        squash_popularity: parseRating(values.squash_popularity, 'Squash Popularity', cs, 'country_ratings_1_10.v2'),
        squash_access: parseRating(values.squash_access, 'Squash Access', cs, 'country_ratings_1_10.v2'),
        development_quality: parseRating(values.development_quality, 'Development Quality', cs, 'country_ratings_1_10.v2'),
        competition_quality: parseRating(values.competition_quality, 'Competition Quality', cs, 'country_ratings_1_10.v2'),
        elite_support: parseRating(values.elite_support, 'Elite Support', cs, 'country_ratings_1_10.v2'),
        squash_tradition: parseRating(values.squash_tradition, 'Squash Tradition', cs, 'country_ratings_1_10.v2'),
        court_count: null,
        population_by_year: parsePopulations(populations, cs),
        expected_package_fingerprint: pkg.fingerprint
      }
      if (!geography.regions.some(item => item.code === payload.region)) throw new Error(cs ? 'Region není v registru.' : 'Region is not in the geography registry.')
      if (payload.travel_region && !geography.travel_regions.some(item => item.code === payload.travel_region)) throw new Error(cs ? 'Neznámý cestovní region.' : 'Unknown Travel Region.')
      if (payload.timezone_area && !geography.timezone_areas.some(item => item.code === payload.timezone_area)) throw new Error(cs ? 'Neznámá časová oblast.' : 'Unknown Timezone Area.')
      const changes = [
        ...fieldChanges({}, payload, ['code','name','notes','area_km2','region','travel_region','timezone_area','squash_popularity','squash_access','development_quality','competition_quality','elite_support','squash_tradition']),
        ...populationChanges({}, payload.population_by_year).map(change => ({...change, field: `Population ${change.field}`}))
      ]
      setValidationError(''); setRequestError(null); setReview({ worldId, payload, changes })
    } catch (error) { setValidationError(formatApiError(error)) }
  }
  const save = () => {
    if (!review || !pkg || !allowed || mutation.isPending || reloading || sourceChanged) return
    if (review.worldId !== worldId || review.payload.expected_package_fingerprint !== pkg.fingerprint) {
      setRequestError({ status: 409, message: 'World Package changed before confirmation.' })
      return
    }
    setRequestError(null)
    mutation.mutate({ worldId: review.worldId, locationKey, payload: review.payload })
  }
  const reload = async () => {
    if (mutation.isPending || reloading) return
    if (!window.confirm(cs ? 'Načíst aktuální balíček a zahodit rozepsanou zemi?' : 'Reload the World Package and discard this draft country?')) return
    const originalWorld = worldId
    const originalLocation = locationKey
    setReloading(true)
    setReloadError(null)
    try {
      // The review must not be discarded until *both* authoritative reads
      // succeed. Invalidating cache is insufficient: a refetch can fail.
      // Fetch outside React Query: two separate fetchQuery calls can write an
      // inconsistent partial snapshot into the cache when one call fails.
      // Only publish the pair after both responses pass the source checks.
      const [freshPackage, freshGeography] = await Promise.all([
        getWorldPackage(originalWorld),
        getWorldPackageGeography(originalWorld)
      ])
      if (!mounted.current || activeWorld.current !== originalWorld ||
          activeLocationKey.current !== originalLocation) return
      if (freshPackage.world_id !== originalWorld || freshGeography.world_id !== originalWorld ||
          freshPackage.type !== 'custom' || freshPackage.source !== 'custom_config' || !freshPackage.editable) {
        throw new Error(cs ? 'Načtené podklady nepatří upravitelnému World Package.' :
          'The refreshed resources do not belong to this editable World Package.')
      }
      queryClient.setQueryData(['world-package', originalWorld], freshPackage)
      queryClient.setQueryData(['world-package-geography', originalWorld], freshGeography)
      setIdentity({ code: '', name: '', notes: '', area: '' })
      setRegion(''); setTravelRegion(''); setTimezoneArea('')
      setValues({ squash_popularity: '5.5', squash_access: '5.5', development_quality: '5.5', competition_quality: '5.5', elite_support: '5.5', squash_tradition: '5.5' })
      setPopulations([{ id: 0, year: '2020', population: '' }])
      setValidationError(''); setRequestError(null); setReloadError(null); setReview(null)
      void queryClient.invalidateQueries({queryKey:['world-package-countries', originalWorld]})
    } catch (error) {
      if (mounted.current && activeWorld.current === originalWorld &&
          activeLocationKey.current === originalLocation) setReloadError(error)
    } finally {
      if (mounted.current && activeWorld.current === originalWorld &&
          activeLocationKey.current === originalLocation) setReloading(false)
    }
  }
  if (packageQuery.isLoading || geographyQuery.isLoading) return <p className="status">{cs ? 'Načítám formulář země…' : 'Loading country form...'}</p>
  if (packageQuery.error || geographyQuery.error) return <p className="error">{cs ? 'Nepodařilo se načíst podklady formuláře: ' : 'Failed to load country form resources: '}{formatApiError(packageQuery.error ?? geographyQuery.error)}</p>
  const requestMessage = (requestError as {message?: unknown} | null)?.message
  const countryAlreadyExists = isFingerprintConflict(requestError) && /country .* already exists/i.test(typeof requestMessage === 'string' ? requestMessage : formatApiError(requestError))
  const responseMismatch = (requestError as {responseMismatch?:unknown} | null)?.responseMismatch === true
  const sourceChanged = (isFingerprintConflict(requestError) && !countryAlreadyExists) || responseMismatch
  if (!allowed) return <section className="panel"><p className="error">{cs ? 'Země lze vytvářet jen v upravitelné vlastní kopii World Package.' : 'Countries can only be created in an editable Custom World source.'}</p></section>
  return <section className="panel">
    <UnsavedWorldPackageNavigationGuard active={dirty} cs={cs} bypassRef={bypassNavigation} />
    <p><Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries`}>{cs ? 'Zpět na země' : 'Back to countries'}</Link></p>
    <h2>{cs ? 'Přidat zemi' : 'Add country'}</h2>
    {validationError && <p className="error" role="alert">{validationError}</p>}
    {reloadError != null && <p className="error" role="alert">{cs ? 'Aktualizaci se nepodařilo načíst. Rozpracovaná země zůstala zachovaná: ' : 'Reload failed. Your draft Country has been preserved: '}{formatApiError(reloadError)}</p>}
    {requestError != null && <p className="error" role="alert">{countryAlreadyExists
      ? (cs ? 'Země s tímto kódem již existuje. Vraťte se k formuláři a zvolte jiný kód.' : 'A country with this code already exists. Return to the form and choose a different code.')
      : responseMismatch
        ? (cs ? 'Server vrátil jinou zemi nebo balíček. Odpověď nebyla použita; načtěte aktuální stav.' : 'The server returned a different Country or World Package. The response was rejected; reload current data.')
        : sourceChanged
          ? (cs ? 'Balíček se mezitím změnil. Bez automatického opakování zápisu načtěte aktuální stav a zkontrolujte úpravu znovu.' : 'The package changed. No write was retried: reload current data and review the edit again.')
        : formatApiError(requestError)}{' '}
      {sourceChanged && <button type="button" disabled={mutation.isPending || reloading} onClick={() => void reload()}>{reloading ? (cs ? 'Načítám…' : 'Reloading…') : (cs ? 'Načíst aktuální data' : 'Reload current data')}</button>}
    </p>}
    {review
      ? <SectionCard title={cs ? 'Před uložením' : 'Before saving'}>
          <ConfirmWorldPackageChanges title={cs ? 'Kontrola nové země' : 'Review new country'}
            worldId={review.worldId} countryCode={review.payload.code} fingerprint={review.payload.expected_package_fingerprint}
            changes={review.changes} cs={cs} saving={mutation.isPending || reloading} locked={sourceChanged || countryAlreadyExists} onBack={() => setReview(null)} onConfirm={save} />
        </SectionCard>
      : <form onSubmit={submit}><fieldset disabled={mutation.isPending || reloading || sourceChanged}>
          <fieldset><legend>{cs ? 'Identita' : 'Identity'}</legend>
            <label>{cs ? 'Kód' : 'Code'}<input required pattern="[A-Z]{3}" maxLength={3} value={identity.code} onChange={event => setIdentity(current => ({...current,code:event.target.value}))} /></label>
            <label>{cs ? 'Název' : 'Name'}<input required value={identity.name} onChange={event => setIdentity(current => ({...current,name:event.target.value}))} /></label>
            <label>{cs ? 'Poznámky' : 'Notes'}<textarea value={identity.notes} onChange={event => setIdentity(current => ({...current,notes:event.target.value}))} /></label>
            <label>{cs ? 'Plocha km²' : 'Area km²'}<input type="number" min="1" step="1" value={identity.area} onChange={event => setIdentity(current => ({...current,area:event.target.value}))} /></label>
          </fieldset>
          <fieldset><legend>{cs ? 'Geografie' : 'Geography'}</legend>
            <label>Region<select required value={region} onChange={event => setRegion(event.target.value)}><option value="">{cs ? 'Vyberte region' : 'Select region'}</option>{geography?.regions.map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
            <label>Travel Region<select value={travelRegion} onChange={event => setTravelRegion(event.target.value)}><option value="">{cs ? 'Žádný' : 'None'}</option>{geography?.travel_regions.map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
            <label>Timezone Area<select value={timezoneArea} onChange={event => setTimezoneArea(event.target.value)}><option value="">{cs ? 'Nepřiřazeno' : 'Not assigned'}</option>{geography?.timezone_areas.map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
          </fieldset>
          <fieldset><legend>{cs ? 'Populace' : 'Population'}</legend>
            {sortedPopulations.map(row => <div key={row.id}>
              <input aria-label={`Population year ${row.id === 0 ? '2020' : row.id}`} type="number" min="1955" max="2050" step="1" required readOnly={row.year === '2020'} value={row.year} onChange={event => setPopulations(current => current.map(item => item.id === row.id ? {...item,year:event.target.value} : item))} />
              <input aria-label={`Population value ${row.year || row.id}`} type="number" min="1" step="1" required value={row.population} onChange={event => setPopulations(current => current.map(item => item.id === row.id ? {...item,population:event.target.value} : item))} />
              {row.year !== '2020' && <button type="button" onClick={() => setPopulations(current => current.filter(item => item.id !== row.id))}>{cs ? 'Odebrat' : 'Remove'}</button>}
            </div>)}
            <button type="button" onClick={() => setPopulations(current => [...current, {id: Math.max(...current.map(row => row.id)) + 1,year:'',population:''}])}>{cs ? '+ Přidat rok' : '+ Add authored year'}</button>
          </fieldset>
          <fieldset><legend>{cs ? 'Herní atributy země' : 'Country game attributes'}</legend>
            {Object.entries(values).map(([key, value]) => <label key={key}>{key.split('_').join(' ')}<input type="number" required min={1} max={10} step={0.1} value={value} onChange={event => setNumber(key as keyof typeof values, event.target.value)} /></label>)}
          </fieldset>
          <button type="submit">{cs ? 'Zkontrolovat před uložením' : 'Review before saving'}</button>
        </fieldset></form>}
  </section>
}

function countryWriteResponseMatches(response: WorldPackageCountryUpdateResponse, worldId: string, code: string): boolean {
  return response.country_detail?.package?.world_id === worldId &&
    response.country_detail?.country?.code === code &&
    (!response.package || response.package.world_id === worldId)
}

type CountryWrite = { worldId: string; countryCode: string; locationKey: string; payload: WorldPackageCountryUpdatePayload }
type PopulationWrite = { worldId: string; countryCode: string; locationKey: string; payload: WorldPackageCountryPopulationUpdatePayload }
type DeleteWrite = { worldId: string; countryCode: string; locationKey: string; fingerprint: string }

function useUnsavedWorldPackageWarning(active: boolean): void {
  useEffect(() => {
    if (!active) return
    const warning = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', warning)
    return () => window.removeEventListener('beforeunload', warning)
  }, [active])
}

function ConfirmWorldPackageChanges({ title, worldId, countryCode, fingerprint, changes, saving, locked = false, cs, onBack, onConfirm }: {
  title: string; worldId: string; countryCode: string; fingerprint: string; changes: ReviewChange[];
  saving: boolean; locked?: boolean; cs: boolean; onBack: () => void; onConfirm: () => void
}): JSX.Element {
  return <div aria-label="World Package change review">
    <h3>{title}</h3>
    <p>{cs ? 'Zkontrolujte přesný cíl a změny před uložením.' : 'Check the exact destination and changes before saving.'}</p>
    <p><strong>World Package:</strong> <code>{worldId}</code> · <strong>{cs ? 'Země' : 'Country'}:</strong> <code>{countryCode}</code></p>
    <p><strong>{cs ? 'Očekávaný fingerprint' : 'Expected fingerprint'}:</strong> <code>{fingerprint}</code></p>
    {changes.length === 0
      ? <p role="status">{cs ? 'Žádné změny k uložení.' : 'No changes to save.'}</p>
      : <table><thead><tr><th>{cs ? 'Údaj' : 'Field'}</th><th>{cs ? 'Původní' : 'Before'}</th><th>{cs ? 'Nová hodnota' : 'After'}</th></tr></thead>
          <tbody>{changes.map(change => <tr key={change.field}><td>{change.field}</td><td>{change.before}</td><td>{change.after}</td></tr>)}</tbody></table>}
    <p><button type="button" disabled={saving} onClick={onBack}>{cs ? 'Zpět k úpravě' : 'Back to editing'}</button>{' '}
      <button type="button" disabled={saving || locked || changes.length === 0} onClick={onConfirm}>
        {saving ? (cs ? 'Ukládání…' : 'Saving…') : (cs ? 'Potvrdit a uložit' : 'Confirm and save')}
      </button></p>
  </div>
}

export function WorldPackageCountryDetailPage(): JSX.Element {
  const { worldId = '', countryCode = '' } = useParams()
  const locationKey = useLocation().key
  const activeLocationKey = useRef(locationKey)
  activeLocationKey.current = locationKey
  const mounted = useRef(false)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
  const { language } = useLanguage()
  const cs = language === 'cs'
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const routeKey = `${worldId}/${countryCode}`
  const activeRoute = useRef(routeKey)
  activeRoute.current = routeKey
  const [editing, setEditing] = useState(false)
  const [populationEditing, setPopulationEditing] = useState(false)
  const [success, setSuccess] = useState('')
  const [writeError, setWriteError] = useState<unknown>(null)
  const [deleteReview, setDeleteReview] = useState<(DeleteWrite & { countryName: string }) | null>(null)
  const [reloadingConflict, setReloadingConflict] = useState(false)
  const [reloadError, setReloadError] = useState<unknown>(null)
  useEffect(() => {
    setEditing(false); setPopulationEditing(false); setSuccess(''); setWriteError(null); setDeleteReview(null); setReloadError(null); setReloadingConflict(false)
  }, [routeKey])
  useUnsavedWorldPackageWarning(editing || populationEditing)
  const query = useQuery({ queryKey: ['world-package-country', worldId, countryCode], queryFn: () => getWorldPackageCountry(worldId, countryCode), enabled: Boolean(worldId && countryCode), retry: false })
  const geographyQuery = useQuery({ queryKey: ['world-package-geography', worldId], queryFn: () => getWorldPackageGeography(worldId), enabled: Boolean(worldId), retry: false })
  const refresh = async (targetWorldId: string, targetCountryCode: string) => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['world-package-country', targetWorldId, targetCountryCode] }),
      queryClient.invalidateQueries({ queryKey: ['world-package-countries', targetWorldId] }),
      queryClient.invalidateQueries({ queryKey: ['world-package', targetWorldId] }),
      queryClient.invalidateQueries({ queryKey: ['world-package-validation', targetWorldId] }),
      queryClient.invalidateQueries({ queryKey: ['world-packages'] })
    ])
  }
  const mutation = useMutation({
    mutationFn: ({ worldId: targetWorldId, countryCode: targetCode, payload }: CountryWrite) => updateWorldPackageCountry(targetWorldId, targetCode, payload),
    onSuccess: (response, command) => {
      if (!countryWriteResponseMatches(response, command.worldId, command.countryCode)) {
        if (mounted.current && activeLocationKey.current === command.locationKey &&
            activeRoute.current === `${command.worldId}/${command.countryCode}`) {
          setWriteError({status:409, scopeMismatch:true, message:'Unexpected World Package Country response'})
        }
        return
      }
      queryClient.setQueryData(['world-package-country', command.worldId, command.countryCode], response.country_detail)
      void refresh(command.worldId, command.countryCode)
      if (mounted.current && activeLocationKey.current === command.locationKey && activeRoute.current === `${command.worldId}/${command.countryCode}`) {
        setEditing(false)
        setWriteError(null)
        setSuccess(cs ? `Země uložena. Stav validace: ${response.validation.status}.` : `Country saved. Validation status: ${response.validation.status}.`)
      }
    },
    onError: (error, command) => {
      if (mounted.current && activeLocationKey.current === command.locationKey && activeRoute.current === `${command.worldId}/${command.countryCode}`) setWriteError(error)
    }
  })
  const populationMutation = useMutation({
    mutationFn: ({ worldId: targetWorldId, countryCode: targetCode, payload }: PopulationWrite) => updateWorldPackageCountryPopulation(targetWorldId, targetCode, payload),
    onSuccess: (response, command) => {
      if (!countryWriteResponseMatches(response, command.worldId, command.countryCode)) {
        if (mounted.current && activeLocationKey.current === command.locationKey &&
            activeRoute.current === `${command.worldId}/${command.countryCode}`) {
          setWriteError({status:409, scopeMismatch:true, message:'Unexpected World Package Country response'})
        }
        return
      }
      queryClient.setQueryData(['world-package-country', command.worldId, command.countryCode], response.country_detail)
      void refresh(command.worldId, command.countryCode)
      if (mounted.current && activeLocationKey.current === command.locationKey && activeRoute.current === `${command.worldId}/${command.countryCode}`) {
        setPopulationEditing(false)
        setWriteError(null)
        setSuccess(cs ? `Populace uložena. Stav validace: ${response.validation.status}.` : `Population saved. Validation status: ${response.validation.status}.`)
      }
    },
    onError: (error, command) => {
      if (mounted.current && activeLocationKey.current === command.locationKey && activeRoute.current === `${command.worldId}/${command.countryCode}`) setWriteError(error)
    }
  })
  const deleteMutation = useMutation({
    mutationFn: ({ worldId: targetWorldId, countryCode: targetCode, fingerprint }: DeleteWrite) => deleteWorldPackageCountry(targetWorldId, targetCode, fingerprint),
    onSuccess: (response, command) => {
      if (response.deleted_country_code !== command.countryCode ||
          response.package?.world_id !== command.worldId) {
        if (mounted.current && activeLocationKey.current === command.locationKey &&
            activeRoute.current === `${command.worldId}/${command.countryCode}`) {
          setWriteError({status:409, scopeMismatch:true, message:'Unexpected Country deletion response'})
        }
        return
      }
      void refresh(command.worldId, command.countryCode)
      if (mounted.current && activeLocationKey.current === command.locationKey && activeRoute.current === `${command.worldId}/${command.countryCode}`) {
        navigate(`/admin/world/library/${encodeURIComponent(command.worldId)}/countries`)
      }
    },
    onError: (error, command) => {
      if (mounted.current && activeLocationKey.current === command.locationKey && activeRoute.current === `${command.worldId}/${command.countryCode}`) setWriteError(error)
    }
  })
  const raw = query.data
  const data = raw?.package.world_id === worldId && raw.country.code === countryCode ? raw : undefined
  const canEdit = data?.package.type === 'custom' && data.package.source === 'custom_config' && data.package.editable
  const pending = mutation.isPending || populationMutation.isPending || deleteMutation.isPending || reloadingConflict
  const scopeMismatch = (writeError as {scopeMismatch?:unknown} | null)?.scopeMismatch === true
  const timeline = Object.entries(data?.country.population_by_year ?? {}).filter((entry): entry is [string, number] => entry[1] != null).sort(([a], [b]) => Number(a) - Number(b))
  const reloadAfterConflict = async () => {
    if (pending) return
    if (!window.confirm(cs ? 'Načíst aktuální data a zahodit neuloženou úpravu?' : 'Reload current data and discard the unsaved edit?')) return
    const targetRoute = routeKey
    const targetLocation = locationKey
    setReloadingConflict(true)
    setReloadError(null)
    try {
      // Refetch a real Country detail; invalidation alone may resolve despite
      // an HTTP failure, silently discarding the user's original proposal.
      // Verify the server response *before* publishing it to the scoped
      // cache. fetchQuery would cache an unrelated Country before detection.
      const fresh = await getWorldPackageCountry(worldId, countryCode)
      if (!mounted.current || activeLocationKey.current !== targetLocation || activeRoute.current !== targetRoute) return
      if (fresh.package.world_id !== worldId || fresh.country.code !== countryCode) {
        throw new Error(cs ? 'Načtené údaje nepatří původní zemi.' : 'Reloaded data belongs to a different Country.')
      }
      queryClient.setQueryData(['world-package-country', worldId, countryCode], fresh)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['world-package', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-countries', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-validation', worldId] })
      ])
      if (!mounted.current || activeLocationKey.current !== targetLocation || activeRoute.current !== targetRoute) return
      setEditing(false); setPopulationEditing(false); setDeleteReview(null)
      setWriteError(null); setReloadError(null); setSuccess('')
    } catch (error) {
      if (mounted.current && activeLocationKey.current === targetLocation && activeRoute.current === targetRoute) {
        setReloadError(error)
      }
    } finally {
      if (mounted.current && activeLocationKey.current === targetLocation && activeRoute.current === targetRoute) {
        setReloadingConflict(false)
      }
    }
  }
  const handleCountrySave = (payload: WorldPackageCountryUpdatePayload) => {
    if (!canEdit || !data || pending || isFingerprintConflict(writeError)) return
    if (payload.expected_package_fingerprint !== data.package.fingerprint) {
      setWriteError({ status: 409, message: 'World Package changed before confirmation.' })
      return
    }
    setWriteError(null)
    mutation.mutate({ worldId, countryCode, locationKey, payload })
  }
  const handlePopulationSave = (payload: WorldPackageCountryPopulationUpdatePayload) => {
    if (!canEdit || !data || pending || isFingerprintConflict(writeError)) return
    if (payload.expected_package_fingerprint !== data.package.fingerprint) {
      setWriteError({ status: 409, message: 'World Package changed before confirmation.' })
      return
    }
    setWriteError(null)
    populationMutation.mutate({ worldId, countryCode, locationKey, payload })
  }
  return <section className="panel">
    <UnsavedWorldPackageNavigationGuard active={editing || populationEditing} cs={cs} />
    <p><Link to="/admin/world/library">World Packages</Link> → <Link to={`/admin/world/library/${encodeURIComponent(worldId)}`}>{data?.package.name ?? worldId}</Link> → <Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries`}>Countries</Link>{data ? ` → ${data.country.name}` : ''}</p>
    {query.isLoading && <p className="status">{cs ? 'Načítám zemi…' : 'Loading country...'}</p>}
    {query.error && <p className="error">{cs ? 'Nepodařilo se načíst zemi: ' : 'Failed to load country: '}{formatApiError(query.error)}</p>}
    {data && <>
      <div className="page-intro"><h2>{data.country.name}</h2><p className="subtitle"><code>{data.country.code}</code></p></div>
      <p><strong>{data.package.name} · {data.package.type === 'custom' ? 'Custom' : 'Built-in'} · {canEdit ? 'Editable source' : 'Read-only'}</strong></p>
      {canEdit && !editing && !populationEditing && <button type="button" disabled={pending} onClick={() => { setEditing(true); setDeleteReview(null); setSuccess(''); setWriteError(null) }}>{cs ? 'Upravit zemi' : 'Edit country'}</button>}
      {canEdit && !editing && !populationEditing && <button type="button" disabled={pending} onClick={() => {
        if (!data) return
        setDeleteReview({worldId, countryCode, locationKey, fingerprint: data.package.fingerprint, countryName: data.country.name})
        setWriteError(null)
      }}>{cs ? 'Smazat zemi' : 'Delete country'}</button>}
      {canEdit && deleteReview && !editing && !populationEditing && <SectionCard
        title={`${cs ? 'Smazat' : 'Delete'} ${deleteReview.countryCode} — ${deleteReview.countryName}?`}>
        <p>{cs
          ? 'Země bude odstraněna pouze z upravitelné kopie World Package; uložené Runy se nezmění.'
          : 'Only the editable World Package copy will change; existing Runs remain unchanged.'}</p>
        <p><strong>World Package:</strong> <code>{deleteReview.worldId}</code> · <strong>{cs ? 'Země' : 'Country'}:</strong> <code>{deleteReview.countryCode}</code></p>
        <p><strong>{cs ? 'Zkontrolovaný fingerprint' : 'Reviewed fingerprint'}:</strong> <code>{deleteReview.fingerprint}</code></p>
        {data.package.fingerprint !== deleteReview.fingerprint && <p className="error" role="alert">
          {cs ? 'Balíček se od otevření potvrzení změnil. Smazání bylo zablokováno.' :
            'The package has changed since deletion was reviewed. Deletion is blocked.'}
        </p>}
        <p><button type="button" disabled={pending || isFingerprintConflict(writeError) || data.package.fingerprint !== deleteReview.fingerprint}
          onClick={() => {
            if (!deleteReview || pending || isFingerprintConflict(writeError)) return
            if (deleteReview.worldId !== worldId || deleteReview.countryCode !== countryCode ||
                deleteReview.locationKey !== locationKey || deleteReview.fingerprint !== data.package.fingerprint) {
              setWriteError({status: 409, message: 'World Package changed after deletion review.'})
              return
            }
            if (!window.confirm(cs ? 'Opravdu smazat zkontrolovanou zemi?' : 'Delete the reviewed country?')) return
            deleteMutation.mutate(deleteReview)
          }}>{cs ? 'Potvrdit smazání' : 'Confirm deletion'}</button>{' '}
          <button type="button" disabled={pending} onClick={() => setDeleteReview(null)}>
            {cs ? 'Zrušit' : 'Cancel'}
          </button></p>
      </SectionCard>}
      {success && <p className="status" role="status">{success}</p>}
      {reloadError != null && <p className="error" role="alert">{cs ? 'Načtení aktuálních údajů selhalo. Rozpracovaný návrh zůstal zachován: ' : 'Reload failed. Your existing draft has been preserved: '}{formatApiError(reloadError)}</p>}
      {writeError != null && <p className="error" role="alert">{scopeMismatch
        ? (cs ? 'Server vrátil údaje pro jinou zemi nebo World Package. Odpověď nebyla použita; načtěte aktuální stav.' :
            'The server returned a different Country or World Package. The response was rejected; reload current data.')
        : isFingerprintConflict(writeError)
          ? (cs ? 'World Package se mezitím změnil. Nic nebylo znovu odesláno. Načtěte aktuální stav a zkontrolujte změny znovu.' : 'The World Package changed meanwhile. No write was retried. Reload current data and review your edits again.')
          : formatApiError(writeError)}{' '}
        {isFingerprintConflict(writeError) && <button type="button" disabled={pending} onClick={() => void reloadAfterConflict()}>{cs ? 'Načíst aktuální data' : 'Reload current data'}</button>}
      </p>}
      {canEdit && editing && <CountryEditForm key={routeKey} detail={data} geography={geographyQuery.data} saving={pending} blocked={isFingerprintConflict(writeError)} cs={cs}
        onCancel={() => { if (window.confirm(cs ? 'Zahodit rozpracovanou úpravu?' : 'Discard unsaved changes?')) setEditing(false) }}
        onSave={handleCountrySave} />}
      {!editing && <SectionCard title="Overview">
        <DetailRow label="Package" value={data.package.name} /><DetailRow label="Region" value={data.region?.name ?? data.country.region} /><DetailRow label="Travel Region" value={data.travel_region?.name ?? data.country.travel_region ?? '—'} /><DetailRow label="Timezone Area" value={data.timezone_area?.name ?? data.country.timezone_area ?? 'Not assigned'} /><DetailRow label="Area" value={`${formatNumber(data.country.area_km2)} km²`} /><DetailRow label="Current/default population" value={formatNumber(data.country.default_population ?? data.country.population)} />
        {data.country.notes && <DetailRow label="Notes" value={data.country.notes} />}
      </SectionCard>}
      {!populationEditing && <SectionCard title="Population">
        {canEdit && !editing && <button type="button" disabled={pending} onClick={() => { setPopulationEditing(true); setDeleteReview(null); setSuccess(''); setWriteError(null) }}>{cs ? 'Upravit populaci' : 'Edit population'}</button>}
        <DetailRow label="Effective/default population" value={formatNumber(data.country.default_population ?? data.country.population)} /><DetailRow label="Default authored year" value={data.country.default_population_year ?? '—'} /><DetailRow label="Authored population years" value={timeline.length} /><DetailRow label="Earliest authored year" value={timeline[0]?.[0] ?? '—'} /><DetailRow label="Latest authored year" value={timeline[timeline.length - 1]?.[0] ?? '—'} />
        <div style={{maxHeight: '28rem', overflowY: 'auto'}}><table aria-label="Authored population timeline"><thead><tr><th>Year</th><th>Population</th></tr></thead><tbody>{timeline.map(([year, value]) => <tr key={year}><td>{year}{year === '2020' ? ' · Default year' : ''}</td><td>{formatNumber(value)}</td></tr>)}</tbody></table></div>
      </SectionCard>}
      {canEdit && populationEditing && <PopulationEditForm key={routeKey} detail={data} saving={pending} blocked={isFingerprintConflict(writeError)} cs={cs}
        onCancel={() => { if (window.confirm(cs ? 'Zahodit rozpracovanou úpravu?' : 'Discard unsaved changes?')) setPopulationEditing(false) }}
        onSave={handlePopulationSave} />}
      <SectionCard title="Geography"><DetailRow label="Area km²" value={formatNumber(data.country.area_km2)} /><DetailRow label="Region" value={data.region ? `${data.region.name} (${data.region.code})` : data.country.region} /><DetailRow label="Continent" value={data.continent?.name ?? '—'} /><DetailRow label="Travel Region" value={data.travel_region ? `${data.travel_region.name} (${data.travel_region.code})` : data.country.travel_region ?? '—'} /></SectionCard>
      <SectionCard title="Squash / Country strength">
        <DetailRow label="Squash Popularity" value={data.country.squash_popularity} /><DetailRow label="Squash Access" value={data.country.squash_access} /><DetailRow label="Development Quality" value={data.country.development_quality} /><DetailRow label="Competition Quality" value={data.country.competition_quality} /><DetailRow label="Elite Support" value={data.country.elite_support} /><DetailRow label="Squash Tradition" value={data.country.squash_tradition} />
      </SectionCard>
      <details><summary>Technical source</summary><code>{data.source_path}</code></details>
    </>}
  </section>
}

type PopulationRow = { year: string, population: string }
function PopulationEditForm({ detail, saving, blocked, cs, onCancel, onSave }: {
  detail: WorldPackageCountryDetail; saving: boolean; blocked: boolean; cs: boolean; onCancel: () => void;
  onSave: (payload: WorldPackageCountryPopulationUpdatePayload) => void
}): JSX.Element {
  const [baseline] = useState(detail)
  const initial = Object.entries(baseline.country.population_by_year ?? {}).filter((entry): entry is [string, number] => entry[1] != null).map(([year, population]) => ({ year, population: String(population) }))
  const [rows, setRows] = useState<PopulationRow[]>(initial)
  const [newYear, setNewYear] = useState('')
  const [newPopulation, setNewPopulation] = useState('')
  const [validationError, setValidationError] = useState('')
  const [review, setReview] = useState<{ payload: WorldPackageCountryPopulationUpdatePayload; changes: ReviewChange[] } | null>(null)
  const sorted = [...rows].sort((a, b) => Number(a.year) - Number(b.year))
  const add = () => {
    try {
      const year = parseInteger(newYear, cs ? 'Rok' : 'Year', cs, 1955, 2050)
      const population = parseInteger(newPopulation, cs ? 'Populace' : 'Population', cs, 1)
      if (rows.some(row => Number(row.year) === year)) throw new Error(cs ? `Rok ${year} už existuje.` : `Year ${year} is already authored.`)
      setRows(current => [...current, { year: String(year), population: String(population) }])
      setNewYear(''); setNewPopulation(''); setValidationError('')
    } catch (error) { setValidationError(formatApiError(error)) }
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    try {
      if (newYear.trim() || newPopulation.trim()) throw new Error(cs ? 'Nejdříve přidejte rozepsaný rok nebo obě pole vymažte.' : 'Add the pending year first, or clear both new-year fields.')
      const values_by_year = parsePopulations(rows, cs)
      const changes = populationChanges(baseline.country.population_by_year, values_by_year)
      setReview({ payload: { values_by_year, expected_package_fingerprint: baseline.package.fingerprint }, changes })
      setValidationError('')
    } catch (error) { setValidationError(formatApiError(error)) }
  }
  return <SectionCard title={cs ? 'Populační historie' : 'Population'}>
    <p><strong>World Package: <code>{baseline.package.world_id}</code> · {cs ? 'Země' : 'Country'}: <code>{baseline.country.code}</code></strong></p>
    {(validationError) && <p className="error" role="alert">{validationError}</p>}
    {review ? <ConfirmWorldPackageChanges title={cs ? 'Kontrola změn populace' : 'Review population changes'}
      worldId={baseline.package.world_id} countryCode={baseline.country.code} fingerprint={baseline.package.fingerprint}
      changes={review.changes} saving={saving} locked={blocked} cs={cs} onBack={() => setReview(null)} onConfirm={() => onSave(review.payload)} />
      : <form onSubmit={submit}>
        <fieldset disabled={saving || blocked}><p><strong>{cs ? 'Výchozí rok: 2020' : 'Default year: 2020'}</strong></p>
          <table aria-label="Edit authored population timeline"><thead><tr><th>{cs ? 'Rok' : 'Year'}</th><th>{cs ? 'Populace' : 'Population'}</th><th /></tr></thead>
            <tbody>{sorted.map(row => <tr key={row.year}><td>{row.year}{row.year === '2020' ? ' · Default year' : ''}</td>
              <td><input aria-label={`Population ${row.year}`} type="number" min="1" step="1" required value={row.population} onChange={event => setRows(current => current.map(item => item.year === row.year ? {...item, population: event.target.value} : item))} /></td>
              <td>{row.year !== '2020' && <button type="button" onClick={() => setRows(current => current.filter(item => item.year !== row.year))}>{cs ? 'Odebrat' : 'Remove'} {row.year}</button>}</td></tr>)}</tbody></table>
          <fieldset><legend>{cs ? 'Přidat rok' : 'Add authored year'}</legend>
            <label>{cs ? 'Rok' : 'Year'}<input aria-label="New population year" type="number" min="1955" max="2050" step="1" value={newYear} onChange={event => setNewYear(event.target.value)} /></label>
            <label>{cs ? 'Populace' : 'Population'}<input aria-label="New population value" type="number" min="1" step="1" value={newPopulation} onChange={event => setNewPopulation(event.target.value)} /></label>
            <button type="button" onClick={add}>{cs ? '+ Přidat rok' : '+ Add authored year'}</button>
          </fieldset>
          <p><button type="submit">{cs ? 'Zkontrolovat změny' : 'Review changes'}</button>{' '}
            <button type="button" onClick={onCancel}>{cs ? 'Zrušit' : 'Cancel'}</button></p>
        </fieldset>
      </form>}
  </SectionCard>
}

function CountryEditForm({ detail, geography, saving, blocked, cs, onCancel, onSave }: {
  detail: WorldPackageCountryDetail; geography?: WorldPackageGeography; saving: boolean; blocked: boolean; cs: boolean;
  onCancel: () => void; onSave: (payload: WorldPackageCountryUpdatePayload) => void
}): JSX.Element {
  const [baseline] = useState(detail)
  const country = baseline.country
  const scale = country.rating_scale === 'country_ratings_1_10.v2' ? 'country_ratings_1_10.v2' : 'country_ratings_1_5.v1'
  const ratingMaximum = scale === 'country_ratings_1_10.v2' ? 10 : 5
  const [name, setName] = useState(country.name)
  const [notes, setNotes] = useState(country.notes ?? '')
  const [area, setArea] = useState(country.area_km2 == null ? '' : String(country.area_km2))
  const [region, setRegion] = useState(country.region)
  const [travelRegion, setTravelRegion] = useState(country.travel_region ?? '')
  const [timezoneArea, setTimezoneArea] = useState(country.timezone_area ?? '')
  const [values, setValues] = useState({
    squash_popularity: String(country.squash_popularity), squash_access: String(country.squash_access),
    development_quality: String(country.development_quality), competition_quality: String(country.competition_quality),
    elite_support: String(country.elite_support), squash_tradition: String(country.squash_tradition)
  })
  const [validationError, setValidationError] = useState('')
  const [review, setReview] = useState<{ payload: WorldPackageCountryUpdatePayload; changes: ReviewChange[] } | null>(null)
  const submit = (event: FormEvent) => {
    event.preventDefault()
    try {
      const payload: WorldPackageCountryUpdatePayload = {
        rating_scale: scale,
        name: requiredName(name, cs ? 'Název' : 'Name', cs),
        notes: notes.trim() ? notes : null,
        area_km2: parseInteger(area, cs ? 'Plocha' : 'Area', cs, 1, undefined, true),
        region: requiredName(region, cs ? 'Region' : 'Region', cs),
        travel_region: travelRegion || null, timezone_area: timezoneArea || null,
        squash_popularity: parseRating(values.squash_popularity, 'Squash Popularity', cs, scale),
        squash_access: parseRating(values.squash_access, 'Squash Access', cs, scale),
        development_quality: parseRating(values.development_quality, 'Development Quality', cs, scale),
        competition_quality: parseRating(values.competition_quality, 'Competition Quality', cs, scale),
        elite_support: parseRating(values.elite_support, 'Elite Support', cs, scale),
        squash_tradition: parseRating(values.squash_tradition, 'Squash Tradition', cs, scale),
        court_count: country.court_count,
        expected_package_fingerprint: baseline.package.fingerprint
      }
      if (geography && !geography.regions.some(item => item.code === payload.region)) throw new Error(cs ? 'Region není v registru zemí.' : 'Region is not in the geography registry.')
      if (geography && payload.travel_region && !geography.travel_regions.some(item => item.code === payload.travel_region)) throw new Error(cs ? 'Cestovní region není v registru.' : 'Travel Region is not in the registry.')
      if (geography && payload.timezone_area && !geography.timezone_areas.some(item => item.code === payload.timezone_area)) throw new Error(cs ? 'Časová oblast není v registru.' : 'Timezone Area is not in the registry.')
      const fields = ['name','notes','area_km2','region','travel_region','timezone_area','squash_popularity','squash_access','development_quality','competition_quality','elite_support','squash_tradition'] as const
      setReview({payload, changes: fieldChanges(country, payload, fields)})
      setValidationError('')
    } catch (error) { setValidationError(formatApiError(error)) }
  }
  const numeric = (key: keyof typeof values, label: string) => <label>{label}<input type="number" required min={1} max={ratingMaximum} step={scale === 'country_ratings_1_10.v2' ? 0.1 : 'any'} value={values[key]} onChange={event => setValues(current => ({ ...current, [key]: event.target.value }))} /></label>
  return <SectionCard title={cs ? 'Upravit zemi' : 'Edit country'}>
    {validationError && <p className="error" role="alert">{validationError}</p>}
    {review ? <ConfirmWorldPackageChanges title={cs ? 'Kontrola změn země' : 'Review country changes'}
      worldId={baseline.package.world_id} countryCode={country.code} fingerprint={baseline.package.fingerprint}
      changes={review.changes} saving={saving} locked={blocked} cs={cs} onBack={() => setReview(null)} onConfirm={() => onSave(review.payload)} />
      : <form onSubmit={submit}><fieldset disabled={saving || blocked}>
        <label>{cs ? 'Název' : 'Name'}<input required value={name} onChange={event => setName(event.target.value)} /></label>
        <label>{cs ? 'Poznámky' : 'Notes'}<textarea value={notes} onChange={event => setNotes(event.target.value)} /></label>
        <label>{cs ? 'Plocha km²' : 'Area km²'}<input type="number" min="1" step="1" value={area} onChange={event => setArea(event.target.value)} /></label>
        <label>Region<select required value={region} onChange={event => setRegion(event.target.value)}><option value="">{cs ? 'Vyberte region' : 'Select region'}</option>{geography?.regions.map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
        <label>Travel Region<select value={travelRegion} onChange={event => setTravelRegion(event.target.value)}><option value="">{cs ? 'Žádný' : 'None'}</option>{geography?.travel_regions.map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
        <label>Timezone Area<select value={timezoneArea} onChange={event => setTimezoneArea(event.target.value)}><option value="">{cs ? 'Nepřiřazeno' : 'Not assigned'}</option>{(geography?.timezone_areas ?? []).map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
        {numeric('squash_popularity', 'Squash Popularity')}{numeric('squash_access', 'Squash Access')}
        {numeric('development_quality', 'Development Quality')}{numeric('competition_quality', 'Competition Quality')}
        {numeric('elite_support', 'Elite Support')}{numeric('squash_tradition', 'Squash Tradition')}
        <p>{country.rating_history && <span>{cs ? 'Historické ratingy vyžadují rok a podklady; použijte import/API. ' : 'Historical ratings require an explicit year and evidence; edit the versioned history through import/API. '}</span>}
          <button type="submit" disabled={Boolean(country.rating_history)}>{cs ? 'Zkontrolovat změny' : 'Review changes'}</button>{' '}
          <button type="button" onClick={onCancel}>{cs ? 'Zrušit' : 'Cancel'}</button>
        </p>
      </fieldset></form>}
  </SectionCard>
}
