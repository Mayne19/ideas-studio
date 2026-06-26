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

export type PreviewResponse = {
  id: string;
  title: string;
  slug: string;
  content: string | null;
  excerpt: string | null;
  meta_title: string | null;
  meta_description: string | null;
  cover_image_url: string | null;
  sub_niche: string | null;
  featured: boolean;
  faq_json: unknown;
  callouts_json: unknown;
  internal_links_json: unknown;
  external_links_json: unknown;
  content_blocks_json: unknown;
  author_name: string | null;
  reading_time_minutes: number | null;
  status: string;
}

export function getArticlePreview(_projectId: string, articleId: string): Promise<PreviewResponse> {
  return api.get<PreviewResponse>(`/articles/${articleId}/preview`)
}

export function listVersions(_projectId: string, articleId: string): Promise<ArticleVersion[]> {
  return api.get<ArticleVersion[]>(`/articles/${articleId}/versions`)
}

export function restoreVersion(_projectId: string, articleId: string, versionId: string): Promise<EditorArticle> {
  return api.post<EditorArticle>(`/articles/${articleId}/versions/${versionId}/restore`)
}
