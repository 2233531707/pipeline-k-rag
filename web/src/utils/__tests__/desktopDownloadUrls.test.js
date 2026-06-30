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

const storage = new Map()
globalThis.localStorage = {
  getItem: (key) => (storage.has(key) ? storage.get(key) : null),
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key),
  clear: () => storage.clear()
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

  const { threadApi } = await server.ssrLoadModule('/src/apis/agent_api.js')
  const workspaceApi = await server.ssrLoadModule('/src/apis/workspace_api.js')
  const viewerFilesystemApi = await server.ssrLoadModule('/src/apis/viewer_filesystem.js')

  assert.equal(
    threadApi.getThreadArtifactUrl(
      'thread-1',
      '/home/gem/user-data/outputs/report final.pdf',
      true
    ),
    'https://backend.example.com/yuxi/api/chat/thread/thread-1/artifacts/home/gem/user-data/outputs/report%20final.pdf?download=true'
  )

  assert.equal(
    workspaceApi.getWorkspaceKnowledgeFileContentUrl('kb-1', 'file-1', 'parsed'),
    'https://backend.example.com/yuxi/api/workspace/knowledge/file?kb_id=kb-1&file_id=file-1&variant=parsed'
  )

  assert.equal(
    workspaceApi.getWorkspaceKnowledgeDownloadUrl('kb-1', 'file-1', 'original'),
    'https://backend.example.com/yuxi/api/workspace/knowledge/download?kb_id=kb-1&file_id=file-1&variant=original'
  )

  assert.equal(
    workspaceApi.getWorkspaceDownloadUrl('/saved_artifacts/chart.png'),
    'https://backend.example.com/yuxi/api/workspace/download?path=%2Fsaved_artifacts%2Fchart.png'
  )

  assert.equal(
    viewerFilesystemApi.getViewerFileContentUrl('thread-1', '/home/gem/user-data/outputs/report.md'),
    'https://backend.example.com/yuxi/api/viewer/filesystem/file?thread_id=thread-1&path=%2Fhome%2Fgem%2Fuser-data%2Foutputs%2Freport.md'
  )

  assert.equal(
    viewerFilesystemApi.getViewerFileDownloadUrl(
      'thread-1',
      '/home/gem/user-data/outputs/final report.pdf'
    ),
    'https://backend.example.com/yuxi/api/viewer/filesystem/download?thread_id=thread-1&path=%2Fhome%2Fgem%2Fuser-data%2Foutputs%2Ffinal+report.pdf'
  )

  console.log('desktopDownloadUrls: all assertions passed')
} finally {
  await server.close()
}
