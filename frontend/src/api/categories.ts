import { api } from './client'
import type { Category } from '@/types'

export type CreateCategoryPayload = {
  name: string
  description?: string
  color?: string | null
  priority?: number
  target_frequency?: number | null
  monthly_frequency?: number | null
  pipeline_enabled?: boolean
  target_audience?: string | null
  editorial_goal?: string | null
}

export type UpdateCategoryPayload = {
  name?: string
  description?: string | null
  color?: string | null
  priority?: number
  target_frequency?: number | null
  monthly_frequency?: number | null
  pipeline_enabled?: boolean
  target_audience?: string | null
  editorial_goal?: string | null
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

export type SyncResult = {
  categories: Category[]
  message: string
}

export async function syncCategories(projectId: string): Promise<SyncResult> {
  const categories = await api.post<Category[]>(`/projects/${projectId}/categories/sync`)
  const message = `${categories.length} categorie(s) synchronisee(s).`
  return { categories, message }
}
