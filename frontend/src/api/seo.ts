import { api } from './client'
import type { SeoAnalysis, ReadyCheck } from '@/types'

export function analyzeArticle(_projectId: string, articleId: string): Promise<SeoAnalysis> {
  return api.post<SeoAnalysis>(`/articles/${articleId}/analyze`)
}

export function getLatestAnalysis(_projectId: string, articleId: string): Promise<SeoAnalysis> {
  return api.get<SeoAnalysis>(`/articles/${articleId}/analysis/latest`)
}

export function readyCheck(_projectId: string, articleId: string): Promise<ReadyCheck> {
  return api.post<ReadyCheck>(`/articles/${articleId}/ready-check`)
}
