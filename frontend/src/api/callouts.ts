import { api } from './client'
import type { CalloutTemplate } from '@/types'

export type CreateCalloutTemplatePayload = {
  slug?: string
  label: string
  style?: string | null
  default_title?: string | null
  color_background?: string | null
  color_border?: string | null
  color_text?: string | null
  icon?: string | null
  class_name?: string | null
  settings_json?: string | null
  source?: 'manual' | 'imported'
  external_id?: string | null
}

export type UpdateCalloutTemplatePayload = Partial<CreateCalloutTemplatePayload>

export function listCalloutTemplates(projectId: string): Promise<CalloutTemplate[]> {
  return api.get<CalloutTemplate[]>(`/projects/${projectId}/callouts`)
}

export function createCalloutTemplate(projectId: string, payload: CreateCalloutTemplatePayload): Promise<CalloutTemplate> {
  return api.post<CalloutTemplate>(`/projects/${projectId}/callouts`, payload)
}

export function updateCalloutTemplate(projectId: string, calloutId: string, payload: UpdateCalloutTemplatePayload): Promise<CalloutTemplate> {
  return api.patch<CalloutTemplate>(`/projects/${projectId}/callouts/${calloutId}`, payload)
}

export function deleteCalloutTemplate(projectId: string, calloutId: string): Promise<void> {
  return api.delete<void>(`/projects/${projectId}/callouts/${calloutId}`)
}

export type SyncCalloutsResult = {
  callouts: CalloutTemplate[]
  message: string
}

export async function syncCalloutTemplates(projectId: string): Promise<SyncCalloutsResult> {
  const callouts = await api.post<CalloutTemplate[]>(`/projects/${projectId}/callouts/sync`)
  const message = `${callouts.length} callout(s) synchronise(s).`
  return { callouts, message }
}
