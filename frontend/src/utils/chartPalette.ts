export const NEUTRAL_CHART_COLORS = {
  primary: '#111827',
  secondary: '#4b5563',
  tertiary: '#9ca3af',
  muted: '#d1d5db',
} as const

export const SEMANTIC_COLORS = {
  success: '#00a63e',
  warning: '#f59e0b',
  danger: '#ef4444',
} as const

export const COUNTRY_PALETTE = [
  NEUTRAL_CHART_COLORS.primary,
  NEUTRAL_CHART_COLORS.secondary,
  NEUTRAL_CHART_COLORS.tertiary,
  NEUTRAL_CHART_COLORS.muted,
  '#6b7280',
  '#374151',
  '#1f2937',
  '#e5e5e5',
] as const

export const DEVICE_COLORS = {
  desktop: NEUTRAL_CHART_COLORS.primary,
  mobile: NEUTRAL_CHART_COLORS.secondary,
  tablet: NEUTRAL_CHART_COLORS.tertiary,
} as const

export function scoreColor(score: number | null | undefined): string {
  if (score === null || score === undefined) return NEUTRAL_CHART_COLORS.tertiary
  if (score >= 75) return SEMANTIC_COLORS.success
  if (score >= 50) return SEMANTIC_COLORS.warning
  return SEMANTIC_COLORS.danger
}
