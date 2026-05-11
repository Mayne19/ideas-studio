import { api } from './client'

export type MediaAsset = {
  id: string
  project_id: string
  article_id: string | null
  url: string
  filename: string | null
  mime_type: string | null
  size: number | null
  alt_text: string | null
  caption: string | null
  source: string | null
  created_at: string
  updated_at: string
}

function localMediaAsset(projectId: string, file: File, objectUrl: string, articleId?: string): MediaAsset {
  const now = new Date().toISOString()
  return {
    id: `local-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    project_id: projectId,
    article_id: articleId ?? null,
    url: objectUrl,
    filename: file.name,
    mime_type: file.type,
    size: file.size,
    alt_text: file.name,
    caption: null,
    source: 'local-preview',
    created_at: now,
    updated_at: now,
  }
}

export async function uploadMedia(projectId: string, file: File, articleId?: string): Promise<MediaAsset> {
  // Backend stores URL references — upload file to a base64 data URL for local preview,
  // or submit as URL if the file is already hosted. Here we create an object URL + register it.
  const objectUrl = URL.createObjectURL(file)
  try {
    return await api.post<MediaAsset>(`/projects/${projectId}/media/upload`, {
      article_id: articleId,
      url: objectUrl,
      filename: file.name,
      mime_type: file.type,
      size: file.size,
      source: 'upload',
    })
  } catch {
    return localMediaAsset(projectId, file, objectUrl, articleId)
  }
}

export function listMedia(projectId: string, articleId?: string): Promise<MediaAsset[]> {
  const qs = articleId ? `?article_id=${articleId}` : ''
  return api.get<MediaAsset[]>(`/projects/${projectId}/media${qs}`)
}

export function deleteMedia(mediaId: string): Promise<void> {
  return api.delete(`/media/${mediaId}`)
}
