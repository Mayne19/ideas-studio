import { api } from './client'
import type { Article, ArticleStatusCode } from '@/types'

export type ArticleFilters = {
  status?: ArticleStatusCode
  statuses?: ArticleStatusCode[]
  category_id?: string
  search?: string
  skip?: number
  limit?: number
  blocked_cost_limit?: number
  published_only?: boolean
  archived?: boolean
}

export type CreateArticlePayload = {
  title: string
  keyword?: string
  category_id?: string
  sub_niche?: string
  is_featured?: boolean
}

export type BulkValidateResponse = {
  validated_count: number
  blocked_count: number
  scheduled_count: number
  not_found_count: number
  not_found_ids: string[]
  blocked_articles: Array<{
    article_id: string
    title: string
    reasons: string[]
  }>
}

export function listArticles(projectId: string, filters: ArticleFilters = {}): Promise<Article[]> {
  const params = new URLSearchParams()
  if (filters.status !== undefined) params.set('status', String(filters.status))
  if (filters.statuses && filters.statuses.length > 0) params.set('statuses', filters.statuses.join(','))
  if (filters.category_id) params.set('category_id', filters.category_id)
  if (filters.search) params.set('search', filters.search)
  if (filters.skip !== undefined) params.set('skip', String(filters.skip))
  if (filters.limit !== undefined) params.set('limit', String(filters.limit))
  if (filters.blocked_cost_limit !== undefined) params.set('blocked_cost_limit', String(filters.blocked_cost_limit))
  if (filters.published_only) params.set('published_only', 'true')
  if (filters.archived) params.set('archived', 'true')
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

export function rollbackArticle(_projectId: string, articleId: string): Promise<Article> {
  return api.post<Article>(`/articles/${articleId}/rollback`)
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

export function unarchiveArticle(_projectId: string, articleId: string): Promise<Article> {
  return api.post<Article>(`/articles/${articleId}/unarchive`)
}

export function scheduleArticle(_projectId: string, articleId: string, scheduledAt: string): Promise<Article> {
  return api.post<Article>(`/articles/${articleId}/schedule`, { scheduled_at: scheduledAt })
}

export function unscheduleArticle(_projectId: string, articleId: string): Promise<Article> {
  return api.post<Article>(`/articles/${articleId}/unschedule`)
}

export function analyzeSeoArticle(_projectId: string, articleId: string): Promise<unknown> {
  return api.post(`/articles/${articleId}/analyze`)
}

export function patchArticle(_projectId: string, articleId: string, data: Partial<{ title: string; keyword: string; category_id: string }>): Promise<Article> {
  return api.patch<Article>(`/articles/${articleId}`, data)
}

export function deleteArticle(_projectId: string, articleId: string): Promise<void> {
  return api.delete(`/articles/${articleId}`)
}

export function bulkValidateArticles(projectId: string, articleIds: string[]): Promise<BulkValidateResponse> {
  return api.post<BulkValidateResponse>(`/projects/${projectId}/articles/bulk/validate`, { article_ids: articleIds })
}

export function bulkPublishArticles(projectId: string, articleIds: string[]): Promise<BulkValidateResponse> {
  return api.post<BulkValidateResponse>(`/projects/${projectId}/articles/bulk/publish`, { article_ids: articleIds })
}

export type BulkValidateByScoreResponse = BulkValidateResponse & {
  score_threshold_applied: number
  total_eligible: number
}

export function bulkValidateByScore(
  projectId: string,
  minScore: number,
  statuses: ArticleStatusCode[],
): Promise<BulkValidateByScoreResponse> {
  return api.post<BulkValidateByScoreResponse>(`/projects/${projectId}/articles/bulk/validate-by-score`, {
    min_score: minScore,
    statuses,
  })
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
  status: ArticleStatusCode
  word_count: number
  provider_name?: string | null
  model_name?: string | null
}

export type GenerationJobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export type GenerationJob = {
  id: string
  project_id: string
  status: GenerationJobStatus
  article_id: string | null
  current_step: string | null
  steps_completed: number
  error: string | null
  title: string | null
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export function isGenerationJobDone(job: GenerationJob): boolean {
  return job.status === 'succeeded' || job.status === 'failed' || job.status === 'cancelled'
}

/** Lance la génération en tâche de fond : le backend répond 202 avec un job
 * (le proxy Railway coupe les requêtes à 300 s, un article prend 7 à 12 min).
 * Suivre l'avancement avec getGenerationJob() / waitForGenerationJob(). */
export function generateArticle(projectId: string, payload: GenerateArticleRequest = {}): Promise<GenerationJob> {
  return api.post<GenerationJob>(`/projects/${projectId}/articles/generate`, payload)
}

export function getGenerationJob(projectId: string, jobId: string): Promise<GenerationJob> {
  return api.get<GenerationJob>(`/projects/${projectId}/generation-jobs/${jobId}`)
}

export function listGenerationJobs(projectId: string, options: { limit?: number; active?: boolean } = {}): Promise<GenerationJob[]> {
  const params = new URLSearchParams()
  if (options.limit !== undefined) params.set('limit', String(options.limit))
  if (options.active) params.set('active', 'true')
  const qs = params.toString()
  return api.get<GenerationJob[]>(`/projects/${projectId}/generation-jobs${qs ? `?${qs}` : ''}`)
}

/** Interroge le job jusqu'à son issue. Une erreur réseau ponctuelle
 * (redéploiement, coupure) ne fait pas échouer le suivi : on réessaie. */
export async function waitForGenerationJob(
  projectId: string,
  jobId: string,
  options: { intervalMs?: number; onUpdate?: (job: GenerationJob) => void; signal?: AbortSignal } = {},
): Promise<GenerationJob> {
  const intervalMs = options.intervalMs ?? 4000
  let consecutiveErrors = 0
  for (;;) {
    if (options.signal?.aborted) throw new DOMException('Suivi interrompu', 'AbortError')
    try {
      const job = await getGenerationJob(projectId, jobId)
      consecutiveErrors = 0
      options.onUpdate?.(job)
      if (isGenerationJobDone(job)) return job
    } catch (err) {
      consecutiveErrors += 1
      if (consecutiveErrors >= 10) throw err
    }
    await new Promise((resolve) => window.setTimeout(resolve, intervalMs))
  }
}
