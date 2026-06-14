import assert from 'node:assert/strict'

import {
  DEFAULT_ALL_AGENT_RESOURCE_KINDS,
  isDefaultAllAgentResourceKind
} from '../agentConfigUtils.js'

assert.ok(DEFAULT_ALL_AGENT_RESOURCE_KINDS.includes('knowledge_tools'))
assert.equal(isDefaultAllAgentResourceKind('knowledge_tools'), true)

console.log('agentConfigUtils tests passed')
