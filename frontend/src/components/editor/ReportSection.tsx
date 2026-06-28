import type { ReactNode } from 'react'
import { tryParseJson } from './reportUtils'

function formatReportValue(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Oui' : 'Non'
  if (typeof value === 'number') return String(value)
  if (typeof value === 'string') {
    if (value.length > 120) return value.slice(0, 120) + '…'
    return value
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '[]'
    if (value.length <= 3) return value.map((v) => formatReportValue(v)).join(', ')
    return `${value.length} éléments`
  }
  if (typeof value === 'object') {
    const keys = Object.keys(value as Record<string, unknown>)
    if (keys.length === 0) return '{}'
    return `{${keys.slice(0, 4).join(', ')}${keys.length > 4 ? ', …' : ''}}`
  }
  return String(value)
}

function ReportField({ label, value }: { label: string; value: unknown }) {
  const display = formatReportValue(value)
  return (
    <div className="text-[10px] leading-snug">
      <span className="font-medium text-secondary">{label}: </span>
      <span className="text-primary">{display}</span>
    </div>
  )
}

export function ReportSection({ title, data }: { title: string; data: unknown }) {
  const parsed = tryParseJson(data)
  const entries = Object.entries(parsed).filter(([k]) => !k.startsWith('_'))

  return (
    <details className="group rounded-[6px] border border-border bg-surface">
      <summary className="flex cursor-pointer items-center justify-between px-3 py-2 text-[11px] font-medium text-secondary hover:text-primary">
        <span>{title}</span>
        <span className="text-[10px] text-tertiary">{entries.length} champs</span>
      </summary>
      <div className="max-h-[300px] overflow-y-auto border-t border-border px-3 py-2">
        {entries.length === 0 ? (
          <p className="text-[10px] text-tertiary">Aucune donnée structurée</p>
        ) : (
          <div className="flex flex-col gap-1.5">
            {entries.map(([key, value]) => (
              <ReportField key={key} label={key} value={value} />
            ))}
          </div>
        )}
      </div>
    </details>
  )
}

export function ReportGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">{title}</p>
      {children}
    </div>
  )
}
