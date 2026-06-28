import type { Article } from '@/types'

export function finiteScore(value: unknown): number | null {
  if (typeof value !== 'number') return null
  return Number.isFinite(value) ? value : null
}

export function scoreTone(value: number | null, valid?: boolean | null): string {
  if (valid === false) return 'bg-warning/10 text-warning'
  if (value === null) return 'bg-surface-soft text-tertiary'
  if (value >= 85) return 'bg-success/10 text-success'
  if (value >= 70) return 'bg-warning/10 text-warning'
  if (value >= 50) return 'bg-warning/10 text-warning'
  return 'bg-surface-soft text-tertiary'
}

export function getOriginalityScore(article: Article | null | undefined): number | null {
  if (!article) return null
  const report = article.originality_report_json
  if (!report || typeof report !== 'object') return null
  const score = (report as Record<string, unknown>).heuristic_score
  return typeof score === 'number' && Number.isFinite(score) ? score : null
}

export function getGeoScore(article: Article | null | undefined): number | null {
  if (!article) return null
  const report = article.geo_optimization_json
  if (!report || typeof report !== 'object') return null
  const raw = (report as Record<string, unknown>)
  const score = raw.geo_score ?? raw.score
  return typeof score === 'number' && Number.isFinite(score) ? score : null
}
