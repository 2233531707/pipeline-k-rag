import { resolveRemoteAssetUrl } from '../runtime/desktop.js'

export const resolvePreviewAssetUrl = (url) => resolveRemoteAssetUrl(url || '')

export const resolveRenderableAssetUrl = (url) => {
  const value = String(url || '').trim()
  if (!value) return null
  if (value.startsWith('/') || /^(https?:|data:|blob:)/i.test(value)) {
    return resolvePreviewAssetUrl(value)
  }
  return null
}
