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

export type DiscoverIdeasResponse = {
  ideas: Array<{
    id: string
    title: string
    keyword: string | null
    angle: string | null
    search_intent: string | null
    audience: string | null
    opportunity_score: number | null
    serp_terms: string[]
  }>
  generated: number
}

export function discoverIdeas(projectId: string, topic: string, count: number = 5): Promise<DiscoverIdeasResponse> {
  return api.post<DiscoverIdeasResponse>(`/projects/${projectId}/ideas/discover`, { topic, count })
}

export type SendToProductionResponse = {
  id: string
  title: string
  status: string
  next_agent_key: string | null
  workflow_status: string | null
}

export function sendToProduction(articleId: string): Promise<SendToProductionResponse> {
  return api.post<SendToProductionResponse>(`/articles/${articleId}/send-to-production`)
}

export type ProductionQueueSummary = {
  total_in_queue: number
  counts: Record<string, number>
  next_up: {
    id: string
    title: string
    next_agent_key: string | null
  } | null
}

export function getProductionQueue(projectId: string): Promise<ProductionQueueSummary> {
  return api.get<ProductionQueueSummary>(`/projects/${projectId}/production/queue`)
}

export function processProductionQueue(projectId: string): Promise<{ processed: number; articles: Array<{ id: string; title: string; status: string; next_agent_key: string | null }> }> {
  return api.post(`/projects/${projectId}/production/process`)
}

export type MonthlyPlanResponse = {
  status: string
  month?: string
  ideas_generated?: number
  categories_used?: number
  errors?: string[] | null
  message?: string
}

export function generateMonthlyPlan(projectId: string, force: boolean = false, generation_day?: number): Promise<MonthlyPlanResponse> {
  return api.post<MonthlyPlanResponse>(`/projects/${projectId}/planning/monthly`, { force, generation_day })
}

export type ImprovementAnalysisResponse = {
  id: string
  monitoring_status: string | null
  performance_diagnosis: Record<string, unknown> | null
  improvement_proposal: Record<string, unknown> | null
}

export function analyzeArticleImprovement(articleId: string): Promise<ImprovementAnalysisResponse> {
  return api.post<ImprovementAnalysisResponse>(`/articles/${articleId}/analyze-improvement`)
}

export type CreateImprovementDraftResponse = {
  id: string
  title: string
  status: string
  original_article_id: string | null
  monitoring_status: string | null
}

export function createImprovementDraft(articleId: string): Promise<CreateImprovementDraftResponse> {
  return api.post<CreateImprovementDraftResponse>(`/articles/${articleId}/create-improvement-draft`)
}

export type ScanMonitoringResponse = {
  scanned: number
  articles_with_proposals: Array<{ id: string; title: string; monitoring_status: string | null }>
}

export function scanMonitoring(projectId: string): Promise<ScanMonitoringResponse> {
  return api.post<ScanMonitoringResponse>(`/projects/${projectId}/monitoring/scan`)
}
