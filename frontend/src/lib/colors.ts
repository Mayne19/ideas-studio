import { amber, blue, crimson, cyan, grass, indigo, orange, plum, slate, teal, tomato, violet } from '@radix-ui/colors'

export const RADIX_COLOR_SWATCHES = [
  { name: 'Bleu', value: blue.blue9 },
  { name: 'Indigo', value: indigo.indigo9 },
  { name: 'Violet', value: violet.violet9 },
  { name: 'Prune', value: plum.plum9 },
  { name: 'Cyan', value: cyan.cyan9 },
  { name: 'Teal', value: teal.teal9 },
  { name: 'Vert', value: grass.grass9 },
  { name: 'Ambre', value: amber.amber9 },
  { name: 'Orange', value: orange.orange9 },
  { name: 'Tomate', value: tomato.tomato9 },
  { name: 'Crimson', value: crimson.crimson9 },
  { name: 'Slate', value: slate.slate9 },
]

export const PALETTE_COLORS = RADIX_COLOR_SWATCHES.map((color) => color.value)
export const DEFAULT_ACCENT_COLOR = blue.blue9

export function isValidHexColor(value: string | null | undefined): value is string {
  return typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value)
}

export function normalizeHexColor(value: string | null | undefined, fallback = DEFAULT_ACCENT_COLOR): string {
  return isValidHexColor(value) ? value.toLowerCase() : fallback
}
