import type { Article } from '@/types'

export function finiteScore(value: unknown): number | null {
  if (typeof value !== 'number') return null
  return Number.isFinite(value) ? value : null
}

export function scoreTone(value: number | null, valid?: boolean | null): string {
  if (valid === false) return 'bg-warning/10 text-[#9B6B19]'
  if (value === null) return 'bg-[#f0f0f2] text-tertiary'
  if (value >= 85) return 'bg-success/10 text-[#1a7a3a]'
  if (value >= 70) return 'bg-warning/10 text-[#9B6B19]'
  if (value >= 50) return 'bg-orange-500/10 text-orange-600'
  return 'bg-[#f0f0f2] text-tertiary'
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
