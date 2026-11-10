import {
  confirmATPReference, getATPReferenceCatalog, previewATPReference,
} from '../../api/client'
import { ATP_REFERENCE_SETUP_ID, reviewedATPReference } from '../../api/atpReferencePackages'
import { ATPSourceApplyPage } from './ATPSourceApplyPage'

export function ATPReferenceApplyPage(): JSX.Element {
  return <ATPSourceApplyPage
    queryPrefix="atp-reference"
    setupId={ATP_REFERENCE_SETUP_ID}
    title={{cs: 'ATP Tour 1990–2026 – referenční balíčky', en: 'ATP Tour 1990–2026 – reference packages'}}
    subtitle={{
      cs: 'Historické Category + Series v jednom Setup. Nejde o hratelné ATP turnaje, zápasy, body ani kalendář pro squash.',
      en: 'Historic Category + Series in one Setup. Not playable ATP tournaments, matches, points or a squash calendar.',
    }}
    getCatalog={getATPReferenceCatalog}
    getPreview={previewATPReference}
    confirmReference={confirmATPReference}
    isReviewed={reviewedATPReference}
  />
}
