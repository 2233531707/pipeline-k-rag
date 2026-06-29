import assert from 'node:assert/strict'

import { resolveSkillUploadFile } from '../skillUpload.js'

const rawFile = { name: 'pipeline-plan-auditor-skill.zip', size: 125376 }

assert.equal(resolveSkillUploadFile(rawFile), rawFile)
assert.equal(resolveSkillUploadFile({ originFileObj: rawFile, uid: 'upload-1' }), rawFile)
assert.equal(resolveSkillUploadFile(null), null)

console.log('skillUpload: all assertions passed')
