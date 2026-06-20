import { api } from './client'
import type { Project, ConnectInfo } from '@/types'

export function listProjects(): Promise<Project[]> {
  return api.get<Project[]>('/projects')
}

export function getProject(id: string): Promise<Project> {
  return api.get<Project>(`/projects/${id}`)
}

export function getConnectInfo(id: string): Promise<ConnectInfo> {
  return api.get<ConnectInfo>(`/projects/${id}/connect`)
}

export type CreateProjectPayload = {
  name: string
  domain?: string
  language?: string
  country_target?: string
  timezone?: string
  description?: string
  industry?: string
  audience?: string
  tone?: string
  reader_level?: string
  writing_style?: string
  editorial_goal?: string
  value_proposition?: string
  allowed_topics?: string
  forbidden_topics?: string
  words_to_avoid?: string
  average_target_length?: string
  preferred_formats?: string
  technical_level?: string
  seo_rules?: string
  geo_rules?: string
  source_guidelines?: string
  internal_linking_guidelines?: string
  external_linking_guidelines?: string
  style_examples?: string
}

export type UpdateProjectPayload = {
  name?: string
  domain?: string
  language?: string
  country_target?: string
  timezone?: string
  description?: string
  industry?: string
  audience?: string
  tone?: string
  reader_level?: string
  writing_style?: string
  editorial_goal?: string
  value_proposition?: string
  allowed_topics?: string
  forbidden_topics?: string
  words_to_avoid?: string
  average_target_length?: string
  preferred_formats?: string
  technical_level?: string
  seo_rules?: string
  geo_rules?: string
  source_guidelines?: string
  internal_linking_guidelines?: string
  external_linking_guidelines?: string
  style_examples?: string
  public_site_url?: string | null
  revalidate_url?: string | null
  revalidate_secret?: string | null
}

export function createProject(payload: CreateProjectPayload): Promise<Project> {
  return api.post<Project>('/projects', payload)
}

export function updateProject(id: string, payload: UpdateProjectPayload): Promise<Project> {
  return api.patch<Project>(`/projects/${id}`, payload)
}

export function deleteProject(id: string): Promise<void> {
  return api.delete<void>(`/projects/${id}`)
}

export function disconnectProject(id: string): Promise<Project> {
  return api.post<Project>(`/projects/${id}/disconnect`)
}

export function revalidateProject(id: string): Promise<{ revalidated: boolean; status: string; message?: string }> {
  return api.post(`/projects/${id}/revalidate`)
}

export type EditorialSuggestion = {
  description: string
  audience: string
  tone: string
  positioning: string
  main_keywords: string[]
  recommended_categories: string[]
  seo_writing_guidelines: string
}

export type EditorialSetupResponse = {
  suggestion: EditorialSuggestion
  source: 'llm' | 'default'
  project_has_data: boolean
}

export function suggestEditorialSetup(projectId: string): Promise<EditorialSetupResponse> {
  return api.post<EditorialSetupResponse>(`/projects/${projectId}/editorial-setup/suggest`)
}
