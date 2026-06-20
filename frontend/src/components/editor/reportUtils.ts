export function tryParseJson(val: unknown): Record<string, unknown> {
  if (typeof val === 'string') {
    try { return JSON.parse(val) } catch { return { raw: val } }
  }
  if (val && typeof val === 'object') return val as Record<string, unknown>
  return {}
}
