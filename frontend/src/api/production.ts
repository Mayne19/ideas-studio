import { api } from './client'

export type WorkflowStatus = 'idea' | 'writing' | 'review' | 'validated' | 'scheduled' | 'published' | 'update' | 'error'

export type ProductionCheck = {
  name: string
  passed: boolean
  detail?: string
  points?: number
  earned?: number
}

export type ProductionArticle = {
  id: string
  title: string
  slug: string
  status: WorkflowStatus | null
  scheduled_for: string | null
  published_at: string | null
  updated_at: string
  category_id: string | null
  category_name: string | null
  keyword: string | null
  duplicate: boolean
  score: number | null
  checks: ProductionCheck[]
  alerts: string[]
  fiche: Record<string, unknown> | null
  planned_write_at: string | null
  cost_usd: number | null
  error: string | null
}

export type WorkflowValidation = {
  article: ProductionArticle
  passed: boolean
  checks: ProductionCheck[]
  scheduled_for: string | null
  global_score: number | null
  min_publish_score: number | null
}

export function listProductionArticles(projectId: string, status?: WorkflowStatus): Promise<ProductionArticle[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return api.get<ProductionArticle[]>(`/projects/${projectId}/editorial-workflow/articles${query}`)
}

export async function getProductionArticle(projectId: string, articleId: string): Promise<ProductionArticle | null> {
  const items = await listProductionArticles(projectId, 'review')
  return items.find((item) => item.id === articleId) ?? null
}

export function listProductionWritingQueue(projectId: string): Promise<ProductionArticle[]> {
  return api.get<ProductionArticle[]>(`/projects/${projectId}/editorial-workflow/writing-queue`)
}

export function listProductionUpdates(projectId: string): Promise<ProductionArticle[]> {
  return api.get<ProductionArticle[]>(`/projects/${projectId}/editorial-workflow/updates`)
}

export function requestProductionWriting(projectId: string, articleId: string): Promise<ProductionArticle> {
  return api.post<ProductionArticle>(`/projects/${projectId}/editorial-workflow/articles/${articleId}/request-writing`)
}

export function returnProductionToWriting(projectId: string, articleId: string, comment: string): Promise<ProductionArticle> {
  return api.post<ProductionArticle>(`/projects/${projectId}/editorial-workflow/articles/${articleId}/return-to-writing`, { comment })
}

export function rejectProductionArticle(projectId: string, articleId: string, comment = ''): Promise<ProductionArticle> {
  return api.post<ProductionArticle>(`/projects/${projectId}/editorial-workflow/articles/${articleId}/reject`, { comment })
}

export function validateProductionArticle(projectId: string, articleId: string): Promise<WorkflowValidation> {
  return api.post<WorkflowValidation>(`/projects/${projectId}/editorial-workflow/articles/${articleId}/validate`)
}
