import { api } from './client'
import type { ProjectMember } from '@/types'

export function listMembers(projectId: string): Promise<ProjectMember[]> {
  return api.get<ProjectMember[]>(`/projects/${projectId}/members`)
}

export function addMember(projectId: string, userId: string, role: string): Promise<ProjectMember> {
  return api.post<ProjectMember>(`/projects/${projectId}/members`, { user_id: userId, role })
}

export function updateMemberRole(
  projectId: string,
  userId: string,
  role: string,
): Promise<ProjectMember> {
  return api.patch<ProjectMember>(`/projects/${projectId}/members/${userId}`, { role })
}

export function removeMember(projectId: string, userId: string): Promise<void> {
  return api.delete<void>(`/projects/${projectId}/members/${userId}`)
}
