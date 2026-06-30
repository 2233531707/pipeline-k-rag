import assert from 'node:assert/strict'

import {
  clearParsedAttachmentState,
  getDefaultParseMethod,
  isTmpAttachmentParseDisabled,
  patchTmpAttachmentParseMethodChange,
  resetTmpAttachmentOcrHealthStatus,
  shouldApplyTmpAttachmentModalSessionResult,
  shouldApplyTmpAttachmentOcrHealthResult,
  resolveTmpAttachmentSelectedParseMethod
} from '../tmpAttachmentParseState.js'

const run = () => {
  assert.equal(getDefaultParseMethod(['rapid_ocr', 'mineru_ocr']), 'rapid_ocr')
  assert.equal(getDefaultParseMethod([]), null)
  assert.equal(getDefaultParseMethod(null), null)
  assert.equal(
    resolveTmpAttachmentSelectedParseMethod({
      parseMethods: ['rapid_ocr', 'mineru_ocr'],
      selectedParseMethod: '',
      isUnavailableMethod: (method) => method === 'rapid_ocr'
    }),
    'mineru_ocr'
  )
  assert.equal(
    resolveTmpAttachmentSelectedParseMethod({
      parseMethods: ['rapid_ocr', 'mineru_ocr'],
      selectedParseMethod: 'rapid_ocr',
      isUnavailableMethod: (method) => method === 'rapid_ocr'
    }),
    'mineru_ocr'
  )
  assert.equal(
    resolveTmpAttachmentSelectedParseMethod({
      parseMethods: ['rapid_ocr', 'mineru_ocr'],
      selectedParseMethod: 'mineru_ocr',
      isUnavailableMethod: (method) => method === 'rapid_ocr'
    }),
    'mineru_ocr'
  )
  assert.equal(
    resolveTmpAttachmentSelectedParseMethod({
      parseMethods: ['mineru_ocr', 'deepseek_ocr'],
      selectedParseMethod: 'rapid_ocr',
      isUnavailableMethod: () => false
    }),
    'mineru_ocr'
  )
  assert.equal(
    resolveTmpAttachmentSelectedParseMethod({
      parseMethods: ['rapid_ocr'],
      selectedParseMethod: 'rapid_ocr',
      isUnavailableMethod: (method) => method === 'rapid_ocr'
    }),
    'rapid_ocr'
  )
  assert.deepEqual(
    resetTmpAttachmentOcrHealthStatus(['rapid_ocr', 'mineru_ocr']),
    {
      rapid_ocr: { status: 'unknown', message: '' },
      mineru_ocr: { status: 'unknown', message: '' }
    }
  )
  assert.deepEqual(resetTmpAttachmentOcrHealthStatus([]), {})
  assert.equal(
    shouldApplyTmpAttachmentModalSessionResult({
      open: true,
      requestSeq: 5,
      activeRequestSeq: 5
    }),
    true
  )
  assert.equal(
    shouldApplyTmpAttachmentModalSessionResult({
      open: false,
      requestSeq: 5,
      activeRequestSeq: 5
    }),
    false
  )
  assert.equal(
    shouldApplyTmpAttachmentModalSessionResult({
      open: true,
      requestSeq: 4,
      activeRequestSeq: 5
    }),
    false
  )
  assert.equal(
    shouldApplyTmpAttachmentOcrHealthResult({
      open: true,
      requestSeq: 3,
      activeRequestSeq: 3
    }),
    true
  )
  assert.equal(
    shouldApplyTmpAttachmentOcrHealthResult({
      open: false,
      requestSeq: 3,
      activeRequestSeq: 3
    }),
    false
  )
  assert.equal(
    shouldApplyTmpAttachmentOcrHealthResult({
      open: true,
      requestSeq: 2,
      activeRequestSeq: 3
    }),
    false
  )

  assert.deepEqual(clearParsedAttachmentState, {
    parsedObjectName: null,
    parsedMinioUrl: null,
    truncated: false,
    parseMethod: null
  })

  const parsedItem = {
    localId: '1',
    status: 'parsed',
    selectedParseMethod: 'rapid_ocr',
    parsedObjectName: 'tmp/parsed/demo.md',
    parsedMinioUrl: 'https://example.com/demo.md',
    truncated: true,
    parseMethod: 'rapid_ocr',
    parseError: 'old error'
  }

  assert.deepEqual(patchTmpAttachmentParseMethodChange(parsedItem, 'mineru_ocr'), {
    parsedObjectName: null,
    parsedMinioUrl: null,
    truncated: false,
    parseMethod: null,
    selectedParseMethod: 'mineru_ocr',
    parseError: null,
    status: 'uploaded'
  })

  assert.deepEqual(
    patchTmpAttachmentParseMethodChange({ ...parsedItem, status: 'uploaded' }, 'disable'),
    {
      parsedObjectName: null,
      parsedMinioUrl: null,
      truncated: false,
      parseMethod: null,
      selectedParseMethod: 'disable',
      parseError: null,
      status: 'uploaded'
    }
  )

  assert.equal(
    isTmpAttachmentParseDisabled({
      item: { status: 'uploaded', selectedParseMethod: 'rapid_ocr' },
      confirming: false,
      isUnavailableMethod: () => false
    }),
    false
  )

  assert.equal(
    isTmpAttachmentParseDisabled({
      item: { status: 'parsing', selectedParseMethod: 'rapid_ocr' },
      confirming: false,
      isUnavailableMethod: () => false
    }),
    true
  )

  assert.equal(
    isTmpAttachmentParseDisabled({
      item: { status: 'uploaded', selectedParseMethod: '' },
      confirming: false,
      isUnavailableMethod: () => false
    }),
    true
  )

  assert.equal(
    isTmpAttachmentParseDisabled({
      item: { status: 'uploaded', selectedParseMethod: 'rapid_ocr' },
      confirming: true,
      isUnavailableMethod: () => false
    }),
    true
  )

  assert.equal(
    isTmpAttachmentParseDisabled({
      item: { status: 'uploaded', selectedParseMethod: 'rapid_ocr' },
      confirming: false,
      isUnavailableMethod: (method) => method === 'rapid_ocr'
    }),
    true
  )

  console.log('tmpAttachmentParseState: all assertions passed')
}

run()
