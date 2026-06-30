export const clearParsedAttachmentState = {
  parsedObjectName: null,
  parsedMinioUrl: null,
  truncated: false,
  parseMethod: null
}

export const resetTmpAttachmentOcrHealthStatus = (ocrMethodKeys) =>
  Object.fromEntries(
    (Array.isArray(ocrMethodKeys) ? ocrMethodKeys : []).map((method) => [
      method,
      { status: 'unknown', message: '' }
    ])
  )

export const shouldApplyTmpAttachmentModalSessionResult = ({
  open,
  requestSeq,
  activeRequestSeq
}) => Boolean(open) && Number(requestSeq) === Number(activeRequestSeq)

export const shouldApplyTmpAttachmentOcrHealthResult = (payload) =>
  shouldApplyTmpAttachmentModalSessionResult(payload)

export const getDefaultParseMethod = (parseMethods) => {
  return Array.isArray(parseMethods) && parseMethods.length ? parseMethods[0] : null
}

export const resolveTmpAttachmentSelectedParseMethod = ({
  parseMethods,
  selectedParseMethod,
  isUnavailableMethod
}) => {
  if (!Array.isArray(parseMethods) || parseMethods.length === 0) return null

  const isUnavailable = (method) => Boolean(isUnavailableMethod?.(method))
  const firstAvailableMethod = parseMethods.find((method) => !isUnavailable(method)) || null
  const hasSelectedMethod = parseMethods.includes(selectedParseMethod)

  if (!selectedParseMethod) return firstAvailableMethod
  if (!hasSelectedMethod) return firstAvailableMethod
  if (isUnavailable(selectedParseMethod) && firstAvailableMethod) return firstAvailableMethod

  return selectedParseMethod
}

export const patchTmpAttachmentParseMethodChange = (item, selectedParseMethod) => ({
  ...clearParsedAttachmentState,
  selectedParseMethod,
  parseError: null,
  status: item?.status === 'parsed' ? 'uploaded' : item?.status
})

export const isTmpAttachmentParseDisabled = ({ item, confirming, isUnavailableMethod }) => {
  return (
    item?.status === 'parsing' ||
    !item?.selectedParseMethod ||
    Boolean(confirming) ||
    Boolean(isUnavailableMethod?.(item.selectedParseMethod))
  )
}
