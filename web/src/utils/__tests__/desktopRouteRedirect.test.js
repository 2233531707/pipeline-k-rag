import assert from 'node:assert/strict'

import { resolveDesktopRouteRedirect } from '../desktopRouteRedirect.js'

assert.equal(
  resolveDesktopRouteRedirect({
    toPath: '/',
    isWebOnly: true,
    isLoggedIn: true,
    hasConfiguredBackendUrl: true
  }),
  '/agent'
)

assert.equal(
  resolveDesktopRouteRedirect({
    toPath: '/',
    isWebOnly: true,
    isLoggedIn: false,
    hasConfiguredBackendUrl: true
  }),
  '/login'
)

assert.equal(
  resolveDesktopRouteRedirect({
    toPath: '/login',
    isWebOnly: false,
    isLoggedIn: true,
    hasConfiguredBackendUrl: true
  }),
  '/agent'
)

assert.equal(
  resolveDesktopRouteRedirect({
    toPath: '/connect',
    isWebOnly: false,
    isLoggedIn: false,
    hasConfiguredBackendUrl: false
  }),
  null
)

assert.equal(
  resolveDesktopRouteRedirect({
    toPath: '/extensions',
    isWebOnly: false,
    isLoggedIn: false,
    hasConfiguredBackendUrl: false
  }),
  '/connect'
)

assert.equal(
  resolveDesktopRouteRedirect({
    toPath: '/auth/oidc/callback',
    isWebOnly: true,
    isLoggedIn: false,
    hasConfiguredBackendUrl: true
  }),
  '/login'
)

console.log('desktopRouteRedirect: all assertions passed')
