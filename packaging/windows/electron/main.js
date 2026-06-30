const path = require('node:path')
const fs = require('node:fs')
const { app, BrowserWindow, ipcMain, protocol, safeStorage } = require('electron')

const PROTOCOL_SCHEME = 'kb-desktop'
const PROTOCOL_ORIGIN = 'kb-desktop://app'
const DEFAULT_BACKEND_URL = process.env.YUXI_DESKTOP_DEFAULT_BACKEND_URL || ''

let mainWindow = null
let store = null

async function getStore() {
  if (store) {
    return store
  }
  const { default: ElectronStore } = await import('electron-store')
  store = new ElectronStore({
    name: 'desktop-client',
    defaults: {
      backendUrl: DEFAULT_BACKEND_URL,
      authToken: ''
    }
  })
  return store
}

protocol.registerSchemesAsPrivileged([
  {
    scheme: PROTOCOL_SCHEME,
    privileges: {
      standard: true,
      secure: true,
      supportFetchAPI: true,
      corsEnabled: true
    }
  }
])

function getRendererEntryPath() {
  return path.join(__dirname, '..', '..', '..', 'web', 'dist', 'index.html')
}

function getPackagedRendererEntryPath() {
  return path.join(process.resourcesPath, 'web-dist', 'index.html')
}

function resolveRendererEntryPath() {
  const packagedPath = getPackagedRendererEntryPath()
  if (app.isPackaged && fs.existsSync(packagedPath)) {
    return packagedPath
  }
  return getRendererEntryPath()
}

function registerDesktopProtocol() {
  protocol.registerFileProtocol(PROTOCOL_SCHEME, (request, callback) => {
    const requestUrl = new URL(request.url)
    const pathname = requestUrl.pathname === '/' ? '/index.html' : requestUrl.pathname
    const entryPath = resolveRendererEntryPath()
    const rootDir = path.dirname(entryPath)
    callback(path.normalize(path.join(rootDir, pathname)))
  })
}

async function readAuthToken() {
  const encrypted = (await getStore()).get('authToken')
  if (!encrypted) {
    return ''
  }

  if (!safeStorage.isEncryptionAvailable()) {
    return String(encrypted)
  }

  try {
    const buffer = Buffer.from(String(encrypted), 'base64')
    return safeStorage.decryptString(buffer)
  } catch {
    return ''
  }
}

async function writeAuthToken(token) {
  const currentStore = await getStore()
  if (!token) {
    currentStore.set('authToken', '')
    return
  }

  if (!safeStorage.isEncryptionAvailable()) {
    currentStore.set('authToken', token)
    return
  }

  const encrypted = safeStorage.encryptString(token).toString('base64')
  currentStore.set('authToken', encrypted)
}

async function buildRuntimeState(authToken) {
  const currentStore = await getStore()
  return {
    isDesktop: true,
    protocolOrigin: PROTOCOL_ORIGIN,
    backendUrl: String(currentStore.get('backendUrl') || ''),
    defaultBackendUrl: DEFAULT_BACKEND_URL,
    authToken: authToken || ''
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 760,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      webSecurity: true
    }
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })
  mainWindow.loadURL(`${PROTOCOL_ORIGIN}/index.html`)
}

ipcMain.handle('desktop:get-runtime-state', async () => {
  return buildRuntimeState(await readAuthToken())
})

ipcMain.handle('desktop:set-connection-config', async (_event, payload) => {
  ;(await getStore()).set('backendUrl', String(payload?.backendUrl || ''))
  return buildRuntimeState(await readAuthToken())
})

ipcMain.handle('desktop:set-auth-token', async (_event, token) => {
  await writeAuthToken(String(token || ''))
  return true
})

ipcMain.handle('desktop:clear-auth-token', async () => {
  await writeAuthToken('')
  return true
})

app.whenReady()
  .then(() => {
    return getStore()
  })
  .then(() => {
    registerDesktopProtocol()
    createWindow()

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createWindow()
      }
    })
  })

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
