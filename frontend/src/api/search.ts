import { api } from './client'

export type SearchResult = {
  type: 'article' | 'category' | 'project'
  id: string
  title: string
  subtitle: string | null
  url: string
}

type SearchResponse = SearchResult[] | { results: SearchResult[]; total: number }

export async function globalSearch(query: string): Promise<SearchResult[]> {
  const response = await api.get<SearchResponse>(`/search?q=${encodeURIComponent(query)}`)
  return Array.isArray(response) ? response : response.results
}
