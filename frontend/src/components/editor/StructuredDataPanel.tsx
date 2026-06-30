import { Code, AlertCircle, CheckCircle } from '@/components/ui/hugeIcons'
import type { EditorArticle } from '@/types'

export default function StructuredDataPanel({ article }: { article: EditorArticle }) {
  const sd = article.structured_data_json as Record<string, unknown> | null

  if (!sd) {
    return (
      <div className="rounded-[10px] border border-border bg-surface p-3 text-[12px] text-tertiary">
        Aucune donnée structurée générée.
      </div>
    )
  }

  const schemas = sd.schemas as Array<Record<string, unknown>> | undefined
  const status = sd.status as string | undefined
  const warnings = sd.warnings as string[] | undefined
  const schemaCount = sd.schema_count as number | undefined

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5 text-[12px] font-medium text-primary">
        <Code size={14} /> Données structurées
      </div>

      <div className="flex items-center justify-between text-[12px]">
        <span className="text-tertiary">Statut</span>
        <span className={status === 'generated' ? 'text-success' : 'text-tertiary'}>
          {status === 'generated' ? 'Généré' : 'Vide'}
        </span>
      </div>

      {schemaCount != null && (
        <div className="flex items-center justify-between text-[12px]">
          <span className="text-tertiary">Schémas</span>
          <span className="text-primary">{schemaCount}</span>
        </div>
      )}

      {warnings && warnings.length > 0 && (
        <div className="flex flex-col gap-1">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-1.5 rounded-[6px] bg-warning/5 px-2 py-1.5 text-[10px] text-warning">
              <AlertCircle size={10} className="mt-0.5 shrink-0" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}

      {schemas && schemas.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer text-[12px] text-secondary hover:text-primary transition-colors">
            Voir le JSON ({schemas.length} schéma{schemas.length > 1 ? 's' : ''})
          </summary>
          <pre className="mt-2 max-h-48 overflow-auto rounded-[6px] bg-[#1d1d1f] p-2 text-[10px] leading-relaxed text-[#f0f0f2]">
            {JSON.stringify(sd, null, 2)}
          </pre>
        </details>
      )}

      {schemas?.map((s, i) => {
        const type = s['@type'] as string | undefined
        return (
          <div key={i} className="flex items-center gap-1.5 text-[10px] text-secondary">
            <CheckCircle size={10} className="text-success shrink-0" />
            <span>{type || 'Schéma'}</span>
          </div>
        )
      })}
    </div>
  )
}
