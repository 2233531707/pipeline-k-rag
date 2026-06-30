const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('kbDesktop', {
  isDesktop: true,
  getRuntimeState: () => ipcRenderer.invoke('desktop:get-runtime-state'),
  setConnectionConfig: (payload) => ipcRenderer.invoke('desktop:set-connection-config', payload),
  setAuthToken: (token) => ipcRenderer.invoke('desktop:set-auth-token', token),
  clearAuthToken: () => ipcRenderer.invoke('desktop:clear-auth-token')
})
