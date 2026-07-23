import {
  viewerHomePath,
  viewerRankingsPath,
  viewerTopCountriesPath,
  viewerTopPlayersPath,
  viewerTopTourPath
} from './viewerRoutes'

export type ModeSwitcherIdentityContext = {
  activeProductRunId: string | null
  activeLegacySimulationRunId: string | null
}

function safeDecodePathSegment(segment: string): string {
  try {
    return decodeURIComponent(segment)
  } catch {
    return segment
  }
}

export function getModeSwitcherTarget(
  pathname: string,
  identityContext?: ModeSwitcherIdentityContext
): { viewerTarget: string; adminTarget: string } {
  const viewerRunMatch = pathname.match(/^\/viewer\/runs\/([^/]+)(?:\/|$)/)
  if (viewerRunMatch) {
    const productRunId = safeDecodePathSegment(viewerRunMatch[1])
    return {
      viewerTarget: pathname,
      adminTarget: `/admin/runs/${encodeURIComponent(productRunId)}/branches`
    }
  }

  const adminBranchesMatch = pathname.match(/^\/admin\/runs\/([^/]+)\/branches$/)
  if (adminBranchesMatch) {
    const productRunId = safeDecodePathSegment(adminBranchesMatch[1])
    return {
      viewerTarget: viewerRankingsPath(productRunId),
      adminTarget: pathname
    }
  }

  const legacyAdminRunMatch = pathname.match(/^\/admin\/runs\/([^/]+)(?:\/|$)/)
  if (legacyAdminRunMatch) {
    const legacySimulationRunId = safeDecodePathSegment(legacyAdminRunMatch[1])
    const activeProductRunId = identityContext?.activeProductRunId
    const activeLegacySimulationRunId = identityContext?.activeLegacySimulationRunId
    const hasExactActiveMatch = Boolean(
      activeProductRunId?.trim() &&
      activeLegacySimulationRunId?.trim() &&
      legacySimulationRunId === activeLegacySimulationRunId
    )
    return {
      viewerTarget: hasExactActiveMatch ? viewerRankingsPath(activeProductRunId!) : '/viewer/runs',
      adminTarget: pathname
    }
  }

  const mappings: Record<string, { viewerTarget: string; adminTarget: string }> = {
    [viewerHomePath()]: { viewerTarget: viewerHomePath(), adminTarget: '/admin' },
    '/admin': { viewerTarget: viewerHomePath(), adminTarget: '/admin' },
    [viewerTopPlayersPath()]: { viewerTarget: viewerTopPlayersPath(), adminTarget: '/admin/players' },
    '/admin/players': { viewerTarget: viewerTopPlayersPath(), adminTarget: '/admin/players' },
    [viewerTopCountriesPath()]: { viewerTarget: viewerTopCountriesPath(), adminTarget: '/admin/world/countries' },
    '/admin/world/countries': { viewerTarget: viewerTopCountriesPath(), adminTarget: '/admin/world/countries' },
    [viewerTopTourPath()]: { viewerTarget: viewerTopTourPath(), adminTarget: '/admin/tour-seasons' },
    '/admin/tour-seasons': { viewerTarget: viewerTopTourPath(), adminTarget: '/admin/tour-seasons' }
  }

  if (mappings[pathname]) return mappings[pathname]
  if (pathname.startsWith('/viewer')) return { viewerTarget: pathname, adminTarget: '/admin' }
  if (pathname.startsWith('/admin')) return { viewerTarget: viewerHomePath(), adminTarget: pathname }
  return { viewerTarget: viewerHomePath(), adminTarget: '/admin' }
}
