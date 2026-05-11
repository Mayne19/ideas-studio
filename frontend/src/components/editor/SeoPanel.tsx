import { useState } from 'react'
import { AlertCircle, AlertTriangle, Info, RefreshCw, CheckCircle, XCircle, MinusCircle } from 'lucide-react'
import { analyzeArticle, readyCheck } from '@/api/seo'
import { ApiError } from '@/api/client'
import type { SeoAnalysis, SeoIssue, ReadyCheck, EditorArticle } from '@/types'
import Button from '@/components/ui/Button'

function translateSeoError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 403: return 'Permission refusee pour cette analyse.'
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
    <div className="flex flex-col items-center gap-1.5 rounded-[12px] border border-border bg-[#f9f9fb] px-2 py-3">
      <svg width="112" height="112" viewBox="0 0 112 112" aria-label={`${label} ${Math.round(val)}`}>
        <circle cx="56" cy="56" r={r} fill="none" stroke="#ececf0" strokeWidth="9" />
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
          fill="#1d1d1f"
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

function ReadinessBlock({ check, hasTitleH1 }: { check: ReadyCheck; hasTitleH1: boolean }) {
  const blockingIssues = hasTitleH1
    ? check.blocking_issues.filter((issue) => !isMissingH1Issue(issue))
    : check.blocking_issues
  const hasBlocking = blockingIssues.length > 0
  const config = check.can_publish || !hasBlocking
    ? { icon: <CheckCircle size={13} />, label: 'Publication readiness: pret ou a verifier', cls: 'bg-success/10 text-[#218044]' }
    : { icon: <XCircle size={13} />, label: 'Publication readiness: bloque', cls: 'bg-danger/8 text-[#d93b33]' }

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
}: {
  article: EditorArticle
  projectId: string
  onBeforeAnalyze?: () => Promise<void> | void
  initialAnalysis?: SeoAnalysis | null
  initialReadiness?: ReadyCheck | null
  onAnalysisUpdate?: (analysis: SeoAnalysis) => void
  onReadinessUpdate?: (check: ReadyCheck) => void
}) {
  const [analysis, setAnalysis] = useState<SeoAnalysis | null>(initialAnalysis)
  const [readiness, setReadiness] = useState<ReadyCheck | null>(initialReadiness)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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

      {!brief && !loading && !error && (
        <p className="text-center text-[11px] text-tertiary">
          Lancez une analyse pour obtenir les scores SEO, lisibilite, qualite et EEAT.
        </p>
      )}
    </div>
  )
}
