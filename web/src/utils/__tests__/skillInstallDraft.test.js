import assert from 'node:assert/strict'

import { buildSkillDraftConfirmation } from '../skillInstallDraft.js'

const shareConfig = {
  access_level: 'global',
  department_ids: [],
  user_uids: []
}

const remoteDraft = {
  source_type: 'remote',
  items: [{ slug: 'remote-skill', source_type: 'remote' }]
}

const unconfirmed = buildSkillDraftConfirmation(remoteDraft, shareConfig, false)
assert.equal(unconfirmed.isRemote, true)
assert.equal(unconfirmed.canConfirm, false)
assert.deepEqual(unconfirmed.payload, {
  share_config: shareConfig,
  high_risk_confirmed: false
})

const confirmed = buildSkillDraftConfirmation(remoteDraft, shareConfig, true)
assert.equal(confirmed.isRemote, true)
assert.equal(confirmed.canConfirm, true)
assert.deepEqual(confirmed.payload, {
  share_config: shareConfig,
  high_risk_confirmed: true
})

const uploadDraft = buildSkillDraftConfirmation({ source_type: 'upload' }, shareConfig, false)
assert.equal(uploadDraft.isRemote, false)
assert.equal(uploadDraft.canConfirm, true)
assert.equal(uploadDraft.payload.high_risk_confirmed, false)

console.log('skillInstallDraft: all assertions passed')
