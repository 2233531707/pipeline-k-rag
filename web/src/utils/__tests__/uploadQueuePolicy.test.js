import assert from 'node:assert/strict'

import { MAX_UPLOAD_CONCURRENCY, resolveUploadRetryDelayMs } from '../uploadQueuePolicy.js'

assert.equal(MAX_UPLOAD_CONCURRENCY, 4)
assert.equal(resolveUploadRetryDelayMs(429, '3'), 3000)
assert.equal(resolveUploadRetryDelayMs(429, null), 2000)
assert.equal(resolveUploadRetryDelayMs(400, '3'), null)

console.log('uploadQueuePolicy: all assertions passed')
