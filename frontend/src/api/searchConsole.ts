import { api } from './client'

export type KeywordOpportunity = {
  keyword: string
  article_id: string | null
  article_title: string | null
  position: number | null
  clicks: number | null
  visits: number | null
  variation: number | null
  opportunity: string | null
  source: 'google_search_console'
}

export type KeywordOpportunitiesResponse = {
  connected: boolean
  keywords: KeywordOpportunity[]
  message: string | null
}

export function getKeywordOpportunities(projectId: string): Promise<KeywordOpportunitiesResponse> {
  return api.get<KeywordOpportunitiesResponse>(`/projects/${projectId}/search-console/keywords`)
}
