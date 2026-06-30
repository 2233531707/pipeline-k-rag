const normalizeMetadata = (chunk) =>
  chunk?.metadata && typeof chunk.metadata === 'object' ? chunk.metadata : {}

const buildGroupKey = (chunk) => {
  const metadata = normalizeMetadata(chunk)
  const kbId = String(chunk?.kb_id || metadata.kb_id || '').trim()
  const fileId = String(chunk?.file_id || metadata.file_id || '').trim()
  if (kbId && fileId) return `${kbId}::${fileId}`
  const source = String(metadata.source || '').trim()
  return `${kbId}::${fileId}::${source}`
}

export const buildKnowledgeSourceGroups = (chunks) => {
  if (!Array.isArray(chunks)) return []

  const groups = new Map()
  for (const chunk of chunks) {
    const metadata = normalizeMetadata(chunk)
    const key = buildGroupKey(chunk)
    if (!groups.has(key)) {
      groups.set(key, {
        kbId: String(chunk?.kb_id || metadata.kb_id || '').trim(),
        fileId: String(chunk?.file_id || metadata.file_id || '').trim(),
        filename: String(
          metadata.source || metadata.file_name || metadata.filename || metadata.title || '未知来源'
        ).trim(),
        chunks: []
      })
    }
    groups.get(key).chunks.push(chunk)
  }

  return Array.from(groups.values()).sort((left, right) => {
    if (left.filename !== right.filename) {
      return left.filename.localeCompare(right.filename, 'zh-Hans-CN')
    }
    if (left.kbId !== right.kbId) {
      return left.kbId.localeCompare(right.kbId, 'zh-Hans-CN')
    }
    return left.fileId.localeCompare(right.fileId, 'zh-Hans-CN')
  })
}

export const buildKnowledgeSourceRouteQuery = (chunk) => {
  const metadata = normalizeMetadata(chunk)
  const kbId = String(chunk?.kb_id || metadata.kb_id || '').trim()
  const fileId = String(chunk?.file_id || metadata.file_id || '').trim()
  if (!kbId || !fileId) return null

  const sourceName = String(
    metadata.source || metadata.file_name || metadata.filename || metadata.title || ''
  ).trim()

  return {
    kb_id: kbId,
    file_id: fileId,
    variant: 'parsed',
    ...(sourceName ? { name: sourceName } : {})
  }
}

export const parseKnowledgeSourceRouteTarget = (query) => {
  const kbId = String(query?.kb_id || '').trim()
  const fileId = String(query?.file_id || '').trim()
  if (!kbId || !fileId) return null

  const rawVariant = String(query?.variant || 'parsed').trim() || 'parsed'
  const variant = ['parsed', 'original'].includes(rawVariant) ? rawVariant : 'parsed'
  const name = String(query?.name || '').trim()

  return {
    kbId,
    fileId,
    variant,
    name
  }
}
