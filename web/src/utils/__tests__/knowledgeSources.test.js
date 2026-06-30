import assert from 'node:assert/strict'

import {
  buildKnowledgeSourceGroups,
  buildKnowledgeSourceRouteQuery,
  parseKnowledgeSourceRouteTarget
} from '../knowledgeSources.js'

const groups = buildKnowledgeSourceGroups([
  {
    kb_id: 'kb-a',
    file_id: 'file-a',
    content: '片段 A',
    metadata: {
      source: '同名文档.md',
      chunk_id: 'chunk-a'
    }
  },
  {
    kb_id: 'kb-b',
    file_id: 'file-b',
    content: '片段 B',
    metadata: {
      source: '同名文档.md',
      chunk_id: 'chunk-b'
    }
  }
])

assert.equal(groups.length, 2)
assert.deepEqual(
  groups.map((group) => ({
    kbId: group.kbId,
    fileId: group.fileId,
    filename: group.filename
  })),
  [
    { kbId: 'kb-a', fileId: 'file-a', filename: '同名文档.md' },
    { kbId: 'kb-b', fileId: 'file-b', filename: '同名文档.md' }
  ]
)

assert.deepEqual(
  buildKnowledgeSourceRouteQuery({
    kb_id: 'kb-a',
    file_id: 'file-a',
    metadata: { source: '规范说明.md' }
  }),
  {
    kb_id: 'kb-a',
    file_id: 'file-a',
    variant: 'parsed',
    name: '规范说明.md'
  }
)

assert.deepEqual(
  parseKnowledgeSourceRouteTarget({
    kb_id: 'kb-a',
    file_id: 'file-a',
    variant: 'original',
    name: '规范说明.md'
  }),
  {
    kbId: 'kb-a',
    fileId: 'file-a',
    variant: 'original',
    name: '规范说明.md'
  }
)

assert.deepEqual(
  parseKnowledgeSourceRouteTarget({
    kb_id: 'kb-a',
    file_id: 'file-a',
    variant: 'unsupported-mode',
    name: '规范说明.md'
  }),
  {
    kbId: 'kb-a',
    fileId: 'file-a',
    variant: 'parsed',
    name: '规范说明.md'
  }
)

assert.equal(parseKnowledgeSourceRouteTarget({ kb_id: 'kb-a' }), null)

console.log('knowledgeSources: all assertions passed')
