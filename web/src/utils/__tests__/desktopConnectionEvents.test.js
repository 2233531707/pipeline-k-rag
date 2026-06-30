import assert from 'node:assert/strict'

if (typeof globalThis.CustomEvent === 'undefined') {
  globalThis.CustomEvent = class CustomEvent extends Event {
    constructor(type, options = {}) {
      super(type)
      this.detail = options.detail
    }
  }
}

globalThis.window = new EventTarget()
globalThis.window.kbDesktop = {
  isDesktop: true,
  getRuntimeState: async () => ({
    backendUrl: 'https://old.example.com',
    defaultBackendUrl: '',
    authToken: ''
  })
}

const {
  DESKTOP_BACKEND_CHANGED_EVENT,
  notifyDesktopBackendChanged,
  onDesktopBackendChanged
} = await import('../../runtime/desktop.js')

let received = null
const stopListening = onDesktopBackendChanged((event) => {
  received = event.detail
})

notifyDesktopBackendChanged({
  previousBackendUrl: 'https://old.example.com',
  nextBackendUrl: 'https://new.example.com'
})

assert.equal(DESKTOP_BACKEND_CHANGED_EVENT, 'kb-desktop-backend-changed')
assert.deepEqual(received, {
  previousBackendUrl: 'https://old.example.com',
  nextBackendUrl: 'https://new.example.com'
})

received = null
stopListening()
notifyDesktopBackendChanged({ nextBackendUrl: 'https://ignored.example.com' })
assert.equal(received, null)

console.log('desktopConnectionEvents: all assertions passed')
