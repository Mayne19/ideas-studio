import { api } from './client'

export type ExternalServiceKey = 'search' | 'images' | 'brand_images' | string

export type ExternalServiceProviderOption = {
  code: string
  label: string
  fields: string[]
  docs_url: string | null
}

export type ExternalServiceSource = 'project' | 'global' | 'env'

/** Jamais la clé elle-même : seulement api_key_configured + 4 derniers caractères. */
export type ExternalServicePublic = {
  service: ExternalServiceKey
  label: string
  description: string | null
  providers: ExternalServiceProviderOption[]
  id: string | null
  project_id: string | null
  provider: string | null
  api_key_configured: boolean
  key_last4: string | null
  config: Record<string, string>
  last_test_status: 'connected' | 'error' | null
  last_test_error: string | null
  last_tested_at: string | null
  updated_at: string | null
  effective_source: ExternalServiceSource | null
  effective_provider: string | null
  effective_key_last4: string | null
}

export type ExternalServiceUpsert = {
  provider: string
  api_key?: string
  config?: Record<string, string>
}

export type ExternalServiceTestResult = {
  service: string
  provider: string | null
  source: string | null
  status: 'connected' | 'error'
  message: string | null
}

function scope(projectId?: string): string {
  return projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
}

export function listExternalServices(projectId?: string): Promise<ExternalServicePublic[]> {
  return api.get<ExternalServicePublic[]>(`/settings/external-services${scope(projectId)}`)
}

export function saveExternalService(
  service: ExternalServiceKey,
  data: ExternalServiceUpsert,
  projectId?: string,
): Promise<ExternalServicePublic> {
  return api.put<ExternalServicePublic>(`/settings/external-services/${service}${scope(projectId)}`, data)
}

export function deleteExternalService(service: ExternalServiceKey, projectId?: string): Promise<void> {
  return api.delete<void>(`/settings/external-services/${service}${scope(projectId)}`)
}

/** Sans `draft` : teste la clé enregistrée (ou celle réellement utilisée). Avec `draft` : teste la clé saisie. */
export function testExternalService(
  service: ExternalServiceKey,
  projectId?: string,
  draft?: ExternalServiceUpsert,
): Promise<ExternalServiceTestResult> {
  return api.post<ExternalServiceTestResult>(`/settings/external-services/${service}/test${scope(projectId)}`, draft)
}
