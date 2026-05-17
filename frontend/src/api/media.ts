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

const BASE_URL = (import.meta.env['VITE_API_URL'] as string | undefined) ?? 'http://localhost:8000'

export async function uploadMedia(projectId: string, file: File, articleId?: string): Promise<MediaAsset> {
  const formData = new FormData()
  formData.append('file', file)
  if (articleId) formData.append('article_id', articleId)

  const token = localStorage.getItem('token')
  const res = await fetch(`${BASE_URL}/projects/${projectId}/media/upload`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  })

  if (!res.ok) {
    throw new Error(`Upload failed (${res.status})`)
  }

  return res.json()
}

export function listMedia(projectId: string, articleId?: string): Promise<MediaAsset[]> {
  const qs = articleId ? `?article_id=${articleId}` : ''
  return api.get<MediaAsset[]>(`/projects/${projectId}/media${qs}`)
}

export function deleteMedia(mediaId: string): Promise<void> {
  return api.delete(`/media/${mediaId}`)
}
