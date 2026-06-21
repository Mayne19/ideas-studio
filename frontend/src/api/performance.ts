import { api } from './client'
import type { PerformanceSummary, ArticlePerformance, ArticlePerformanceBrief } from '@/types'

export type PerformancePeriodParams = string | {
  period?: string
  period_type?: string
  start_date?: string
  end_date?: string
}

function periodQuery(params: PerformancePeriodParams = '30d') {
  if (typeof params === 'string') return `period=${encodeURIComponent(params)}`
  const query = new URLSearchParams()
  if (params.period) query.set('period', params.period)
  if (params.period_type) query.set('period_type', params.period_type)
  if (params.start_date) query.set('start_date', params.start_date)
  if (params.end_date) query.set('end_date', params.end_date)
  return query.toString()
}

export function getPerformanceSummary(projectId: string, period: PerformancePeriodParams = '30d'): Promise<PerformanceSummary> {
  return api.get<PerformanceSummary>(`/projects/${projectId}/performance/summary?${periodQuery(period)}`)
}

export function getArticlesPerformance(projectId: string, period: PerformancePeriodParams = '30d'): Promise<ArticlePerformanceBrief[]> {
  return api.get<ArticlePerformanceBrief[]>(`/projects/${projectId}/performance/articles?${periodQuery(period)}`)
}

export function getArticlePerformance(articleId: string, period = '30d'): Promise<ArticlePerformance> {
  return api.get<ArticlePerformance>(`/articles/${articleId}/performance?period=${period}`)
}
