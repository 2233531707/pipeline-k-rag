import assert from 'node:assert/strict'

import {
  buildConfirmableTmpAttachments,
  buildTmpAttachmentConfirmPayload
} from '../tmpAttachmentConfirm.js'

const run = () => {
  const fileItems = [
    {
      fileName: 'report.pdf',
      fileType: 'application/pdf',
      bucketName: 'knowledgebases',
      objectName: 'tmp/original/report.pdf',
      status: 'uploaded',
      parsedObjectName: null,
      truncated: 0
    },
    {
      fileName: 'image.png',
      fileType: 'image/png',
      bucketName: 'knowledgebases',
      objectName: 'tmp/original/image.png',
      status: 'parsed',
      parsedObjectName: 'tmp/parsed/image.md',
      truncated: 'yes'
    },
    {
      fileName: 'broken.docx',
      fileType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      bucketName: 'knowledgebases',
      objectName: 'tmp/original/broken.docx',
      status: 'error',
      parsedObjectName: 'tmp/parsed/broken.md',
      truncated: true
    },
    {
      fileName: 'loading.txt',
      fileType: 'text/plain',
      bucketName: 'knowledgebases',
      objectName: 'tmp/original/loading.txt',
      status: 'uploading'
    }
  ]

  const confirmableItems = buildConfirmableTmpAttachments(fileItems)
  assert.equal(confirmableItems.length, 2)
  assert.deepEqual(
    confirmableItems.map((item) => item.fileName),
    ['report.pdf', 'image.png']
  )

  assert.deepEqual(buildTmpAttachmentConfirmPayload(fileItems), [
    {
      file_name: 'report.pdf',
      file_type: 'application/pdf',
      bucket_name: 'knowledgebases',
      object_name: 'tmp/original/report.pdf',
      parsed_object_name: null,
      truncated: false
    },
    {
      file_name: 'image.png',
      file_type: 'image/png',
      bucket_name: 'knowledgebases',
      object_name: 'tmp/original/image.png',
      parsed_object_name: 'tmp/parsed/image.md',
      truncated: true
    }
  ])

  console.log('tmpAttachmentConfirm: all assertions passed')
}

run()
