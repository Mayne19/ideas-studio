import { api } from './client'

export type IllustrationMode = 'ai' | 'unsplash' | 'none'

export type IllustrationOption = {
  code: string
  label: string
  approx_cost_usd: number | null
}

export type IllustrationConfig = {
  model: string
  style_preset: string
  custom_style: string
  primary_color: string
  secondary_color: string
  max_images: number
}

export type IllustrationSettings = {
  project_id: string | null
  configured: boolean
  effective_source: 'project' | 'global' | 'default'
  mode: IllustrationMode
  config: IllustrationConfig
  modes: IllustrationOption[]
  models: IllustrationOption[]
  style_presets: IllustrationOption[]
  max_images_limit: number
  openrouter_configured: boolean
}

export type IllustrationPreview = {
  image_data_url: string
  prompt: string
  model: string
  cost_usd: number | null
}

function scope(projectId?: string): string {
  return projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''
}

export function getIllustrationSettings(projectId?: string): Promise<IllustrationSettings> {
  return api.get<IllustrationSettings>(`/settings/illustrations${scope(projectId)}`)
}

export function saveIllustrationSettings(
  mode: IllustrationMode,
  config: IllustrationConfig,
  projectId?: string,
): Promise<IllustrationSettings> {
  return api.put<IllustrationSettings>(`/settings/illustrations${scope(projectId)}`, { mode, config })
}

/** Génère une image d'essai avec les réglages saisis (non enregistrés). */
export function previewIllustration(config: IllustrationConfig, projectId?: string, subject?: string): Promise<IllustrationPreview> {
  // Génération d'image : souvent 10 à 40 s, au-delà du délai API par défaut.
  return api.post<IllustrationPreview>(
    `/settings/illustrations/preview${scope(projectId)}`,
    { config, subject: subject || null },
    { timeoutMs: 120000 },
  )
}
