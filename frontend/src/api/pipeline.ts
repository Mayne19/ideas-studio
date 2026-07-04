import { api } from './client'

export type PipelineRunStatus = 'running' | 'success' | 'partial_success' | 'failed'

export type PipelineSettings = {
  id: string
  project_id: string
  enabled: boolean
  active_days: string[]
  launch_hour: number
  ideas_day_of_month: number | null
  publish_hour_start: number
  publish_hour_end: number
  articles_per_week: number
  category_priorities: Record<string, number>
  cost_limit_per_article_eur: number | null
  max_parallel_writing_jobs?: number | null
  total_monthly_from_categories: number | null
  categories_frequencies: Array<{
    id: string
    name: string
    monthly_frequency: number | null
    pipeline_enabled: boolean | null
    priority: number
  }>
  automation_notes: string
  created_at: string
  updated_at: string
}

export type PipelineSettingsUpdate = {
  enabled?: boolean
  max_parallel_writing_jobs?: number
  active_days?: string[]
  launch_hour?: number
  ideas_day_of_month?: number | null
  publish_hour_start?: number
  publish_hour_end?: number
  articles_per_week?: number
  category_priorities?: Record<string, number>
  cost_limit_per_article_eur?: number | null
}

export type PipelineLog = {
  id: string
  project_id: string
  status: PipelineRunStatus
  workflow_run_id: string | null
  expected_ideas: number
  generated_ideas: number
  failed_categories: Array<{
    category_id?: string | null
    category_name?: string | null
    expected: number
    generated: number
    errors: string[]
  }>
  run_errors: string[]
  ideas_generated: number
  articles_created: number
  errors: string | null
  started_at: string
  finished_at: string | null
}

export type PipelineRunResult = {
  status: PipelineRunStatus
  workflow_run_id: string
  expected_ideas: number
  generated_ideas: number
  total_expected_ideas: number
  total_generated_ideas: number
  ideas_generated: number
  articles_created: number
  categories_processed: Array<{
    category_id: string
    category_name: string
    expected: number
    generated: number
    errors: string[]
  }>
  failed_categories: Array<{
    category_id?: string | null
    category_name?: string | null
    expected: number
    generated: number
    errors: string[]
  }>
  errors: string[]
  started_at: string
  finished_at: string | null
  pipeline_mode: string
}

export function pipelineStatusLabel(status: string): string {
  if (status === 'success') return 'Succès'
  if (status === 'partial_success') return 'Partiel'
  if (status === 'running') return 'En cours'
  return 'Échec'
}

export function pipelineStatusTone(status: string): 'success' | 'warning' | 'danger' | 'secondary' {
  if (status === 'success') return 'success'
  if (status === 'partial_success') return 'warning'
  if (status === 'failed') return 'danger'
  return 'secondary'
}

function translateRunError(error: string): string {
  const pending = error.match(/^Max pending drafts reached \((\d+)\/(\d+)\)/)
  if (pending) {
    return `Limite de brouillons en attente atteinte (${pending[1]}/${pending[2]}). Validez, annulez ou supprimez des brouillons en production, ou augmentez la limite dans Paramètres → Pipeline.`
  }
  if (error.startsWith('Pipeline is paused')) {
    return 'Le pipeline est en pause. Réactivez-le dans Paramètres → Pipeline.'
  }
  return error
}

export function pipelineRunMessage(result: Pick<PipelineRunResult, 'status' | 'expected_ideas' | 'generated_ideas' | 'failed_categories' | 'errors'>): string {
  if (result.status === 'running') return 'Exécution en cours…'
  if (result.status === 'success') return `${result.generated_ideas} idée(s) générée(s) avec succès.`
  if (result.status === 'partial_success') {
    const failed = result.failed_categories.length
    return `${result.generated_ideas} idée(s) générée(s), ${failed || Math.max(0, result.expected_ideas - result.generated_ideas)} catégorie(s) en erreur.`
  }
  const firstError = result.errors?.[0]
    ?? result.failed_categories?.find((c) => c.errors?.length)?.errors?.[0]
  if (firstError) return `Aucune idée générée : ${translateRunError(firstError)}`
  return 'Aucune idée générée. Consultez le journal du pipeline pour le détail.'
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
