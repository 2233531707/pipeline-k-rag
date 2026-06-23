import assert from 'node:assert/strict'

import { buildKnowledgeGroupSections } from '../knowledgeGroups.js'

const sections = buildKnowledgeGroupSections(
  [
    { group_id: 'project', name: '项目资料', is_default: false },
    { group_id: 'default', name: '默认分组', is_default: true },
    { group_id: 'empty', name: '空分组', is_default: false }
  ],
  [
    { kb_id: 'kb-1', name: '默认知识库' },
    { kb_id: 'kb-2', name: '项目知识库', group_id: 'project' },
    { kb_id: 'kb-3', name: '未知分组知识库', group_id: 'missing' }
  ]
)

assert.equal(sections[0].group_id, 'default')
assert.deepEqual(
  sections.find((section) => section.group_id === 'default').databases.map((db) => db.kb_id),
  ['kb-1', 'kb-3']
)
assert.deepEqual(
  sections.find((section) => section.group_id === 'project').databases.map((db) => db.kb_id),
  ['kb-2']
)
assert.deepEqual(
  sections.find((section) => section.group_id === 'empty').databases,
  []
)

const nestedSections = buildKnowledgeGroupSections(
  [
    { group_id: 'default', name: '默认分组', is_default: true },
    { group_id: 'project', name: '项目资料', is_default: false },
    {
      group_id: 'project-design',
      name: '设计文档',
      is_default: false,
      parent_group_id: 'project'
    }
  ],
  [{ kb_id: 'kb-4', name: '设计说明', group_id: 'project-design' }]
)

const projectGroup = nestedSections.find((section) => section.group_id === 'project')
assert.equal(projectGroup.children.length, 1)
assert.equal(projectGroup.children[0].group_id, 'project-design')
assert.deepEqual(projectGroup.children[0].databases.map((db) => db.kb_id), ['kb-4'])

const orphanSections = buildKnowledgeGroupSections(
  [
    { group_id: 'default', name: '默认分组', is_default: true },
    { group_id: 'orphan', name: '孤儿分组', is_default: false, parent_group_id: 'missing' }
  ],
  []
)

assert.equal(orphanSections.some((section) => section.group_id === 'orphan'), true)

console.log('knowledgeGroups tests passed')
