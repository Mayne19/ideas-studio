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

export type SearchConsoleStatus = {
  connected: boolean
  provider?: string
  message: string | null
  docs_url?: string
}

export type SearchConsolePage = {
  url: string
  clicks: number
  impressions: number
  ctr: number
  position: number
}

export type SearchConsolePerformance = {
  connected?: boolean
  clicks: number
  impressions: number
  ctr: number
  position: number
  date?: string
  message?: string | null
}

export type SearchConsolePagesResponse = {
  connected: boolean
  pages: SearchConsolePage[]
  message: string | null
}

export function getSearchConsoleStatus(projectId: string): Promise<SearchConsoleStatus> {
  return api.get<SearchConsoleStatus>(`/projects/${projectId}/search-console/status`)
}

export function getSearchConsolePages(projectId: string): Promise<SearchConsolePagesResponse> {
  return api.get<SearchConsolePagesResponse>(`/projects/${projectId}/search-console/pages`)
}

export function getSearchConsolePerformance(projectId: string): Promise<SearchConsolePerformance> {
  return api.get<SearchConsolePerformance>(`/projects/${projectId}/search-console/performance`)
}
