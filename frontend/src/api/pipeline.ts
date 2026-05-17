import { api } from './client'

export type PipelineSettings = {
  id: string
  project_id: string
  enabled: boolean
  active_days: string[]
  launch_hour: number
  articles_per_week: number
  category_priorities: Record<string, number>
  created_at: string
  updated_at: string
}

export type PipelineSettingsUpdate = {
  enabled?: boolean
  active_days?: string[]
  launch_hour?: number
  articles_per_week?: number
  category_priorities?: Record<string, number>
}

export type PipelineLog = {
  id: string
  project_id: string
  status: string
  ideas_generated: number
  articles_created: number
  errors: string | null
  started_at: string
  finished_at: string | null
}

export type PipelineRunResult = {
  status: string
  ideas_generated: number
  articles_created: number
}

export function getPipelineSettings(projectId: string): Promise<PipelineSettings> {
  return api.get<PipelineSettings>(`/projects/${projectId}/pipeline`)
}

export function updatePipelineSettings(projectId: string, data: PipelineSettingsUpdate): Promise<PipelineSettings> {
  return api.patch<PipelineSettings>(`/projects/${projectId}/pipeline`, data)
}

export function triggerPipelineRun(projectId: string): Promise<PipelineRunResult> {
  return api.post<PipelineRunResult>(`/projects/${projectId}/pipeline/run`)
}

export function getPipelineLogs(projectId: string, limit = 20): Promise<PipelineLog[]> {
  return api.get<PipelineLog[]>(`/projects/${projectId}/pipeline/logs?limit=${limit}`)
}
