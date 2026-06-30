import assert from 'node:assert/strict'

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

const { initializeDesktopRuntime } = await import('../../runtime/desktop.js')
await initializeDesktopRuntime()

const { resolvePreviewAssetUrl, resolveRenderableAssetUrl } = await import('../desktopAssets.js')

assert.equal(
  resolvePreviewAssetUrl('/api/chat/thread/thread-1/artifacts/result.png'),
  'https://backend.example.com/yuxi/api/chat/thread/thread-1/artifacts/result.png'
)
assert.equal(
  resolvePreviewAssetUrl('https://cdn.example.com/result.png'),
  'https://cdn.example.com/result.png'
)
assert.equal(resolvePreviewAssetUrl('data:image/png;base64,abc'), 'data:image/png;base64,abc')
assert.equal(
  resolveRenderableAssetUrl('/api/chat/thread/thread-1/artifacts/chart.png'),
  'https://backend.example.com/yuxi/api/chat/thread/thread-1/artifacts/chart.png'
)
assert.equal(resolveRenderableAssetUrl('这是一段普通文本'), null)

console.log('desktopAssets: all assertions passed')
