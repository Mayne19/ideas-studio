export function formatMetric(value: number, compact = false) {
  if (!Number.isFinite(value)) return '0'
  if (!compact) return Math.round(value).toLocaleString('fr-FR')
  return Intl.NumberFormat('fr-FR', {
    notation: 'compact',
    maximumFractionDigits: value >= 10000 ? 0 : 1,
  }).format(value)
}

export function formatAxisTick(value: number | string) {
  const numeric = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(numeric) ? formatMetric(numeric, numeric >= 1000) : String(value)
}

export function percentOf(value: number, total: number) {
  if (!total) return 0
  return Math.max(0, Math.min(100, Math.round((value / total) * 100)))
}

function cleanDomain(value: string) {
  const raw = value.trim()
  if (!raw) return ''
  try {
    return new URL(raw.startsWith('http') ? raw : `https://${raw}`).hostname.replace(/^www\./, '')
  } catch {
    return raw.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0] ?? raw
  }
}

export function getSourceDisplay(referrer: string) {
  const domain = cleanDomain(referrer)
  if (!domain) return { label: 'Direct', kind: 'direct', domain: '' }
  if (domain.includes('google.')) return { label: 'Google', kind: 'google', domain }
  if (domain.includes('linkedin.')) return { label: 'LinkedIn', kind: 'linkedin', domain }
  if (domain.includes('twitter.') || domain.includes('x.com')) return { label: 'X / Twitter', kind: 'x', domain }
  if (domain.includes('facebook.') || domain.includes('fb.')) return { label: 'Facebook', kind: 'facebook', domain }
  if (domain.includes('reddit.')) return { label: 'Reddit', kind: 'reddit', domain }
  return { label: domain, kind: 'domain', domain }
}

export function getSourceChannel(referrer: string) {
  const source = getSourceDisplay(referrer)
  if (source.kind === 'google') return 'Organic Search'
  if (source.kind === 'direct') return 'Direct'
  if (source.kind === 'linkedin' || source.kind === 'x' || source.kind === 'facebook' || source.kind === 'reddit') return 'Social'
  return 'Referral'
}

export function getFaviconUrl(domain: string) {
  return domain ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=32` : null
}

const COUNTRY_LABELS: Record<string, { flag: string; label: string }> = {
  FR: { flag: '🇫🇷', label: 'France' },
  France: { flag: '🇫🇷', label: 'France' },
  BE: { flag: '🇧🇪', label: 'Belgique' },
  Belgique: { flag: '🇧🇪', label: 'Belgique' },
  CH: { flag: '🇨🇭', label: 'Suisse' },
  Suisse: { flag: '🇨🇭', label: 'Suisse' },
  CA: { flag: '🇨🇦', label: 'Canada' },
  Canada: { flag: '🇨🇦', label: 'Canada' },
  MA: { flag: '🇲🇦', label: 'Maroc' },
  Maroc: { flag: '🇲🇦', label: 'Maroc' },
  US: { flag: '🇺🇸', label: 'États-Unis' },
  DE: { flag: '🇩🇪', label: 'Allemagne' },
  GB: { flag: '🇬🇧', label: 'Royaume-Uni' },
}

function flagFromCountryCode(value: string) {
  const code = value.toUpperCase()
  if (!/^[A-Z]{2}$/.test(code)) return null
  return code
    .split('')
    .map((letter) => String.fromCodePoint(127397 + letter.charCodeAt(0)))
    .join('')
}

export function getCountryDisplay(country: string) {
  const key = country.trim()
  if (!key) return { flag: '•', label: 'Inconnu' }
  const known = COUNTRY_LABELS[key] ?? COUNTRY_LABELS[key.toUpperCase()]
  if (known) return known
  return { flag: flagFromCountryCode(key) ?? '•', label: key }
}

export function getDeviceLabel(device: string) {
  const normalized = device.toLowerCase()
  if (normalized === 'desktop') return 'Ordinateur'
  if (normalized === 'mobile') return 'Mobile'
  if (normalized === 'tablet') return 'Tablette'
  return device || 'Inconnu'
}
