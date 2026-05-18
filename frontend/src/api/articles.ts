import { api } from './client'
import type { Article } from '@/types'

export type ArticleFilters = {
  status?: string
  category_id?: string
  search?: string
  skip?: number
  limit?: number
}

export type CreateArticlePayload = {
  title: string
  keyword?: string
  category_id?: string
  status?: string
}

export function listArticles(projectId: string, filters: ArticleFilters = {}): Promise<Article[]> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.category_id) params.set('category_id', filters.category_id)
  if (filters.search) params.set('search', filters.search)
  if (filters.skip !== undefined) params.set('skip', String(filters.skip))
  if (filters.limit !== undefined) params.set('limit', String(filters.limit))
  const qs = params.toString()
  return api.get<Article[]>(`/projects/${projectId}/articles${qs ? `?${qs}` : ''}`)
}

export function getArticle(_projectId: string, articleId: string): Promise<Article> {
  return api.get<Article>(`/articles/${articleId}`)
}

export function createArticle(projectId: string, payload: CreateArticlePayload): Promise<Article> {
  return api.post<Article>(`/projects/${projectId}/articles`, payload)
}

export type PublishResponse = Article & { revalidated: boolean }
export type PromoteResponse = Article & { revalidated: boolean }

export function publishArticle(_projectId: string, articleId: string): Promise<PublishResponse> {
  return api.post<PublishResponse>(`/articles/${articleId}/publish`)
}

export function promoteArticle(_projectId: string, articleId: string): Promise<PromoteResponse> {
  return api.post<PromoteResponse>(`/articles/${articleId}/promote`)
}

export function unpublishArticle(_projectId: string, articleId: string): Promise<Article> {
  return api.post<Article>(`/articles/${articleId}/unpublish`)
}

export function markReadyArticle(_projectId: string, articleId: string): Promise<Article> {
  return api.post<Article>(`/articles/${articleId}/mark-ready`)
}

export function archiveArticle(_projectId: string, articleId: string): Promise<Article> {
  return api.post<Article>(`/articles/${articleId}/archive`)
}

export function scheduleArticle(_projectId: string, articleId: string, scheduledAt: string): Promise<Article> {
  return api.post<Article>(`/articles/${articleId}/schedule`, { scheduled_at: scheduledAt })
}

export function analyzeSeoArticle(_projectId: string, articleId: string): Promise<unknown> {
  return api.post(`/articles/${articleId}/analyze`)
}

export function patchArticle(_projectId: string, articleId: string, data: Partial<{ status: string; title: string; keyword: string; category_id: string }>): Promise<Article> {
  return api.patch<Article>(`/articles/${articleId}`, data)
}

export function deleteArticle(_projectId: string, articleId: string): Promise<void> {
  return api.delete(`/articles/${articleId}`)
}

export type GenerateArticleRequest = {
  preferred_title?: string | null
  keyword?: string | null
  category_id?: string | null
  audience?: string | null
  angle?: string | null
  search_intent?: string | null
  context_hint?: string | null
  include_faq?: boolean | null
  include_callouts?: boolean | null
}

export type GenerateArticleResponse = {
  id: string
  title: string
  keyword: string | null
  status: string
  word_count: number
  provider_name?: string | null
  model_name?: string | null
}

export function generateArticle(projectId: string, payload: GenerateArticleRequest = {}): Promise<GenerateArticleResponse> {
  return api.post<GenerateArticleResponse>(`/projects/${projectId}/articles/generate`, payload)
}

export type AutoGenerateIdeasResponse = {
  ideas: Array<{
    id: string
    title: string
    keyword: string | null
    angle: string | null
    search_intent: string | null
    audience: string | null
    opportunity_score: number | null
  }>
  generated: number
}

export function autoGenerateIdeas(projectId: string, count: number = 3, context_hint?: string | null): Promise<AutoGenerateIdeasResponse> {
  return api.post<AutoGenerateIdeasResponse>(`/projects/${projectId}/ideas/auto-generate`, { count, context_hint })
}
