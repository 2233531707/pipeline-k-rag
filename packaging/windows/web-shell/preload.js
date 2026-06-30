const { contextBridge, ipcRenderer } = require('electron')

if (window.location.protocol === 'file:') {
  contextBridge.exposeInMainWorld('yuxiWebShell', {
    getConfig: () => ipcRenderer.invoke('web-shell:get-config'),
    saveConfig: (payload) => ipcRenderer.invoke('web-shell:save-config', payload),
    openTarget: () => ipcRenderer.invoke('web-shell:open-target')
  })
}
