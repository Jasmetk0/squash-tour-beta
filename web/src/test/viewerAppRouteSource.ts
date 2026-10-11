export function viewerAppRoutePaths(appSource: string): Set<string> {
  const routes = new Set<string>()

  for (const match of appSource.matchAll(/<Route\s+path="([^"]+)"/g)) {
    const path = match[1]
    if (path.startsWith('viewer')) routes.add(`/${path}`)
  }

  const parentMarker =
    '<Route path="viewer/runs/:runId" element={<ViewerProductRunRouteBoundary />}>'
  const parentStart = appSource.indexOf(parentMarker)
  if (parentStart >= 0) {
    const parentEnd = appSource.indexOf('</Route>', parentStart)
    if (parentEnd < 0) {
      throw new Error('Viewer Product Run route boundary is not closed')
    }
    const parentSource = appSource.slice(parentStart, parentEnd)
    routes.add('/viewer/runs/:runId')
    for (const match of parentSource.matchAll(/<Route\s+path="([^"]+)"/g)) {
      const child = match[1]
      if (child === 'viewer/runs/:runId') continue
      routes.add(`/viewer/runs/:runId/${child}`)
    }
  }

  return routes
}

export function viewerAppRouteExists(
  appSource: string,
  destination: string,
): boolean {
  const destinationSegments = destination.split('/')
  return [...viewerAppRoutePaths(appSource)].some((route) => {
    const routeSegments = route.split('/')
    if (routeSegments.length !== destinationSegments.length) return false
    return routeSegments.every(
      (segment, index) =>
        segment.startsWith(':') || segment === destinationSegments[index],
    )
  })
}
