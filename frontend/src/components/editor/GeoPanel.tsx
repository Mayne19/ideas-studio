import { Globe, CheckCircle, HelpCircle, TrendingUp } from '@/components/ui/hugeIcons'
import type { EditorArticle } from '@/types'

export default function GeoPanel({ article }: { article: EditorArticle }) {
  const geo = article.geo_optimization_json as Record<string, unknown> | null

  if (!geo) {
    return (
      <div className="rounded-[10px] border border-border bg-surface p-3 text-[12px] text-tertiary">
        Aucune analyse GEO disponible.
      </div>
    )
  }

  const score = geo.geo_score as number | undefined
  const status = geo.status as string | undefined
  const checks = geo.checks as Array<Record<string, unknown>> | undefined
  const recommendations = geo.recommendations as string[] | undefined

  const statusLabel = status === 'good' ? 'Bon' : status === 'needs_improvement' ? 'À améliorer' : 'Faible'
  const statusColor = status === 'good' ? 'text-success' : status === 'needs_improvement' ? 'text-warning' : 'text-danger'

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5 text-[12px] font-medium text-primary">
        <Globe size={14} /> Optimisation GEO
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-[8px] border border-border bg-surface-soft px-2.5 py-2">
          <div className="text-[10px] text-tertiary">Score GEO</div>
          <div className={`text-[14px] font-medium ${statusColor}`}>
            {score != null ? `${score}/100` : '—'}
          </div>
        </div>
        <div className="rounded-[8px] border border-border bg-surface-soft px-2.5 py-2">
          <div className="text-[10px] text-tertiary">Statut</div>
          <div className={`text-[14px] font-medium ${statusColor}`}>{statusLabel}</div>
        </div>
      </div>

      {checks && checks.length > 0 && (
        <div className="flex flex-col gap-1">
          <div className="text-[12px] text-secondary font-medium">Vérifications</div>
          {checks.map((c, i) => {
            const passed = c.passed as boolean
            const label = c.label as string
            const comment = c.comment as string
            return (
              <div key={i} className="flex items-start gap-1.5 rounded-[6px] border border-border px-2 py-1.5">
                {passed
                  ? <CheckCircle size={10} className="mt-0.5 shrink-0 text-success" />
                  : <HelpCircle size={10} className="mt-0.5 shrink-0 text-warning" />
                }
                <div>
                  <div className="text-[10px] font-medium text-primary">{label}</div>
                  <div className="text-[9px] text-tertiary">{comment}</div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {recommendations && recommendations.length > 0 && (
        <div className="flex flex-col gap-1 rounded-[8px] bg-warning/5 px-2.5 py-2">
          <div className="text-[10px] font-medium text-warning">Recommandations</div>
          {recommendations.map((r, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[10px] text-warning">
              <TrendingUp size={10} className="mt-0.5 shrink-0" />
              <span>{r}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
