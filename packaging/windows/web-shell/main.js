const fs = require('node:fs')
const path = require('node:path')
const { app, BrowserWindow, Menu, ipcMain, session } = require('electron')

const DEFAULT_WIDTH = 1400
const DEFAULT_HEIGHT = 900

let mainWindow = null

function getExternalConfigPath() {
  return path.join(app.isPackaged ? path.dirname(process.execPath) : __dirname, 'config.json')
}

function getUserConfigPath() {
  return path.join(app.getPath('userData'), 'config.json')
}

function readJsonFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return {}
  }
  return JSON.parse(fs.readFileSync(filePath, 'utf8'))
}

function normalizeWebUrl(value) {
  const raw = String(value || '').trim()
  if (!raw) {
    return ''
  }

  const url = new URL(raw)
  if (!['http:', 'https:'].includes(url.protocol)) {
    throw new Error('服务器地址必须以 http:// 或 https:// 开头')
  }
  url.hash = ''
  return url.toString().replace(/\/$/, '')
}

function readConfiguredWebUrl() {
  const external = readJsonFile(getExternalConfigPath())
  if (external.webUrl) {
    return normalizeWebUrl(external.webUrl)
  }

  const user = readJsonFile(getUserConfigPath())
  if (user.webUrl) {
    return normalizeWebUrl(user.webUrl)
  }

  return ''
}

function saveUserWebUrl(webUrl) {
  const normalized = normalizeWebUrl(webUrl)
  fs.mkdirSync(app.getPath('userData'), { recursive: true })
  fs.writeFileSync(getUserConfigPath(), `${JSON.stringify({ webUrl: normalized }, null, 2)}\n`, 'utf8')
  return normalized
}

async function clearWebSession() {
  await session.defaultSession.clearStorageData()
  await session.defaultSession.clearCache()
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: DEFAULT_WIDTH,
    height: DEFAULT_HEIGHT,
    minWidth: 1100,
    minHeight: 720,
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

  loadConfiguredTarget()
}

function loadConfiguredTarget() {
  const webUrl = readConfiguredWebUrl()
  if (!webUrl) {
    mainWindow.loadFile(path.join(__dirname, 'config.html'))
    return
  }
  mainWindow.loadURL(webUrl)
}

function openConfigPage() {
  if (!mainWindow) {
    return
  }
  mainWindow.loadFile(path.join(__dirname, 'config.html'))
}

function buildMenu() {
  return Menu.buildFromTemplate([
    {
      label: '应用',
      submenu: [
        { label: '配置服务器地址', click: openConfigPage },
        { label: '重新加载', role: 'reload' },
        { type: 'separator' },
        { label: '退出', role: 'quit' }
      ]
    }
  ])
}

ipcMain.handle('web-shell:get-config', () => {
  return {
    webUrl: readConfiguredWebUrl(),
    externalConfigPath: getExternalConfigPath(),
    userConfigPath: getUserConfigPath()
  }
})

ipcMain.handle('web-shell:save-config', async (_event, payload) => {
  const webUrl = saveUserWebUrl(payload?.webUrl)
  await clearWebSession()
  return { webUrl }
})

ipcMain.handle('web-shell:open-target', () => {
  loadConfiguredTarget()
  return true
})

app.whenReady().then(() => {
  Menu.setApplicationMenu(buildMenu())
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
