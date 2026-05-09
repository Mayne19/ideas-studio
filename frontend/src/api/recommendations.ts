import { api } from './client'
import type { OptimizationRecommendation } from '@/types'

export function listRecommendations(projectId: string): Promise<OptimizationRecommendation[]> {
  return api.get<OptimizationRecommendation[]>(`/projects/${projectId}/recommendations`)
}

export function triggerReview(projectId: string): Promise<{ generated: number }> {
  return api.post<{ generated: number }>(`/projects/${projectId}/recommendations/review`)
}

export function acceptRecommendation(id: string): Promise<OptimizationRecommendation> {
  return api.post<OptimizationRecommendation>(`/recommendations/${id}/accept`)
}

export function rejectRecommendation(id: string): Promise<OptimizationRecommendation> {
  return api.post<OptimizationRecommendation>(`/recommendations/${id}/reject`)
}

export function applyRecommendation(id: string): Promise<OptimizationRecommendation> {
  return api.post<OptimizationRecommendation>(`/recommendations/${id}/apply`)
}
