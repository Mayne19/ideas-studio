import { api } from './client'

export type SearchResult = {
  type: 'article' | 'category' | 'project'
  id: string
  title: string
  subtitle: string | null
  url: string
}

export function globalSearch(query: string): Promise<SearchResult[]> {
  return api.get<SearchResult[]>(`/search?q=${encodeURIComponent(query)}`)
}
