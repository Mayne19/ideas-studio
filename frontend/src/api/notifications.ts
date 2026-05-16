import { api } from './client'
import type { Notification } from '@/types'

export function listNotifications(projectId: string): Promise<Notification[]> {
  return api.get<Notification[]>(`/projects/${projectId}/notifications`)
}

export function markNotificationRead(notificationId: string): Promise<Notification> {
  return api.post<Notification>(`/notifications/${notificationId}/read`)
}

export function markAllNotificationsRead(projectId: string): Promise<{ marked_read: number }> {
  return api.post<{ marked_read: number }>(`/projects/${projectId}/notifications/read-all`)
}
