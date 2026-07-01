export const NEUTRAL_CHART_COLORS = {
  primary: '#2E2E2E',
  secondary: '#5E5E5E',
  tertiary: '#8A8A8A',
  muted: '#D7D7D7',
} as const

export const SEMANTIC_COLORS = {
  success: '#008A2E',
  warning: '#A35200',
  danger: '#E5484D',
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
