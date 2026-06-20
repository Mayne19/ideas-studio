import { api } from './client'

export type AIProviderPublic = {
  id: string
  project_id: string | null
  provider: string
  label: string
  display_name: string | null
  api_key_configured: boolean
  model: string | null
  base_url: string | null
  is_default: boolean
  enabled: boolean
  last_test_status: string | null
  last_test_error: string | null
  last_tested_at: string | null
  created_at: string
  updated_at: string
}

export function listAIProviders(projectId?: string): Promise<AIProviderPublic[]> {
  const params = projectId ? `?project_id=${projectId}` : ''
  return api.get<AIProviderPublic[]>(`/settings/ai-providers${params}`)
}
