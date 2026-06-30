export const normalizeKnowledgePreviewVariants = (variants) => {
  if (!Array.isArray(variants)) return []
  return variants.filter((variant) => variant?.supported !== false && variant?.key)
}

export const canSwitchKnowledgePreviewVariant = ({ currentVariant, nextVariant, variants }) => {
  if (!nextVariant || currentVariant === nextVariant) return false

  return normalizeKnowledgePreviewVariants(variants).some((variant) => variant.key === nextVariant)
}
