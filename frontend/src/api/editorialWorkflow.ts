import { api } from './client'

export type WorkflowArticle = {
  id: string
  title: string
  slug: string
  status: 'idea' | 'writing' | 'review' | 'validated' | 'scheduled' | 'published' | 'update' | null
  scheduled_for: string | null
  published_at: string | null
  updated_at: string
}

export type ValidationReport = {
  article: WorkflowArticle
  passed: boolean
  checks: Array<{ name: string; passed: boolean; detail: string }>
  scheduled_for?: string | null
}

export function listWorkflowArticles(projectId: string, status?: WorkflowArticle['status']): Promise<WorkflowArticle[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return api.get<WorkflowArticle[]>(`/projects/${projectId}/editorial-workflow/articles${query}`)
}

export function listWritingQueue(projectId: string): Promise<WorkflowArticle[]> {
  return api.get<WorkflowArticle[]>(`/projects/${projectId}/editorial-workflow/writing-queue`)
}

export function listWorkflowUpdates(projectId: string): Promise<WorkflowArticle[]> {
  return api.get<WorkflowArticle[]>(`/projects/${projectId}/editorial-workflow/updates`)
}

export function listPublicationCalendar(projectId: string): Promise<WorkflowArticle[]> {
  return api.get<WorkflowArticle[]>(`/projects/${projectId}/editorial-workflow/calendar`)
}

export function requestWorkflowWriting(projectId: string, articleId: string): Promise<WorkflowArticle> {
  return api.post<WorkflowArticle>(`/projects/${projectId}/editorial-workflow/articles/${articleId}/request-writing`)
}

export function validateWorkflowArticle(projectId: string, articleId: string): Promise<ValidationReport> {
  return api.post<ValidationReport>(`/projects/${projectId}/editorial-workflow/articles/${articleId}/validate`)
}

export function scheduleWorkflowArticle(projectId: string, articleId: string, scheduledFor: string): Promise<ValidationReport> {
  return api.post<ValidationReport>(`/projects/${projectId}/editorial-workflow/articles/${articleId}/schedule`, {
    scheduled_for: scheduledFor,
  })
}
