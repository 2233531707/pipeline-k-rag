import assert from 'node:assert/strict'
import process from 'node:process'
import { createServer } from 'vite'

globalThis.window = {
  kbDesktop: {
    isDesktop: true,
    getRuntimeState: async () => ({
      backendUrl: 'https://backend.example.com/yuxi',
      defaultBackendUrl: '',
      authToken: ''
    })
  }
}

const server = await createServer({
  configFile: false,
  root: process.cwd(),
  logLevel: 'error',
  server: { middlewareMode: true },
  appType: 'custom',
  resolve: {
    alias: {
      '@': `${process.cwd()}/src`
    }
  },
  optimizeDeps: {
    entries: [],
    noDiscovery: true
  }
})

try {
  const { initializeDesktopRuntime } = await server.ssrLoadModule('/src/runtime/desktop.js')
  await initializeDesktopRuntime()

  const { normalizeAttachmentPreview } = await server.ssrLoadModule('/src/utils/file_utils.js')
  const preview = normalizeAttachmentPreview({
    file_id: 'file-1',
    file_name: 'result.png',
    file_type: 'image/png',
    file_size: 128,
    artifact_url: '/api/chat/thread/thread-1/artifacts/result.png'
  })

  assert.equal(
    preview.previewUrl,
    'https://backend.example.com/yuxi/api/chat/thread/thread-1/artifacts/result.png'
  )
  assert.equal(preview.isImage, true)

  console.log('desktopAttachmentPreview: all assertions passed')
} finally {
  await server.close()
}
