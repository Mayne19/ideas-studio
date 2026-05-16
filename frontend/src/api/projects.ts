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
  audience?: string
  tone?: string
}

export type UpdateProjectPayload = {
  name?: string
  domain?: string
  language?: string
  country_target?: string
  audience?: string
  tone?: string
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
