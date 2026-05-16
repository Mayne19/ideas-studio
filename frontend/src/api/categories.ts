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

export type SyncResult = {
  categories: Category[]
  message: string
}

export async function syncCategories(projectId: string): Promise<SyncResult> {
  const res = await fetch(`${import.meta.env['VITE_API_URL']}/projects/${projectId}/categories/sync`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token')}`,
    },
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({})) as { detail?: string }
    throw new Error(data.detail || `Erreur ${res.status}`)
  }

  const categories: Category[] = await res.json()
  const message = res.headers.get('X-Sync-Message') || `${categories.length} categorie(s) synchronisee(s).`
  return { categories, message }
}
