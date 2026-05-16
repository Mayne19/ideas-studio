import { DEFAULT_ACCENT_COLOR, normalizeHexColor } from '@/lib/colors'

function hexToRgb(hex: string) {
  const normalized = normalizeHexColor(hex, DEFAULT_ACCENT_COLOR).replace('#', '')
  const value = Number.parseInt(normalized, 16)
  return {
    r: (value >> 16) & 255,
    g: (value >> 8) & 255,
    b: value & 255,
  }
}

function rgbToHex({ r, g, b }: { r: number; g: number; b: number }) {
  return `#${[r, g, b].map((channel) => Math.max(0, Math.min(255, Math.round(channel))).toString(16).padStart(2, '0')).join('')}`
}

function mix(hex: string, target: string, amount: number) {
  const source = hexToRgb(hex)
  const destination = hexToRgb(target)
  return rgbToHex({
    r: source.r + (destination.r - source.r) * amount,
    g: source.g + (destination.g - source.g) * amount,
    b: source.b + (destination.b - source.b) * amount,
  })
}

function relativeLuminance(hex: string) {
  const { r, g, b } = hexToRgb(hex)
  const channels = [r, g, b].map((value) => {
    const srgb = value / 255
    return srgb <= 0.03928 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

export function slugifyCalloutLabel(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80) || 'callout'
}

export function deriveCalloutColors(primaryColor: string) {
  const border = normalizeHexColor(primaryColor, DEFAULT_ACCENT_COLOR)
  const background = mix(border, '#ffffff', 0.9)
  const text = relativeLuminance(border) > 0.4 ? mix(border, '#111111', 0.72) : mix(border, '#111111', 0.28)
  return {
    color_background: background,
    color_border: border,
    color_text: text,
  }
}
