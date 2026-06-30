export const buildPendingAttachmentRequest = (attachments) => {
  const normalizedAttachments = Array.isArray(attachments)
    ? attachments.filter((attachment) => {
        const fileId = String(attachment?.file_id || '').trim()
        return Boolean(fileId)
      })
    : []

  const fileIds = []
  const seen = new Set()

  normalizedAttachments.forEach((attachment) => {
    const fileId = String(attachment.file_id).trim()
    if (seen.has(fileId)) return
    seen.add(fileId)
    fileIds.push(fileId)
  })

  return {
    attachments: normalizedAttachments,
    fileIds
  }
}

export const markThreadAttachmentsRequestId = (threadAttachments, pendingAttachments, requestId) => {
  if (!Array.isArray(threadAttachments) || !threadAttachments.length) return threadAttachments || []
  if (!Array.isArray(pendingAttachments) || !pendingAttachments.length || !requestId) {
    return threadAttachments
  }

  const fileIds = new Set(
    pendingAttachments
      .map((attachment) => String(attachment?.file_id || '').trim())
      .filter(Boolean)
  )

  if (!fileIds.size) return threadAttachments

  return threadAttachments.map((attachment) =>
    fileIds.has(String(attachment?.file_id || '').trim())
      ? { ...attachment, request_id: requestId }
      : attachment
  )
}
