import assert from 'node:assert/strict'

import {
  buildPendingAttachmentRequest,
  markThreadAttachmentsRequestId
} from '../threadAttachments.js'

const run = () => {
  const pendingAttachments = [
    { file_id: 'file-1', file_name: 'report.md' },
    { file_id: 'file-2', file_name: 'chart.png' },
    { file_id: 'file-1', file_name: 'report.md' },
    { file_id: '', file_name: 'invalid.txt' },
    null
  ]

  const request = buildPendingAttachmentRequest(pendingAttachments)

  assert.deepEqual(request.fileIds, ['file-1', 'file-2'])
  assert.deepEqual(request.attachments, [
    { file_id: 'file-1', file_name: 'report.md' },
    { file_id: 'file-2', file_name: 'chart.png' },
    { file_id: 'file-1', file_name: 'report.md' }
  ])

  const previousAttachments = [
    { file_id: 'file-1', file_name: 'report.md' },
    { file_id: 'file-2', file_name: 'chart.png', request_id: 'old-request' },
    { file_id: 'file-3', file_name: 'notes.txt' }
  ]

  const nextAttachments = markThreadAttachmentsRequestId(
    previousAttachments,
    request.attachments,
    'req-123'
  )

  assert.deepEqual(nextAttachments, [
    { file_id: 'file-1', file_name: 'report.md', request_id: 'req-123' },
    { file_id: 'file-2', file_name: 'chart.png', request_id: 'req-123' },
    { file_id: 'file-3', file_name: 'notes.txt' }
  ])

  assert.deepEqual(markThreadAttachmentsRequestId(previousAttachments, [], 'req-123'), previousAttachments)

  console.log('threadAttachments: all assertions passed')
}

run()
