import { api } from './client'
import type { PerformanceSummary, ArticlePerformance, ArticlePerformanceBrief } from '@/types'

export function getPerformanceSummary(projectId: string, period = '30d'): Promise<PerformanceSummary> {
  return api.get<PerformanceSummary>(`/projects/${projectId}/performance/summary?period=${period}`)
}

export function getArticlesPerformance(projectId: string, period = '30d'): Promise<ArticlePerformanceBrief[]> {
  return api.get<ArticlePerformanceBrief[]>(`/projects/${projectId}/performance/articles?period=${period}`)
}

export function getArticlePerformance(articleId: string, period = '30d'): Promise<ArticlePerformance> {
  return api.get<ArticlePerformance>(`/articles/${articleId}/performance?period=${period}`)
}
