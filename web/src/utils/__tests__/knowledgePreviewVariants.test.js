import assert from 'node:assert/strict'

import {
  canSwitchKnowledgePreviewVariant,
  normalizeKnowledgePreviewVariants
} from '../knowledgePreviewVariants.js'

assert.deepEqual(
  normalizeKnowledgePreviewVariants([
    { key: 'parsed', label: 'MD', supported: true },
    { key: 'original', label: 'Source', supported: false },
    { key: '', label: 'Empty', supported: true },
    null
  ]),
  [{ key: 'parsed', label: 'MD', supported: true }]
)

assert.equal(
  canSwitchKnowledgePreviewVariant({
    currentVariant: 'parsed',
    nextVariant: 'original',
    variants: [
      { key: 'parsed', label: 'MD', supported: true },
      { key: 'original', label: 'Source', supported: true }
    ]
  }),
  true
)

assert.equal(
  canSwitchKnowledgePreviewVariant({
    currentVariant: 'parsed',
    nextVariant: 'parsed',
    variants: [{ key: 'parsed', label: 'MD', supported: true }]
  }),
  false
)

assert.equal(
  canSwitchKnowledgePreviewVariant({
    currentVariant: 'parsed',
    nextVariant: 'original',
    variants: [{ key: 'parsed', label: 'MD', supported: true }]
  }),
  false
)

console.log('knowledgePreviewVariants: all assertions passed')
