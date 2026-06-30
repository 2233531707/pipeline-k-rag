export const DEFAULT_SIDEBAR_WIDTH = 252
export const MIN_SIDEBAR_WIDTH = 220
export const MAX_SIDEBAR_WIDTH = 360

export const normalizeSidebarWidth = (width, viewportWidth = Number.POSITIVE_INFINITY) => {
  const numericWidth = Number(width)
  const viewportMax = Number.isFinite(viewportWidth)
    ? Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, viewportWidth - 320))
    : MAX_SIDEBAR_WIDTH
  const maxWidth = Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, viewportMax))
  if (!Number.isFinite(numericWidth)) return DEFAULT_SIDEBAR_WIDTH
  return Math.round(Math.min(maxWidth, Math.max(MIN_SIDEBAR_WIDTH, numericWidth)))
}

export const isNavItemActive = (item, route) => {
  const activePaths = item.activePaths || [item.path.split('?')[0]]
  const pathActive = activePaths.some(
    (path) => route.path === path || route.path.startsWith(`${path}/`)
  )
  if (!pathActive || !item.activeTabs) return pathActive
  const activeTab = typeof route.query?.tab === 'string' ? route.query.tab : 'knowledge'
  return item.activeTabs.includes(activeTab)
}

export const resolveRouterLinkActiveClass = (item) => (item.action || item.activeTabs ? '' : 'active')
