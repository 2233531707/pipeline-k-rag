export const buildConfirmableTmpAttachments = (fileItems) => {
  if (!Array.isArray(fileItems)) return []
  return fileItems.filter((item) => ['uploaded', 'parsed'].includes(item?.status))
}

export const buildTmpAttachmentConfirmPayload = (fileItems) => {
  return buildConfirmableTmpAttachments(fileItems).map((item) => ({
    file_name: item.fileName,
    file_type: item.fileType,
    bucket_name: item.bucketName,
    object_name: item.objectName,
    parsed_object_name: item.parsedObjectName || null,
    truncated: Boolean(item.truncated)
  }))
}
