import { api } from './client'
import { listArticles } from './articles'
import type {
  Article,
  IdeaGenerateRequest,
  IdeaGenerateResponse,
  IdeaRejectRequest,
  IdeaLaunchRequest,
  IdeaLaunchResponse,
} from '@/types'

export function listIdeas(projectId: string, status?: string): Promise<Article[]> {
  return listArticles(projectId, { status, limit: 100 })
}

export function generateIdea(projectId: string, payload: IdeaGenerateRequest = {}): Promise<IdeaGenerateResponse> {
  return api.post<IdeaGenerateResponse>(`/projects/${projectId}/ideas/generate`, payload)
}

export function rejectIdea(articleId: string, payload: IdeaRejectRequest = {}): Promise<{ status: string }> {
  return api.post<{ status: string }>(`/articles/${articleId}/reject`, payload)
}

export function setIdeaPriority(articleId: string, priority: number): Promise<{ priority: number; status: string }> {
  return api.post<{ priority: number; status: string }>(`/articles/${articleId}/priority`, { priority })
}

export function startWriting(articleId: string): Promise<IdeaGenerateResponse> {
  return api.post<IdeaGenerateResponse>(`/articles/${articleId}/start-writing`)
}

export function createManualDraft(articleId: string): Promise<IdeaGenerateResponse> {
  return api.post<IdeaGenerateResponse>(`/articles/${articleId}/manual-draft`)
}

export function launchIdeas(projectId: string, payload: IdeaLaunchRequest): Promise<IdeaLaunchResponse> {
  return api.post<IdeaLaunchResponse>(`/projects/${projectId}/launch`, payload)
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
