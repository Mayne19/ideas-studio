import { useState } from 'react'
import { AlertCircle, AlertTriangle, Info, RefreshCw, CheckCircle, XCircle, MinusCircle, HelpCircle } from 'lucide-react'
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
        <circle cx="56" cy="56" r={r} fill="none" className="stroke-[#ececf0] dark:stroke-[#333]" strokeWidth="9" />
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
          className="fill-[#1d1d1f] dark:fill-[#e0e0e4]"
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

      {/* Meta title info */}
      <div className="rounded-[10px] border border-border bg-[#f9f9fb] px-3 py-2.5">
        <p className="text-[11px] font-medium text-primary">
          Meta title utilise : {article.meta_title?.trim() ? `"${article.meta_title.trim()}"` : 'titre de l\'article'}
        </p>
        <p className="mt-0.5 text-[10px] text-tertiary">
          {article.meta_title?.trim()
            ? 'Un meta title personnalise est defini.'
            : 'Aucun meta title personnalise. Le titre de l\'article est utilise comme fallback pour l\'analyse SEO.'}
        </p>
      </div>

      {/* How SEO score is calculated */}
      <details className="group">
        <summary className="flex cursor-pointer items-center gap-1.5 text-[11px] font-medium text-secondary hover:text-primary">
          <HelpCircle size={12} />
          Comment le score SEO est calcule
        </summary>
        <div className="mt-2 flex flex-col gap-2 text-[10px] leading-snug text-tertiary">
          <p className="font-medium text-secondary">Criteres analyses :</p>
          <ul className="flex flex-col gap-1 pl-3">
            <li>- Mot-cle principal dans le titre / meta title</li>
            <li>- Mot-cle dans le H1</li>
            <li>- Mot-cle dans l'introduction (100 premiers mots)</li>
            <li>- Densite du mot-cle (0.5% a 3%)</li>
            <li>- Unicite du H1</li>
            <li>- Meta title (30-60 car.) et meta description (120-160 car.)</li>
            <li>- Mot-cle dans le meta title</li>
            <li>- Slug (present, contient le mot-cle)</li>
            <li>- Structure H2 (au moins 2 sections)</li>
            <li>- Longueur du contenu (300+ mots critique, 800+ recommande)</li>
            <li>- Presence d'une introduction et d'une conclusion</li>
            <li>- Image de couverture</li>
            <li>- Extrait (excerpt)</li>
            <li>- Liens externes vers des sources fiables</li>
            <li>- Exemples concrets ou donnees</li>
            <li>- Caractere actionnable (listes, etapes)</li>
            <li>- Phrases longues (&gt;25 mots) et paragraphes longs (&gt;150 mots)</li>
            <li>- Densite des sous-titres</li>
          </ul>
          <p className="mt-1">
            Chaque probleme critique retire 20 points, chaque avertissement 10 points,
            chaque info 3 points. Score maximal : 100.
          </p>
          <p className="mt-0.5">
            La publication est bloquee si au moins un probleme critique est detecte.
          </p>
        </div>
      </details>

      {!brief && !loading && !error && (
        <p className="text-center text-[11px] text-tertiary">
          Lancez une analyse pour obtenir les scores SEO, lisibilite, qualite et EEAT.
        </p>
      )}
    </div>
  )
}
