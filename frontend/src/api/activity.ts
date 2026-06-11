import { api } from './client'

export type ActivityLog = {
  id: string
  project_id: string
  user_id: string
  user_name: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  description: string | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export function listActivity(projectId: string, limit: number = 20): Promise<ActivityLog[]> {
  return api.get<ActivityLog[]>(`/projects/${projectId}/activity?limit=${limit}`)
}
