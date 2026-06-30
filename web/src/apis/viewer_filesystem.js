import { apiDelete, apiGet, apiPost, apiUrl } from './base'

const buildQuery = (params) => {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value))
    }
  })
  return query.toString()
}

const buildViewerQuery = (threadId, path) => {
  return buildQuery({
    thread_id: threadId,
    path
  })
}

export const getViewerFileSystemTree = (threadId, path = '/') => {
  const query = buildViewerQuery(threadId, path)
  return apiGet(`/api/viewer/filesystem/tree?${query}`)
}

export const getViewerFileContent = (threadId, path) => {
  return apiGet(getViewerFileContentUrl(threadId, path))
}

export const downloadViewerFile = (threadId, path) => {
  return apiGet(getViewerFileDownloadUrl(threadId, path), {}, true, 'blob')
}

export const deleteViewerFile = (threadId, path) => {
  const query = buildViewerQuery(threadId, path)
  return apiDelete(`/api/viewer/filesystem/file?${query}`)
}

export const createViewerDirectory = (threadId, parentPath, name) => {
  return apiPost('/api/viewer/filesystem/directory', {
    thread_id: threadId,
    parent_path: parentPath,
    name
  })
}

export const uploadViewerFiles = (threadId, parentPath, files) => {
  const formData = new FormData()
  formData.set('thread_id', threadId)
  formData.set('parent_path', parentPath)
  files.forEach((file) => formData.append('files', file))
  return apiPost('/api/viewer/filesystem/upload', formData)
}

export const getViewerFileContentUrl = (threadId, path) => {
  const query = buildViewerQuery(threadId, path)
  return apiUrl(`/api/viewer/filesystem/file?${query}`)
}

export const getViewerFileDownloadUrl = (threadId, path) => {
  const query = buildViewerQuery(threadId, path)
  return apiUrl(`/api/viewer/filesystem/download?${query}`)
}
