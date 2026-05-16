import { api } from './client'
import type { Category } from '@/types'

export type CreateCategoryPayload = {
  name: string
  description?: string
  color?: string | null
  priority?: number
  target_frequency?: number | null
}

export type UpdateCategoryPayload = {
  name?: string
  description?: string | null
  color?: string | null
  priority?: number
  target_frequency?: number | null
}

export function listCategories(projectId: string): Promise<Category[]> {
  return api.get<Category[]>(`/projects/${projectId}/categories`)
}

export function createCategory(projectId: string, payload: CreateCategoryPayload): Promise<Category> {
  return api.post<Category>(`/projects/${projectId}/categories`, payload)
}

export function updateCategory(_projectId: string, categoryId: string, payload: UpdateCategoryPayload): Promise<Category> {
  return api.patch<Category>(`/categories/${categoryId}`, payload)
}

export function deleteCategory(_projectId: string, categoryId: string): Promise<void> {
  return api.delete<void>(`/categories/${categoryId}`)
}

export function syncCategories(projectId: string): Promise<Category[]> {
  return api.post<Category[]>(`/projects/${projectId}/categories/sync`)
}
