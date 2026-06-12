import { useState } from 'react'
import { AlertCircle, AlertTriangle, Info, RefreshCw, CheckCircle, XCircle, MinusCircle, HelpCircle } from 'lucide-react'
import { analyzeArticle, readyCheck, runSeoExpertReview } from '@/api/seo'
import { ApiError } from '@/api/client'
import type { SeoAnalysis, SeoIssue, ReadyCheck, EditorArticle, SeoExpertIssue, SeoExpertReview } from '@/types'
import Button from '@/components/ui/Button'

function translateSeoError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 403: return 'Permission refusee pour cette analyse.'
      case 404: return "Article introuvable pour cet audit."
      case 409: return 'Une analyse est deja en cours.'
      case 422: return "Contenu invalide. Verifiez que l'article a un titre et du contenu."
      case 500: return "Erreur serveur lors de l'analyse. Reessayez dans quelques instants."
      default: return err.message || `Erreur ${err.status}`
    }
  }
  return "Impossible de lancer l'analyse. Verifiez votre connexion."
}

const CATEGORY_LABELS: Record<string, string> = {
  seo: 'SEO',
  readability: 'Lisibilite',
  quality: 'Qualite',
  eeat: 'E-E-A-T',
  meta: 'Meta',
  links: 'Liens',
  images: 'Images',
  structure: 'Structure',
}

function ScoreRing({ label, score }: { label: string; score: number | null }) {
  const val = score ?? 0
  const color = val >= 70 ? '#31c96b' : val >= 40 ? '#ffad33' : '#ff6258'
  const r = 42
  const circ = 2 * Math.PI * r
  const dash = (val / 100) * circ

  return (
    <div className="flex flex-col items-center gap-1.5 rounded-[12px] border border-border bg-surface px-2 py-3">
      <svg width="112" height="112" viewBox="0 0 112 112" aria-label={`${label} ${Math.round(val)}`} className="text-primary">
        <circle cx="56" cy="56" r={r} fill="none" className="stroke-border" strokeWidth="9" />
        <circle
          cx="56"
          cy="56"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 56 56)"
          style={{ transition: 'stroke-dasharray 0.4s ease' }}
        />
        <text
          x="56"
          y="63"
          textAnchor="middle"
          fontSize="20"
          fontWeight="700"
          className="fill-current"
          style={{ fontFamily: 'inherit', letterSpacing: 0 }}
        >
          {val > 0 ? Math.round(val) : '-'}
        </text>
      </svg>
      <span className="text-[11px] font-semibold text-secondary">{label}</span>
    </div>
  )
}

function IssueItem({ issue }: { issue: SeoIssue }) {
  const icon =
    issue.severity === 'critical' ? <AlertCircle size={12} className="mt-0.5 shrink-0 text-danger" /> :
    issue.severity === 'warning' ? <AlertTriangle size={12} className="mt-0.5 shrink-0 text-warning" /> :
    <Info size={12} className="mt-0.5 shrink-0 text-accent" />

  return (
    <div className="flex gap-2 text-[11px]">
      {icon}
      <div>
        <p className="leading-snug text-primary">{issue.message}</p>
        {issue.suggestion && <p className="mt-0.5 leading-snug text-tertiary">{issue.suggestion}</p>}
      </div>
    </div>
  )
}

function ExpertIssueItem({ issue }: { issue: SeoExpertIssue }) {
  const icon =
    issue.severity === 'critical' ? <AlertCircle size={12} className="mt-0.5 shrink-0 text-danger" /> :
    issue.severity === 'warning' ? <AlertTriangle size={12} className="mt-0.5 shrink-0 text-warning" /> :
    <Info size={12} className="mt-0.5 shrink-0 text-accent" />

  return (
    <div className="flex gap-2 text-[11px]">
      {icon}
      <div>
        <p className="leading-snug text-primary">{issue.message}</p>
        <p className="mt-0.5 leading-snug text-tertiary">{issue.check}</p>
      </div>
    </div>
  )
}

function normalizeExpertReview(review: SeoExpertReview | null | undefined): SeoExpertReview | null {
  if (!review || typeof review !== 'object') return null
  return {
    score_global: typeof review.score_global === 'number' ? review.score_global : 0,
    seo_score: typeof review.seo_score === 'number' ? review.seo_score : 0,
    eeat_score: typeof review.eeat_score === 'number' ? review.eeat_score : 0,
    readability_score: typeof review.readability_score === 'number' ? review.readability_score : 0,
    issues: Array.isArray(review.issues) ? review.issues : [],
    recommendations: Array.isArray(review.recommendations) ? review.recommendations : [],
    passed_checks: Array.isArray(review.passed_checks) ? review.passed_checks : [],
    failed_checks: Array.isArray(review.failed_checks) ? review.failed_checks : [],
    knowledge_pack_sources: review.knowledge_pack_sources,
    diagnostics: review.diagnostics,
  }
}

function ReadinessBlock({ check, hasTitleH1 }: { check: ReadyCheck; hasTitleH1: boolean }) {
  const blockingIssues = hasTitleH1
    ? check.blocking_issues.filter((issue) => !isMissingH1Issue(issue))
    : check.blocking_issues
  const hasBlocking = blockingIssues.length > 0
  const config = check.can_publish || !hasBlocking
    ? { icon: <CheckCircle size={13} />, label: 'Publication readiness: pret ou a verifier', cls: 'bg-success/10 text-success' }
    : { icon: <XCircle size={13} />, label: 'Publication readiness: bloque', cls: 'bg-danger/8 text-danger' }

  return (
    <div className={`rounded-[10px] px-3 py-2.5 ${config.cls}`}>
      <p className="flex items-center gap-1.5 text-[12px] font-medium">
        {hasBlocking ? config.icon : <MinusCircle size={13} />}
        {config.label}
      </p>
      {hasBlocking && (
        <ul className="mt-2 flex flex-col gap-1">
          {blockingIssues.map((issue, i) => (
            <li key={i} className="text-[11px] leading-snug">- {issue.message}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function isMissingH1Issue(issue: SeoIssue): boolean {
  const text = `${issue.type} ${issue.message} ${issue.suggestion}`.toLowerCase()
  return text.includes('h1') && (text.includes('manquant') || text.includes('missing') || text.includes('sans'))
}

export default function SeoPanel({
  article,
  projectId,
  onBeforeAnalyze,
  initialAnalysis = null,
  initialReadiness = null,
  onAnalysisUpdate,
  onReadinessUpdate,
  onExpertReviewUpdate,
}: {
  article: EditorArticle
  projectId: string
  onBeforeAnalyze?: () => Promise<void> | void
  initialAnalysis?: SeoAnalysis | null
  initialReadiness?: ReadyCheck | null
  onAnalysisUpdate?: (analysis: SeoAnalysis) => void
  onReadinessUpdate?: (check: ReadyCheck) => void
  onExpertReviewUpdate?: (review: SeoExpertReview) => void
}) {
  const [analysis, setAnalysis] = useState<SeoAnalysis | null>(initialAnalysis)
  const [readiness, setReadiness] = useState<ReadyCheck | null>(initialReadiness)
  const [expertReviewOverride, setExpertReviewOverride] = useState<SeoExpertReview | null>(null)
  const [loading, setLoading] = useState(false)
  const [expertLoading, setExpertLoading] = useState(false)
  const [error, setError] = useState('')
  const [expertError, setExpertError] = useState('')
  const [expertSuccess, setExpertSuccess] = useState('')
  const expertReview = normalizeExpertReview(expertReviewOverride ?? article.seo_review_json ?? null)

  const brief = analysis ?? article.latest_analysis
  const hasTitleH1 = Boolean(article.title?.trim())
  const visibleIssues = analysis?.issues.filter((issue) => !hasTitleH1 || !isMissingH1Issue(issue)) ?? []

  async function runAnalysis() {
    setLoading(true)
    setError('')
    try {
      await onBeforeAnalyze?.()
      const result = await analyzeArticle(projectId, article.id)
      setAnalysis(result)
      onAnalysisUpdate?.(result)
      try {
        const check = await readyCheck(projectId, article.id)
        setReadiness(check)
        onReadinessUpdate?.(check)
      } catch {
        // Readiness is helpful but should not hide analysis results.
      }
    } catch (err) {
      setError(translateSeoError(err))
    } finally {
      setLoading(false)
    }
  }

  async function runExpertAnalysis() {
    setExpertLoading(true)
    setExpertError('')
    setExpertSuccess('')
    try {
      await onBeforeAnalyze?.()
      const result = await runSeoExpertReview(projectId, article.id)
      setExpertReviewOverride(result)
      onExpertReviewUpdate?.(result)
      setExpertSuccess("Audit SEO Expert mis a jour.")
    } catch (err) {
      setExpertError(translateSeoError(err))
    } finally {
      setExpertLoading(false)
    }
  }

  const groupedIssues: Record<string, SeoIssue[]> = {}
  for (const issue of visibleIssues) {
    const cat = issue.category ?? 'seo'
    if (!groupedIssues[cat]) groupedIssues[cat] = []
    groupedIssues[cat].push(issue)
  }
  const groupKeys = Object.keys(groupedIssues)

  return (
    <div className="flex flex-col gap-4">
      {brief && (
        <div className="grid grid-cols-2 gap-3">
          <ScoreRing label="SEO" score={brief.seo_score} />
          <ScoreRing label="Lisibilite" score={brief.readability_score} />
          <ScoreRing label="Qualite" score={brief.quality_score} />
          <ScoreRing label="EEAT" score={brief.eeat_score} />
        </div>
      )}

      {readiness && <ReadinessBlock check={readiness} hasTitleH1={hasTitleH1} />}

      <div className="rounded-[12px] border border-border bg-surface p-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[12px] font-semibold text-primary">SEO Expert</p>
            <p className="mt-1 text-[10px] leading-snug text-tertiary">
              Analyse SEO actuelle = regles rapides. SEO Expert = audit editorial, EEAT, lisibilite et recommandations.
            </p>
          </div>
          <Button
            size="sm"
            variant="secondary"
            icon={<RefreshCw size={12} />}
            loading={expertLoading}
            className="shrink-0"
            onClick={runExpertAnalysis}
          >
            Relancer l'audit SEO Expert
          </Button>
        </div>

        {expertError && (
          <div className="mt-3 flex items-start gap-2 rounded-[8px] border border-danger/20 bg-danger/5 px-2.5 py-2 text-[11px] text-danger">
            <AlertCircle size={12} className="mt-0.5 shrink-0" />
            <span className="leading-snug">{expertError}</span>
          </div>
        )}

        {expertSuccess && !expertError && (
          <div className="mt-3 flex items-start gap-2 rounded-[8px] border border-success/20 bg-success/8 px-2.5 py-2 text-[11px] text-success">
            <CheckCircle size={12} className="mt-0.5 shrink-0" />
            <span className="leading-snug">{expertSuccess}</span>
          </div>
        )}

        {expertReview ? (
          <div className="mt-3 flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <ScoreRing label="Global" score={expertReview.score_global} />
              <ScoreRing label="SEO Expert" score={expertReview.seo_score} />
              <ScoreRing label="EEAT Expert" score={expertReview.eeat_score} />
              <ScoreRing label="Lisibilite Expert" score={expertReview.readability_score} />
            </div>

            {expertReview.issues.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="text-[11px] font-medium uppercase tracking-wide text-secondary">Issues SEO Expert</p>
                {expertReview.issues.map((issue, index) => (
                  <ExpertIssueItem key={`${issue.check}-${index}`} issue={issue} />
                ))}
              </div>
            )}

            {expertReview.recommendations.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <p className="text-[11px] font-medium uppercase tracking-wide text-secondary">Recommandations</p>
                {expertReview.recommendations.map((recommendation, index) => (
                  <p key={index} className="text-[11px] leading-snug text-secondary">- {recommendation}</p>
                ))}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 text-[11px]">
              <div className="rounded-[10px] border border-border bg-[#fafafc] p-2.5">
                <p className="font-medium text-secondary">Checks valides</p>
                <p className="mt-1 text-primary">{expertReview.passed_checks.length}</p>
              </div>
              <div className="rounded-[10px] border border-border bg-[#fafafc] p-2.5">
                <p className="font-medium text-secondary">Checks en echec</p>
                <p className="mt-1 text-primary">{expertReview.failed_checks.length}</p>
              </div>
            </div>
          </div>
        ) : (
          <p className="mt-3 text-[11px] leading-snug text-tertiary">
            Aucun rapport SEO Expert enregistre pour cet article pour l'instant.
          </p>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-[8px] border border-danger/20 bg-danger/5 px-2.5 py-2 text-[11px] text-danger">
          <AlertCircle size={12} className="mt-0.5 shrink-0" />
          <span className="leading-snug">{error}</span>
        </div>
      )}

      <Button
        size="sm"
        variant="secondary"
        icon={<RefreshCw size={12} />}
        loading={loading}
        className="w-full justify-center"
        onClick={runAnalysis}
      >
        {brief ? "Reanalyser l'article" : 'Analyser'}
      </Button>

      {analysis && groupKeys.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">Problemes bloquants et points a corriger</p>
          {groupKeys.map((cat) => (
            <div key={cat}>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-tertiary">
                {CATEGORY_LABELS[cat] ?? cat} ({groupedIssues[cat].length})
              </p>
              <div className="flex flex-col gap-2">
                {groupedIssues[cat].map((issue, i) => (
                  <IssueItem key={i} issue={issue} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {analysis && analysis.suggestions.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <p className="text-[11px] font-medium uppercase tracking-wide text-secondary">Suggestions</p>
          {analysis.suggestions.map((s, i) => (
            <p key={i} className="text-[11px] leading-snug text-secondary">- {s}</p>
          ))}
        </div>
      )}

      <details className="group">
        <summary className="flex cursor-pointer items-center gap-1.5 text-[11px] font-medium text-secondary hover:text-primary">
          <HelpCircle size={12} />
          Comment les scores sont calcules
        </summary>
        <div className="mt-2 flex flex-col gap-2 text-[10px] leading-snug text-tertiary">
          <p className="font-medium text-secondary">SEO</p>
          <ul className="flex flex-col gap-1 pl-3">
            <li>- Meta title present et evalue avec fallback sur le titre de l'article si besoin.</li>
            <li>- Meta description presente et longueur du meta title / de la meta description.</li>
            <li>- Mot-cle principal dans le titre, le H1, le meta title, l'introduction et le slug.</li>
            <li>- Densite du mot-cle (0.5% a 3%).</li>
            <li>- Presence d'un seul H1 et au moins 2 sections H2.</li>
          </ul>
          <p className="font-medium text-secondary">Lisibilite</p>
          <ul className="flex flex-col gap-1 pl-3">
            <li>- Phrases longues (plus de 25 mots).</li>
            <li>- Paragraphes longs (plus de 150 mots).</li>
            <li>- Introduction presente et suffisamment developpee.</li>
            <li>- Densite de sous-titres sur les contenus longs.</li>
            <li>- Les listes a puces ne sont pas notees directement aujourd'hui : c'est une recommandation editoriale, pas une regle du score.</li>
          </ul>
          <p className="font-medium text-secondary">Qualite</p>
          <ul className="flex flex-col gap-1 pl-3">
            <li>- Structure H2 (au moins 2 sections).</li>
            <li>- Longueur du contenu (300+ mots critique, 800+ recommande).</li>
            <li>- Presence d'une introduction et d'une conclusion.</li>
            <li>- Image de couverture.</li>
            <li>- Extrait (excerpt).</li>
            <li>- Detection de contenu trop mince ou de texte placeholder/mock.</li>
          </ul>
          <p className="font-medium text-secondary">EEAT</p>
          <ul className="flex flex-col gap-1 pl-3">
            <li>- Liens externes vers des sources fiables.</li>
            <li>- Exemples concrets, donnees ou chiffres.</li>
            <li>- Contenu actionnable avec etapes ou verbes d'action.</li>
            <li>- Le nom d'auteur peut aider la credibilite editoriale, mais il n'entre pas encore directement dans le score EEAT actuel.</li>
          </ul>
          <p className="mt-1">
            Chaque probleme critique retire 20 points, chaque avertissement 10 points,
            chaque info 3 points. Score maximal : 100.
          </p>
          <p className="mt-0.5">
            La publication est bloquee si au moins un probleme critique est detecte.
          </p>
          <p className="mt-0.5">
            Certains points affiches ici sont des recommandations editoriales pour guider la redaction, mais seuls les controles ci-dessus sont reellement calcules aujourd'hui par l'analyseur.
          </p>
        </div>
      </details>

      {!brief && !loading && !error && (
        <p className="text-center text-[11px] text-tertiary">
          Lancez une analyse pour obtenir les scores SEO, lisibilite, qualite et EEAT.
        </p>
      )}

      {/* ── Rapports de génération et briefs ─────────────────────────── */}
      {(article.generation_report_json || article.research_brief_json) && (
        <div className="flex flex-col gap-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-secondary">
            Rapports
          </p>

          {article.generation_report_json && (
            <ReportSection title="Rapport de génération" data={article.generation_report_json} />
          )}

          {article.research_brief_json && (
            <ReportSection title="Brief Recherche" data={article.research_brief_json} />
          )}

          {article.keyword_brief_json && (
            <ReportSection title="Brief Mots-clés" data={article.keyword_brief_json} />
          )}

          {article.editorial_angle_json && (
            <ReportSection title="Angle éditorial" data={article.editorial_angle_json} />
          )}

          {article.intent_analysis_json && (
            <ReportSection title="Analyse d&apos;intention" data={article.intent_analysis_json} />
          )}

          {article.language_quality_report_json && (
            <ReportSection title="Qualité linguistique" data={article.language_quality_report_json} />
          )}

          {article.originality_report_json && (
            <ReportSection title="Originalité" data={article.originality_report_json} />
          )}

          {article.humanization_report_json && (
            <ReportSection title="Humanisation" data={article.humanization_report_json} />
          )}

          {article.eeat_checklist_json && (
            <ReportSection title="EEAT" data={article.eeat_checklist_json} />
          )}

          {article.editorial_quality_report_json && (
            <ReportSection title="Qualité éditoriale" data={article.editorial_quality_report_json} />
          )}

          {article.seo_final_checklist_json && (
            <ReportSection title="Checklist SEO finale" data={article.seo_final_checklist_json} />
          )}

          {typeof article.outline_json === 'string' && (
            <ReportSection title="Plan" data={tryParseJson(article.outline_json)} />
          )}

          {article.image_plan_json && (
            <ReportSection title="Plan images" data={article.image_plan_json} />
          )}

          {article.callout_plan_json && (
            <ReportSection title="Plan callouts" data={article.callout_plan_json} />
          )}

          {article.cannibalization_check_json && (
            <ReportSection title="Check cannibalisation" data={article.cannibalization_check_json} />
          )}
        </div>
      )}
    </div>
  )
}

function tryParseJson(val: unknown): Record<string, unknown> {
  if (typeof val === 'string') {
    try { return JSON.parse(val) } catch { return { raw: val } }
  }
  if (val && typeof val === 'object') return val as Record<string, unknown>
  return {}
}

function ReportSection({ title, data }: { title: string; data: unknown }) {
  const parsed = tryParseJson(data)
  const entries = Object.entries(parsed).filter(([k]) => !k.startsWith('_'))

  return (
    <details className="group rounded-[10px] border border-border bg-surface">
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

function ReportField({ label, value }: { label: string; value: unknown }) {
  const display = formatReportValue(value)
  return (
    <div className="text-[10px] leading-snug">
      <span className="font-medium text-secondary">{label}: </span>
      <span className="text-primary">{display}</span>
    </div>
  )
}

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
