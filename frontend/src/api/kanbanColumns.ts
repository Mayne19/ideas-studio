import { api } from './client'

export type KanbanColumn = {
  id: string
  project_id: string
  label: string
  status: string
  color: string
  sort_order: number
  created_at: string
  updated_at: string
}

export type KanbanColumnCreate = {
  label: string
  status?: string
  color?: string
  sort_order?: number
}

export type KanbanColumnUpdate = {
  label?: string
  color?: string
  sort_order?: number
}

export function listKanbanColumns(projectId: string): Promise<KanbanColumn[]> {
  return api.get<KanbanColumn[]>(`/projects/${projectId}/kanban-columns`)
}

export function createKanbanColumn(projectId: string, data: KanbanColumnCreate): Promise<KanbanColumn> {
  return api.post<KanbanColumn>(`/projects/${projectId}/kanban-columns`, data)
}

export function updateKanbanColumn(columnId: string, data: KanbanColumnUpdate): Promise<KanbanColumn> {
  return api.patch<KanbanColumn>(`/kanban-columns/${columnId}`, data)
}

export function deleteKanbanColumn(columnId: string): Promise<void> {
  return api.delete(`/kanban-columns/${columnId}`)
}
