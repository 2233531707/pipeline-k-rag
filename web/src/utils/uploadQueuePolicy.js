export const MAX_UPLOAD_CONCURRENCY = 4

export const resolveUploadRetryDelayMs = (status, retryAfter) => {
  if (status !== 429) {
    return null
  }

  const seconds = Number.parseInt(retryAfter || '', 10)
  return (Number.isFinite(seconds) && seconds > 0 ? seconds : 2) * 1000
}
