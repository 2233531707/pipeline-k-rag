import assert from 'node:assert/strict'

import { summarizeSkillConfirmResults } from '../skillConfirmResults.js'

assert.deepEqual(summarizeSkillConfirmResults(null), {
  successCount: 0,
  failedCount: 0,
  firstError: null
})

assert.deepEqual(
  summarizeSkillConfirmResults([
    { slug: 'ok', success: true },
    { slug: 'bad', success: false, error: '技能目录不存在: skills/pipeline-plan-auditor' }
  ]),
  {
    successCount: 1,
    failedCount: 1,
    firstError: '技能目录不存在: skills/pipeline-plan-auditor'
  }
)

console.log('skillConfirmResults: all assertions passed')
