export function resolveDesktopRouteRedirect({
  toPath,
  isWebOnly,
  isLoggedIn,
  hasConfiguredBackendUrl
}) {
  if (!hasConfiguredBackendUrl && toPath !== '/connect') {
    return '/connect'
  }

  if (toPath === '/') {
    return isLoggedIn ? '/agent' : '/login'
  }

  if (toPath === '/login' && isLoggedIn) {
    return '/agent'
  }

  if (isWebOnly) {
    return '/login'
  }

  return null
}
