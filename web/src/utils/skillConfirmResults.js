export function summarizeSkillConfirmResults(results) {
  const normalized = Array.isArray(results) ? results : []
  const successCount = normalized.filter((item) => item?.success).length
  const failedItems = normalized.filter((item) => !item?.success)
  const firstError = failedItems.find((item) => item?.error)?.error || null

  return {
    successCount,
    failedCount: failedItems.length,
    firstError
  }
}
