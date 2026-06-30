import { AlertCircle, DollarSign, TrendingUp, HelpCircle } from '@/components/ui/hugeIcons'
import type { EditorArticle } from '@/types'

export default function CostPanel({ article }: { article: EditorArticle }) {
  const report = article.generation_report_json as Record<string, unknown> | null
  if (!report) {
    return (
      <div className="rounded-[10px] border border-border bg-surface p-3 text-[12px] text-tertiary">
        Aucun coût enregistré pour cet article.
      </div>
    )
  }

  const est = report.estimated_cost_eur as number | null | undefined
  const act = report.actual_cost_eur as number | null | undefined
  const limit = report.cost_limit_eur as number | null | undefined
  const costStatus = report.cost_status as string | undefined
  const breakdown = report.cost_breakdown_json as Array<Record<string, unknown>> | undefined
  const warnings = report.cost_warnings as string[] | undefined

  const isOverLimit = costStatus === 'over_limit'
  const hasUnknown = costStatus === 'partial_unknown' || costStatus === 'not_tracked'

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5 text-[12px] font-medium text-primary">
        <DollarSign size={14} /> Coûts IA
      </div>

      {isOverLimit && (
        <div className="flex items-start gap-2 rounded-[8px] border border-danger/20 bg-danger/5 px-2.5 py-2 text-[12px] text-danger">
          <AlertCircle size={12} className="mt-0.5 shrink-0" />
          <span className="leading-snug">Limite de coût dépassée.</span>
        </div>
      )}

      {hasUnknown && (
        <div className="flex items-start gap-2 rounded-[8px] border border-warning/20 bg-warning/5 px-2.5 py-2 text-[12px] text-warning">
          <HelpCircle size={12} className="mt-0.5 shrink-0" />
          <span className="leading-snug">Certains prix de modèles ne sont pas configurés.</span>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-[8px] border border-border bg-surface-soft px-2.5 py-2">
          <div className="text-[10px] text-tertiary">Estimé</div>
          <div className="text-[14px] font-medium text-primary">
            {est != null ? `${est.toFixed(4)} €` : '—'}
          </div>
        </div>
        <div className="rounded-[8px] border border-border bg-surface-soft px-2.5 py-2">
          <div className="text-[10px] text-tertiary">Réel</div>
          <div className="text-[14px] font-medium text-primary">
            {act != null ? `${act.toFixed(4)} €` : '—'}
          </div>
        </div>
      </div>

      {limit != null && (
        <div className="flex items-center justify-between text-[12px]">
          <span className="text-tertiary">Limite</span>
          <span className="text-primary">{limit.toFixed(2)} €</span>
        </div>
      )}

      {warnings && warnings.length > 0 && (
        <div className="flex flex-col gap-1 rounded-[8px] bg-warning/5 px-2.5 py-2">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[10px] text-warning">
              <TrendingUp size={10} className="mt-0.5 shrink-0" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {breakdown && breakdown.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-[12px] text-secondary hover:text-primary transition-colors">
            Détail par agent ({breakdown.length})
          </summary>
          <div className="mt-2 flex flex-col gap-1">
            {breakdown.map((b, i) => (
              <div key={i} className="rounded-[6px] border border-border px-2 py-1.5 text-[10px]">
                <div className="flex items-center justify-between">
                  <span className="font-medium text-primary">{b.agent_key as string}</span>
                  <span className="text-tertiary">
                    {b.actual_cost_eur != null
                      ? `${(b.actual_cost_eur as number).toFixed(4)} €`
                      : b.estimated_cost_eur != null
                        ? `~${(b.estimated_cost_eur as number).toFixed(4)} €`
                        : '—'}
                  </span>
                </div>
                <div className="text-tertiary">
                  {b.provider as string}/{b.model as string}
                  {b.input_tokens != null && ` · ${b.input_tokens}i/${b.output_tokens}o tok`}
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  )
}
