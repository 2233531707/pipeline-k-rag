import assert from 'node:assert/strict'

import {
  DEFAULT_SIDEBAR_WIDTH,
  MAX_SIDEBAR_WIDTH,
  MIN_SIDEBAR_WIDTH,
  isNavItemActive,
  normalizeSidebarWidth,
  resolveRouterLinkActiveClass
} from '../sidebarNav.js'

const extensionsItem = {
  path: '/extensions?tab=skills',
  activePaths: ['/extensions'],
  activeTabs: ['skills', 'tools', 'mcp']
}

const knowledgeItem = {
  path: '/extensions?tab=knowledge',
  activePaths: ['/extensions'],
  activeTabs: ['knowledge']
}

assert.equal(isNavItemActive(extensionsItem, { path: '/extensions', query: { tab: 'skills' } }), true)
assert.equal(isNavItemActive(knowledgeItem, { path: '/extensions', query: { tab: 'skills' } }), false)

assert.equal(isNavItemActive(extensionsItem, { path: '/extensions', query: { tab: 'knowledge' } }), false)
assert.equal(isNavItemActive(knowledgeItem, { path: '/extensions', query: { tab: 'knowledge' } }), true)

assert.equal(resolveRouterLinkActiveClass({ action: true }), '')
assert.equal(resolveRouterLinkActiveClass(extensionsItem), '')
assert.equal(resolveRouterLinkActiveClass(knowledgeItem), '')
assert.equal(resolveRouterLinkActiveClass({ path: '/workspace' }), 'active')

assert.equal(normalizeSidebarWidth(100), MIN_SIDEBAR_WIDTH)
assert.equal(normalizeSidebarWidth(999), MAX_SIDEBAR_WIDTH)
assert.equal(normalizeSidebarWidth('bad'), DEFAULT_SIDEBAR_WIDTH)
assert.equal(normalizeSidebarWidth(300, 500), MIN_SIDEBAR_WIDTH)
assert.equal(normalizeSidebarWidth(300, 720), 300)

console.log('sidebarNav tests passed')
