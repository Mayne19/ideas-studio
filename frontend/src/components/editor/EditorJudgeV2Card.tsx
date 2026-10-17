// Note du juge v2 (grille du rédacteur en chef, app/services/seo/editorial_judge_v2.py) :
// total sur 100, note par critère, plafonds des fautes graves. Affichée « non étalonné »
// tant que l'étalonnage sur les notes humaines n'est pas validé.

type Criterion = { score: number; max: number; evidence?: string }
type GraveFault = { type: string; passage?: string; detail?: string }
type JudgeV2 = {
  total?: number
  raw_total?: number
  status?: string
  error?: string
  criteria?: Record<string, Criterion>
  caps?: { grave_faults: number; cap: number | null }
  grave_faults?: GraveFault[]
  summary?: string
}

const CRITERIA_LABELS: Record<string, string> = {
  accuracy_sources: 'Exactitude et sources (E-E-A-T)',
  information_gain: "Apport d'information et originalité",
  readability: 'Lisibilité et clarté',
  intent: 'Réponse et intention',
  introduction: 'Introduction',
  structure: 'Structure et promesses',
  tone: 'Ton et engagement',
  faq: 'FAQ',
  seo: 'SEO technique',
  form: 'Forme',
}

const GRAVE_LABELS: Record<string, string> = {
  false_fact: 'Fait faux',
  central_contradiction: 'Contradiction sur le conseil central',
  competitor_named: 'Concurrent nommé',
  unsourced_health_figure: 'Chiffre de santé sans source',
}

export default function EditorJudgeV2Card({ judgement }: { judgement: Record<string, unknown> | null }) {
  if (!judgement) return null
  const j = judgement as JudgeV2
  if (j.error) {
    return (
      <div className="rounded-[10px] border border-border px-3 py-2.5 text-[12px] text-tertiary">
        Juge v2 indisponible : {j.error}
      </div>
    )
  }
  const criteria = Object.entries(j.criteria ?? {})
  return (
    <div className="rounded-[10px] border border-border px-3 py-3">
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <p className="text-[13px] font-medium text-primary">Note du rédacteur en chef (juge v2)</p>
        <p className="text-[18px] font-semibold text-primary">
          {j.total ?? '-'}<span className="text-[12px] font-normal text-tertiary">/100</span>
        </p>
      </div>
      <p className="mb-3 text-[11px] text-tertiary">
        {j.status === 'étalonné' ? 'Étalonné sur les notes humaines.' : 'Non étalonné : à titre indicatif.'}
        {j.caps?.cap != null && ` Plafonnée à ${j.caps.cap} (${j.caps.grave_faults} faute(s) grave(s), ${j.raw_total} avant plafond).`}
      </p>
      <ul className="flex flex-col gap-2">
        {criteria.map(([key, c]) => (
          <li key={key} title={c.evidence ?? ''}>
            <div className="flex justify-between text-[12px] text-secondary">
              <span>{CRITERIA_LABELS[key] ?? key}</span>
              <span className="text-primary">{c.score}/{c.max}</span>
            </div>
            <div className="mt-1 h-1.5 rounded-full bg-surface-soft">
              <div className="h-1.5 rounded-full bg-primary"
                style={{ width: `${c.max ? Math.round((c.score / c.max) * 100) : 0}%` }} />
            </div>
          </li>
        ))}
      </ul>
      {(j.grave_faults ?? []).length > 0 && (
        <div className="mt-3 flex flex-col gap-1.5">
          <p className="text-[12px] font-medium text-danger">Fautes graves</p>
          {(j.grave_faults ?? []).map((g, i) => (
            <p key={i} className="text-[11px] text-secondary">
              <span className="font-medium">{GRAVE_LABELS[g.type] ?? g.type}</span>
              {g.passage ? ` : « ${g.passage} »` : ''}{g.detail ? ` (${g.detail})` : ''}
            </p>
          ))}
        </div>
      )}
      {j.summary && <p className="mt-3 text-[11px] text-tertiary">{j.summary}</p>}
    </div>
  )
}
