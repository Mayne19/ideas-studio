import { api } from './client'
import type { EditorArticle, AutosaveRequest, AutosaveResponse, ArticleVersion } from '@/types'

export type EditorUpdatePayload = AutosaveRequest

export function getEditorArticle(_projectId: string, articleId: string): Promise<EditorArticle> {
  return api.get<EditorArticle>(`/articles/${articleId}/editor`)
}

export function updateEditorArticle(_projectId: string, articleId: string, payload: EditorUpdatePayload): Promise<EditorArticle> {
  return api.patch<EditorArticle>(`/articles/${articleId}/editor`, payload)
}

export function autosaveArticle(_projectId: string, articleId: string, payload: AutosaveRequest): Promise<AutosaveResponse> {
  return api.post<AutosaveResponse>(`/articles/${articleId}/autosave`, payload)
}

export function getArticlePreview(_projectId: string, articleId: string): Promise<{ html: string }> {
  return api.get<{ html: string }>(`/articles/${articleId}/preview`)
}

export function listVersions(_projectId: string, articleId: string): Promise<ArticleVersion[]> {
  return api.get<ArticleVersion[]>(`/articles/${articleId}/versions`)
}

export function restoreVersion(_projectId: string, articleId: string, versionId: string): Promise<EditorArticle> {
  return api.post<EditorArticle>(`/articles/${articleId}/versions/${versionId}/restore`)
}
