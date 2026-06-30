import { reactive, readonly } from 'vue'

const desktopBridge = typeof window !== 'undefined' ? window.kbDesktop ?? null : null
export const DESKTOP_BACKEND_CHANGED_EVENT = 'kb-desktop-backend-changed'

const state = reactive({
  initialized: false,
  isDesktop: Boolean(desktopBridge?.isDesktop),
  backendUrl: '',
  defaultBackendUrl: '',
  authToken: ''
})

function trimTrailingSlash(value) {
  return value.replace(/\/+$/, '')
}

export function isDesktopMode() {
  return state.isDesktop
}

export function getDesktopRuntimeState() {
  return readonly(state)
}

export async function initializeDesktopRuntime() {
  if (state.initialized) {
    return state
  }

  if (state.isDesktop && desktopBridge?.getRuntimeState) {
    const runtimeState = await desktopBridge.getRuntimeState()
    state.backendUrl = runtimeState?.backendUrl || ''
    state.defaultBackendUrl = runtimeState?.defaultBackendUrl || ''
    state.authToken = runtimeState?.authToken || ''
  }

  state.initialized = true
  return state
}

export function readPersistedToken() {
  return state.isDesktop ? state.authToken || '' : localStorage.getItem('user_token') || ''
}

export async function persistAuthToken(token) {
  state.authToken = token || ''
  if (state.isDesktop && desktopBridge?.setAuthToken) {
    await desktopBridge.setAuthToken(state.authToken)
    return
  }
  if (token) {
    localStorage.setItem('user_token', token)
  } else {
    localStorage.removeItem('user_token')
  }
}

export async function clearPersistedToken() {
  state.authToken = ''
  if (state.isDesktop && desktopBridge?.clearAuthToken) {
    await desktopBridge.clearAuthToken()
    return
  }
  localStorage.removeItem('user_token')
}

export function getBackendUrl() {
  return state.backendUrl || ''
}

export function hasConfiguredBackendUrl() {
  return Boolean(getBackendUrl())
}

export function normalizeBackendUrl(rawValue) {
  const value = String(rawValue || '').trim()
  if (!value) {
    throw new Error('请输入后端服务器地址')
  }

  let parsedUrl
  try {
    parsedUrl = new URL(value)
  } catch {
    throw new Error('后端服务器地址格式不正确')
  }

  if (!['http:', 'https:'].includes(parsedUrl.protocol)) {
    throw new Error('后端服务器地址必须以 http:// 或 https:// 开头')
  }

  const pathname = trimTrailingSlash(parsedUrl.pathname || '')
  return `${parsedUrl.protocol}//${parsedUrl.host}${pathname}`
}

export async function setConnectionConfig({ backendUrl }) {
  const normalized = normalizeBackendUrl(backendUrl)
  if (state.isDesktop && desktopBridge?.setConnectionConfig) {
    await desktopBridge.setConnectionConfig({ backendUrl: normalized })
  }
  state.backendUrl = normalized
  return normalized
}

export function notifyDesktopBackendChanged(detail = {}) {
  if (typeof window === 'undefined' || typeof window.dispatchEvent !== 'function') return
  window.dispatchEvent(new CustomEvent(DESKTOP_BACKEND_CHANGED_EVENT, { detail }))
}

export function onDesktopBackendChanged(handler) {
  if (typeof window === 'undefined' || typeof window.addEventListener !== 'function') {
    return () => {}
  }
  window.addEventListener(DESKTOP_BACKEND_CHANGED_EVENT, handler)
  return () => window.removeEventListener(DESKTOP_BACKEND_CHANGED_EVENT, handler)
}

export function resolveApiUrl(path, baseUrl = '') {
  if (typeof path !== 'string' || !path) {
    return path
  }

  if (/^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(path)) {
    return path
  }

  if (!state.isDesktop) {
    return path
  }

  const targetBaseUrl = trimTrailingSlash(baseUrl || state.backendUrl || '')
  if (!targetBaseUrl) {
    return path
  }

  if (!path.startsWith('/')) {
    return `${targetBaseUrl}/${path}`
  }
  return `${targetBaseUrl}${path}`
}

export function resolveRemoteAssetUrl(path, baseUrl = '') {
  if (typeof path !== 'string' || !path) {
    return path
  }

  if (/^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(path) || path.startsWith('data:')) {
    return path
  }

  if (!state.isDesktop) {
    return path
  }

  const targetBaseUrl = trimTrailingSlash(baseUrl || state.backendUrl || '')
  if (!targetBaseUrl) {
    return path
  }

  if (path.startsWith('/')) {
    return `${targetBaseUrl}${path}`
  }

  return `${targetBaseUrl}/${path}`
}

export function buildLoginLocation() {
  return state.isDesktop ? '#/login' : '/login'
}

export function redirectToLogin() {
  if (state.isDesktop) {
    window.location.hash = '#/login'
    return
  }
  window.location.href = '/login'
}
