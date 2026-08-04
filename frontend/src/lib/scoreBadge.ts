export function finiteScore(value: unknown): number | null {
  if (typeof value !== 'number') return null
  return Number.isFinite(value) ? value : null
}

export function scoreTone(value: number | null, valid?: boolean | null): string {
  if (valid === false) return 'border-warning/20 bg-warning/8 text-warning'
  if (value === null) return 'border-border bg-surface-soft text-tertiary'
  if (value >= 85) return 'border-success/20 bg-success/8 text-success'
  if (value >= 70) return 'border-warning/20 bg-warning/8 text-warning'
  if (value >= 50) return 'border-warning/20 bg-warning/8 text-warning'
  return 'border-border bg-surface-soft text-tertiary'
}
