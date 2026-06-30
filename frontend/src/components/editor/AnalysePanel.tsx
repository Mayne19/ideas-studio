import { useState, useEffect, useRef } from 'react'
import {
  AlertCircle, AlertTriangle, Info, RefreshCw, CheckCircle,
  HelpCircle, ChevronDown, ChevronRight, Download,
} from '@/components/ui/hugeIcons'
import { analyzeArticle, readyCheck, runSeoExpertReview } from '@/api/seo'
import { ApiError } from '@/api/client'
import type { AnalysisBrief, SeoAnalysis, SeoIssue, ReadyCheck, EditorArticle, SeoExpertReview } from '@/types'
import { finiteScore, scoreTone, getOriginalityScore, getGeoScore } from '@/lib/scoreBadge'
import Button from '@/components/ui/Button'
import CostPanel from './CostPanel'
import StructuredDataPanel from './StructuredDataPanel'
import GeoPanel from './GeoPanel'

/* ─── Error translation ─────────────────────────────────────── */

function translateError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 403: return 'Permission refusée pour cette analyse.'
      case 404: return 'Article introuvable pour cet audit.'
      case 409: return 'Une analyse est déjà en cours.'
      case 422: return 'Contenu invalide. Vérifiez que l\'article a un titre et du contenu.'
      case 500: return 'Erreur serveur lors de l\'analyse. Réessayez dans quelques instants.'
      default: return err.message || `Erreur ${err.status}`
    }
  }
  return 'Impossible de lancer l\'analyse. Vérifiez votre connexion.'
}

/* ─── Score data resolution ─────────────────────────────────── */

const SCORE_TILES = [
  { key: 'Synthèse', label: 'Global' },
  { key: 'SEO', label: 'SEO' },
  { key: 'Qualité', label: 'Qualité' },
  { key: 'Lisibilité', label: 'Lisibilité' },
  { key: 'Originalité', label: 'Originalité' },
  { key: 'GEO', label: 'GEO' },
  { key: 'EEAT', label: 'EEAT' },
] as const

type ScoreKey = typeof SCORE_TILES[number]['key']

function resolveScore(article: EditorArticle, brief: AnalysisBrief | SeoAnalysis | null, expertReview: SeoExpertReview | null, key: ScoreKey): number | null {
  switch (key) {
    case 'Synthèse': return finiteScore(article.global_score)
    case 'SEO': return finiteScore(brief?.seo_score ?? article.seo_score ?? expertReview?.seo_score)
    case 'Qualité': return finiteScore(brief?.quality_score ?? article.quality_score)
    case 'Lisibilité': return finiteScore(brief?.readability_score ?? article.readability_score ?? expertReview?.readability_score)
    case 'Originalité': return getOriginalityScore(article)
    case 'GEO': return getGeoScore(article)
    case 'EEAT': return finiteScore(brief?.eeat_score ?? article.eeat_score)
  }
}

/* ─── Issues helpers ────────────────────────────────────────── */

const SEO_KEYWORDS = [
  { kw: 'meta title', label: 'Balise title présente' },
  { kw: 'meta description', label: 'Meta description présente' },
  { kw: 'mot-clé', label: 'Mot-clé principal présent' },
  { kw: 'densité', label: 'Densité du mot-clé correcte' },
  { kw: 'h1', label: 'Un seul H1' },
  { kw: 'h2', label: 'Au moins 2 sections H2' },
  { kw: 'lien interne', label: 'Liens internes' },
  { kw: 'lien externe', label: 'Liens externes' },
  { kw: 'faq', label: 'FAQ présente' },
]

const READABILITY_KEYWORDS = [
  { kw: 'phrase longue', label: 'Pas de phrases trop longues' },
  { kw: 'paragraphe long', label: 'Paragraphes de longueur correcte' },
  { kw: 'introduction', label: 'Introduction présente' },
  { kw: 'sous-titre', label: 'Densité de sous-titres suffisante' },
  { kw: 'transition', label: 'Transitions fluides' },
]

const QUALITY_KEYWORDS = [
  { kw: 'h2', label: 'Structure H2 suffisante' },
  { kw: 'longueur', label: 'Longueur du contenu suffisante' },
  { kw: 'introduction', label: 'Introduction présente' },
  { kw: 'conclusion', label: 'Conclusion présente' },
  { kw: 'image', label: 'Image de couverture' },
  { kw: 'contenu trop mince', label: 'Contenu non détecté comme trop mince' },
]

const EEAT_KEYWORDS = [
  { kw: 'lien externe', label: 'Liens vers des sources fiables' },
  { kw: 'exemple', label: 'Exemples concrets ou données' },
  { kw: 'chiffre', label: 'Données chiffrées présentes' },
  { kw: 'auteur', label: 'Auteur identifiable' },
]

function deriveWhatWorks(issues: SeoIssue[], keywords: { kw: string; label: string }[]): string[] {
  const messages = issues.map((i) => i.message.toLowerCase())
  return keywords
    .filter(({ kw }) => !messages.some((m) => m.includes(kw)))
    .map(({ label }) => label)
}

/* ─── Calculation text per score type ───────────────────────── */

const CALCULATION_TEXT: Record<string, string> = {
  SEO: 'Le score SEO évalue la présence et la qualité des balises meta, la structure des titres (H1/H2/H3), l\'optimisation du mot-clé principal (densité entre 0.5% et 3%), la présence dans le title, H1, meta title, introduction et slug, ainsi que les liens internes, externes, la FAQ et les données structurées.',
  Qualité: 'Le score Qualité évalue la structure éditoriale : au moins 2 sections H2, une longueur minimale de 300 mots (800+ recommandé), la présence d\'une introduction et d\'une conclusion, une image de couverture, un extrait, et l\'absence de contenu trop mince ou de texte placebo.',
  Lisibilité: 'Le score Lisibilité évalue la clarté du texte : absence de phrases trop longues (>25 mots), paragraphes raisonnables (<150 mots), introduction développée, densité de sous-titres suffisante sur les contenus longs, et bon rythme de lecture.',
  Originalité: 'Le score Originalité est basé sur une analyse heuristique du contenu : similarité avec d\'autres sources, répétitions internes, formulations génériques, risque de paraphrase, et proximité avec du contenu existant.',
  GEO: 'Le score GEO (Generative Engine Optimization) évalue l\'adaptation du contenu aux moteurs de recherche génératifs : réponse directe aux questions, sections autonomes, définitions claires, contenu extractible, et structure adaptée aux LLM.',
  EEAT: 'Le score EEAT évalue l\'expertise, l\'autorité et la fiabilité du contenu : présence de liens externes vers des sources fiables, exemples concrets ou données chiffrées, contenu actionnable, et crédibilité éditoriale.',
  Synthèse: 'Le score Global est une pondération des scores SEO, Qualité, Lisibilité, Originalité, GEO et EEAT. Il détermine si l\'article est prêt à être publié. Un score sous les seuils de validation bloque la publication.',
}

/* ─── Accordion sub-component ───────────────────────────────── */

function Accordion({ title, defaultOpen = false, children }: { title: string; defaultOpen?: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-[12px] border border-border bg-surface">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3.5 py-2.5 text-left text-[12px] font-semibold text-primary"
      >
        {title}
        {open ? <ChevronDown size={14} className="text-tertiary" /> : <ChevronRight size={14} className="text-tertiary" />}
      </button>
      {open && <div className="border-t border-border px-3.5 py-3">{children}</div>}
    </div>
  )
}

/* ─── Score synthesis card ──────────────────────────────────── */

function ScoreSynthesisCard({
  article, brief, expertReview, selected, onSelect,
}: {
  article: EditorArticle
  brief: AnalysisBrief | SeoAnalysis | null
  expertReview: SeoExpertReview | null
  selected: ScoreKey
  onSelect: (key: ScoreKey) => void
}) {
  const globalScore = resolveScore(article, brief, expertReview, 'Synthèse')
  const globalTone = scoreTone(globalScore)

  return (
    <div className="rounded-[14px] border border-border bg-surface p-4">
      <p className="text-[12px] font-semibold text-primary mb-3">Synthèse des scores</p>

      <div className="flex items-center gap-4 mb-4">
        <div className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-full text-[18px] font-bold ${globalTone}`}>
          {globalScore === null ? '—' : Math.round(globalScore)}
        </div>
        <div className="text-[11px] leading-snug text-secondary">
          Score global calculé à partir de l'ensemble des critères de qualité, SEO, lisibilité et fiabilité.
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {SCORE_TILES.map((tile) => {
          const score = resolveScore(article, brief, expertReview, tile.key)
          return (
            <button
              key={tile.key}
              type="button"
              onClick={() => onSelect(tile.key)}
              className={`rounded-[10px] px-2.5 py-2 text-left transition-colors ${
                selected === tile.key ? 'bg-surface-soft ring-1 ring-accent/25' : 'hover:bg-surface-soft'
              }`}
            >
              <span className="block text-[10px] font-medium uppercase tracking-wide text-tertiary">{tile.label}</span>
              <span className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold ${scoreTone(score)}`}>
                {score === null ? '—' : Math.round(score)}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

/* ─── V2.1 signals breakdown ────────────────────────────────── */

type V2Signal = { value: number; weight: number; contribution?: number; [k: string]: unknown }
type V2Report = { score?: number; signals?: Record<string, V2Signal>; flags?: string[]; explanation?: string; confidence?: string; status?: string; version?: string }

function getV2Report(article: EditorArticle, key: ScoreKey): V2Report | null {
  const raw: Record<string, unknown> | null = (() => {
    switch (key) {
      case 'EEAT':        return (article.eeat_checklist_json as Record<string, unknown> | null)
      case 'Originalité': return (article.originality_report_json as Record<string, unknown> | null)
      case 'GEO':         return (article.geo_optimization_json as Record<string, unknown> | null)
      case 'Lisibilité':  return (article.readability_report_json as Record<string, unknown> | null)
      default:            return null
    }
  })()
  if (!raw) return null
  const v2 = raw.v2 as V2Report | undefined
  return v2?.version === '2.1' ? v2 : (raw.version === '2.1' ? raw as V2Report : null)
}

const SIGNAL_LABELS: Record<string, string> = {
  external_links:    'Liens externes',
  cited_stats:       'Statistiques sourcées',
  heading_structure: 'Structure H2/H3',
  author_bio:        'Bio auteur',
  nuance_markers:    'Marqueurs de nuance',
  heading_diversity: 'Diversité des titres',
  ai_generic_absence:'Absence de généricité IA',
  internal_uniqueness:'Unicité interne',
  source_verification:'Vérification des sources',
  concrete_examples: 'Exemples concrets',
  direct_answers:    'Réponses directes',
  heading_format:    'Format des titres',
  structured_data:   'Données structurées',
  named_entities:    'Entités nommées',
  summary_blocks:    'Blocs de synthèse',
  semantic_density:  'Densité sémantique',
  lix_score:         'Score LIX (lisibilité)',
  paragraph_score:   'Longueur des paragraphes',
  passive_score:     'Voix active',
  transition_score:  'Transitions',
}

const FLAG_LABELS: Record<string, string> = {
  no_author_bio:                 'Pas de bio auteur',
  insufficient_external_links:   'Liens externes insuffisants',
  no_cited_statistics:           'Aucune statistique sourcée',
  no_sources_unverified:         'Aucune source fournie — score non vérifié',
  high_source_overlap:           'Fort chevauchement avec les sources',
  generic_ai_patterns_detected:  'Patterns IA génériques détectés',
  probable_internal_duplicate:   'Possible doublon interne',
  no_structured_data:            'Pas de données structurées (JSON-LD)',
  no_summary_block:              'Pas de bloc de synthèse',
  sections_lack_direct_answers:  'Sections sans réponse directe',
  high_lix_difficult_reading:    'LIX élevé — lecture difficile',
  paragraph_length_issue:        'Longueur des paragraphes problématique',
}

function V2SignalsBreakdown({ report }: { report: V2Report }) {
  const signals = report.signals ?? {}
  if (Object.keys(signals).length === 0) return null

  return (
    <div className="flex flex-col gap-2">
      {report.explanation && (
        <p className="text-[11px] leading-snug text-secondary italic">{report.explanation}</p>
      )}

      {report.flags && report.flags.length > 0 && (
        <div className="flex flex-col gap-1">
          {report.flags.map((flag) => (
            <div key={flag} className="flex items-start gap-1.5 rounded-[8px] bg-warning/5 px-2.5 py-1.5">
              <AlertTriangle size={10} className="mt-0.5 shrink-0 text-warning" />
              <span className="text-[11px] text-secondary">{FLAG_LABELS[flag] ?? flag}</span>
            </div>
          ))}
        </div>
      )}

      <p className="text-[10px] font-semibold uppercase tracking-wide text-tertiary mt-1">Détail des signaux</p>
      <div className="flex flex-col gap-1.5">
        {Object.entries(signals).map(([key, signal]) => {
          const pct = Math.round(signal.value)
          const barColor = pct >= 75 ? 'bg-success' : pct >= 50 ? 'bg-warning' : 'bg-danger'
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-[10px] text-secondary">{SIGNAL_LABELS[key] ?? key}</span>
                <span className="text-[10px] font-medium text-primary">{pct}/100</span>
              </div>
              <div className="h-1 w-full rounded-full bg-border">
                <div className={`h-1 rounded-full transition-all ${barColor}`} style={{ width: `${pct}%` }} />
              </div>
            </div>
          )
        })}
      </div>

      {report.confidence && (
        <p className="text-[10px] text-tertiary mt-1">
          Confiance : {report.confidence === 'high' ? 'élevée' : report.confidence === 'medium' ? 'moyenne' : 'faible'}
          {report.confidence === 'low' && ' — score affiché avec préfixe ~'}
        </p>
      )}
    </div>
  )
}

/* ─── Score detail panel ────────────────────────────────────── */

function getIssuesForCategory(issues: SeoIssue[], category: string) {
  return issues.filter((i) => i.category === category)
}

function ScoreDetailPanel({
  selected, article, brief, readiness, expertReview, analysis,
}: {
  selected: ScoreKey
  article: EditorArticle
  brief: AnalysisBrief | SeoAnalysis | null
  readiness: ReadyCheck | null
  expertReview: SeoExpertReview | null
  analysis: SeoAnalysis | null
}) {
  const score = resolveScore(article, brief, expertReview, selected)
  const issues = analysis?.issues ?? []
  const cat = categoryMap[selected]
  const categoryIssues = cat ? getIssuesForCategory(issues, cat) : issues

  const crit = categoryIssues.filter((i) => i.severity === 'critical')
  const warn = categoryIssues.filter((i) => i.severity === 'warning')
  const info = categoryIssues.filter((i) => i.severity === 'info')
  const hasProblems = crit.length > 0 || warn.length > 0
  const hasActions = info.length > 0 || (analysis?.suggestions?.length ?? 0) > 0

  const v2Report = getV2Report(article, selected)

  let whatWorks: string[] = []
  if (selected === 'Synthèse') {
    if (readiness) {
      if (readiness.can_publish) whatWorks.push('Tous les seuils de validation sont atteints')
      if (readiness.global_score_valid) whatWorks.push('Score global validé')
    }
    if (expertReview?.passed_checks?.length) {
      whatWorks.push(`${expertReview.passed_checks.length} contrôles SEO Expert validés`)
    }
  } else if (v2Report) {
    // v2.1 experts: derive "what works" from signal scores
    const signals = v2Report.signals ?? {}
    whatWorks = Object.entries(signals)
      .filter(([, s]) => s.value >= 75)
      .map(([k]) => SIGNAL_LABELS[k] ?? k)
    if (v2Report.status === 'original' || v2Report.status === 'adds_value') {
      whatWorks.push('Contenu original vérifié')
    }
    if (score !== null && score >= 70 && whatWorks.length === 0) {
      whatWorks.push('Tous les signaux sont satisfaisants')
    }
  } else {
    const keywords = keywordsMap[selected]
    if (keywords) whatWorks = deriveWhatWorks(categoryIssues, keywords)
    if (expertReview?.passed_checks?.length) {
      const allPassed = expertReview.passed_checks
      whatWorks = [...new Set([...allPassed, ...whatWorks])]
    }
    if (whatWorks.length === 0 && categoryIssues.length === 0 && score !== null && score > 0) {
      whatWorks.push('Tous les contrôles sont validés pour ce critère')
    }
  }

  return (
    <div className="rounded-[14px] border border-border bg-surface p-4">
      <div className="flex items-center gap-3 mb-4">
        <span className={`inline-flex rounded-full px-3 py-1 text-[13px] font-semibold ${scoreTone(score)}`}>
          {selected} : {score === null ? '—' : Math.round(score)}
        </span>
        <span className="text-[11px] text-tertiary leading-snug">
          {selected === 'Synthèse' ? 'Vue d\'ensemble de l\'article' : 'Détail du score sélectionné'}
        </span>
      </div>

      <div className="flex flex-col gap-3">
        <div className="rounded-[10px] bg-surface-soft px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-secondary mb-1">Comment ce score est calculé</p>
          <p className="text-[11px] leading-snug text-secondary">{CALCULATION_TEXT[selected]}</p>
        </div>

        {whatWorks.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-success mb-1.5">Ce qui fonctionne</p>
            <div className="flex flex-col gap-1">
              {whatWorks.map((item, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[11px]">
                  <CheckCircle size={11} className="mt-0.5 shrink-0 text-success" />
                  <span className="text-secondary">{item}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {v2Report && <V2SignalsBreakdown report={v2Report} />}

        {!v2Report && hasProblems && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-danger mb-1.5">
              Problèmes bloquants {crit.length > 0 ? `(${crit.length} critique${crit.length > 1 ? 's' : ''})` : ''}
            </p>
            <div className="flex flex-col gap-1.5">
              {[...crit, ...warn].map((issue, i) => (
                <div key={i} className="flex items-start gap-1.5 rounded-[8px] bg-danger/5 px-2.5 py-2">
                  {issue.severity === 'critical'
                    ? <AlertCircle size={11} className="mt-0.5 shrink-0 text-danger" />
                    : <AlertTriangle size={11} className="mt-0.5 shrink-0 text-warning" />
                  }
                  <div>
                    <p className="text-[11px] leading-snug text-primary">{issue.message}</p>
                    {issue.suggestion && <p className="mt-0.5 text-[10px] leading-snug text-tertiary">{issue.suggestion}</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {hasActions && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-accent mb-1.5">Actions recommandées</p>
            <div className="flex flex-col gap-1.5">
              {info.map((issue, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[11px]">
                  <Info size={11} className="mt-0.5 shrink-0 text-accent" />
                  <div>
                    <p className="leading-snug text-secondary">{issue.message}</p>
                    {issue.suggestion && <p className="mt-0.5 text-[10px] text-tertiary">{issue.suggestion}</p>}
                  </div>
                </div>
              ))}
              {analysis?.suggestions?.map((s, i) => (
                <div key={`s-${i}`} className="flex items-start gap-1.5 text-[11px]">
                  <RefreshCw size={11} className="mt-0.5 shrink-0 text-accent" />
                  <span className="text-secondary">{s}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {!hasProblems && !hasActions && whatWorks.length === 0 && (
          <div className="flex items-center gap-2 rounded-[10px] bg-surface-soft px-3 py-2.5 text-[11px] text-tertiary">
            <HelpCircle size={12} className="shrink-0" />
            <span>Lancez une analyse pour obtenir les détails de ce score.</span>
          </div>
        )}
      </div>
    </div>
  )
}

const categoryMap: Partial<Record<ScoreKey, string>> = {
  SEO: 'seo',
  Lisibilité: 'readability',
  Qualité: 'quality',
  EEAT: 'eeat',
}

const keywordsMap: Partial<Record<ScoreKey, { kw: string; label: string }[]>> = {
  SEO: SEO_KEYWORDS,
  Lisibilité: READABILITY_KEYWORDS,
  Qualité: QUALITY_KEYWORDS,
  EEAT: EEAT_KEYWORDS,
}

/* ─── Expert review sub-component ───────────────────────────── */

function ExpertReviewSection({
  expertReview, expertLoading, expertError, expertSuccess, isOpen, onToggle, onRun,
}: {
  expertReview: SeoExpertReview | null
  expertLoading: boolean
  expertError: string
  expertSuccess: string
  isOpen: boolean
  onToggle: () => void
  onRun: () => void
}) {
  return (
    <div className="rounded-[12px] border border-border bg-surface">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-3.5 py-2.5 text-left text-[12px] font-semibold text-primary"
      >
        SEO Expert
        {isOpen ? <ChevronDown size={14} className="text-tertiary" /> : <ChevronRight size={14} className="text-tertiary" />}
      </button>
      {isOpen && (
        <div className="border-t border-border px-3.5 py-3 flex flex-col gap-3">
          <div className="flex items-start justify-between gap-3">
            <p className="text-[11px] leading-snug text-tertiary">
              Analyse SEO avancée avec audit éditorial, EEAT, lisibilité et recommandations personnalisées.
            </p>
            <Button size="sm" variant="secondary" icon={<RefreshCw size={12} />} loading={expertLoading} className="shrink-0" onClick={onRun}>
              Lancer l'audit
            </Button>
          </div>

          {expertError && (
            <div className="flex items-start gap-2 rounded-[8px] border border-danger/20 bg-danger/5 px-2.5 py-2 text-[11px] text-danger">
              <AlertCircle size={12} className="mt-0.5 shrink-0" />
              <span className="leading-snug">{expertError}</span>
            </div>
          )}

          {expertSuccess && !expertError && (
            <div className="flex items-start gap-2 rounded-[8px] border border-success/20 bg-success/8 px-2.5 py-2 text-[11px] text-success">
              <CheckCircle size={12} className="mt-0.5 shrink-0" />
              <span className="leading-snug">{expertSuccess}</span>
            </div>
          )}

          {expertReview ? (
            <div className="flex flex-col gap-3">
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                {([
                  ['Global', expertReview.score_global],
                  ['SEO Expert', expertReview.seo_score],
                  ['EEAT Expert', expertReview.eeat_score],
                  ['Lisibilité Expert', expertReview.readability_score],
                ] as const).map(([label, val]) => (
                  <div key={label} className="rounded-[10px] border border-border bg-surface-soft p-2.5">
                    <p className="text-[10px] text-tertiary">{label}</p>
                    <p className={`mt-0.5 text-[14px] font-bold ${scoreTone(val)}`}>{Math.round(val)}</p>
                  </div>
                ))}
              </div>

              {expertReview.issues.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-secondary">Issues</p>
                  {expertReview.issues.map((issue, i) => {
                    const Icon = issue.severity === 'critical' ? AlertCircle : issue.severity === 'warning' ? AlertTriangle : Info
                    const iconColor = issue.severity === 'critical' ? 'text-danger' : issue.severity === 'warning' ? 'text-warning' : 'text-accent'
                    return (
                      <div key={i} className="flex items-start gap-1.5 text-[11px]">
                        <Icon size={11} className={`mt-0.5 shrink-0 ${iconColor}`} />
                        <div>
                          <p className="leading-snug text-primary">{issue.message}</p>
                          <p className="text-[10px] text-tertiary">{issue.check}</p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {expertReview.recommendations.length > 0 && (
                <div className="flex flex-col gap-1">
                  <p className="text-[10px] font-medium uppercase tracking-wide text-secondary">Recommandations</p>
                  {expertReview.recommendations.map((rec, i) => (
                    <p key={i} className="text-[11px] leading-snug text-secondary">- {rec}</p>
                  ))}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="rounded-[10px] border border-border bg-surface-soft p-2.5">
                  <p className="text-[10px] text-tertiary">Contrôles validés</p>
                  <p className="mt-0.5 text-[14px] font-bold text-success">{expertReview.passed_checks.length}</p>
                </div>
                <div className="rounded-[10px] border border-border bg-surface-soft p-2.5">
                  <p className="text-[10px] text-tertiary">Contrôles en échec</p>
                  <p className="mt-0.5 text-[14px] font-bold text-danger">{expertReview.failed_checks.length}</p>
                </div>
              </div>
            </div>
          ) : (
            !expertLoading && (
              <p className="text-[11px] text-tertiary">
                Aucun rapport SEO Expert enregistré pour cet article.
              </p>
            )
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Main AnalysePanel ─────────────────────────────────────── */

type AnalysePanelProps = {
  article: EditorArticle
  projectId: string
  onBeforeAnalyze: () => Promise<void>
  initialAnalysis: SeoAnalysis | null
  initialReadiness: ReadyCheck | null
  onAnalysisUpdate: (analysis: SeoAnalysis) => void
  onReadinessUpdate: (check: ReadyCheck) => void
  onExpertReviewUpdate: (review: SeoExpertReview) => void
}

export default function AnalysePanel({
  article, projectId, onBeforeAnalyze,
  initialAnalysis = null, initialReadiness = null,
  onAnalysisUpdate, onReadinessUpdate, onExpertReviewUpdate,
}: AnalysePanelProps) {
  const [analysis, setAnalysis] = useState<SeoAnalysis | null>(initialAnalysis)
  const [readiness, setReadiness] = useState<ReadyCheck | null>(initialReadiness)
  const [expertReviewOverride, setExpertReviewOverride] = useState<SeoExpertReview | null>(null)
  const [loading, setLoading] = useState(false)
  const [expertLoading, setExpertLoading] = useState(false)
  const [error, setError] = useState('')
  const [expertError, setExpertError] = useState('')
  const [expertSuccess, setExpertSuccess] = useState('')
  const [selectedScore, setSelectedScore] = useState<ScoreKey>('Synthèse')
  const [expertOpen, setExpertOpen] = useState(false)

  const brief = analysis ?? article.latest_analysis
  const expertReview = expertReviewOverride ?? article.seo_review_json ?? null

  const autoTriggeredRef = useRef(false)
  useEffect(() => {
    if (autoTriggeredRef.current) return
    if (brief) return
    if (!article.content || article.content.length < 100) return
    autoTriggeredRef.current = true
    void runAnalysis()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function runAnalysis() {
    setLoading(true)
    setError('')
    try {
      await onBeforeAnalyze()
      const result = await analyzeArticle(projectId, article.id)
      setAnalysis(result)
      onAnalysisUpdate(result)
      try {
        const check = await readyCheck(projectId, article.id)
        setReadiness(check)
        onReadinessUpdate(check)
      } catch {
        // readiness optional
      }
    } catch (err) {
      setError(translateError(err))
    } finally {
      setLoading(false)
    }
  }

  async function runExpertAnalysis() {
    setExpertLoading(true)
    setExpertError('')
    setExpertSuccess('')
    try {
      await onBeforeAnalyze()
      const result = await runSeoExpertReview(projectId, article.id)
      setExpertReviewOverride(result)
      onExpertReviewUpdate(result)
      setExpertSuccess('Audit SEO Expert mis à jour.')
    } catch (err) {
      setExpertError(translateError(err))
    } finally {
      setExpertLoading(false)
    }
  }

  function handleExport() {
    const lines: string[] = []
    lines.push('=== Rapport d\'analyse ===')
    lines.push('')
    for (const tile of SCORE_TILES) {
      const val = resolveScore(article, brief, expertReview, tile.key)
      lines.push(`${tile.label}: ${val === null ? '—' : Math.round(val)}`)
    }
    lines.push('')
    if (analysis) {
      lines.push(`Issues: ${analysis.issues.length}`)
      lines.push(`Suggestions: ${analysis.suggestions.length}`)
    }
    lines.push(`Date: ${new Date().toISOString()}`)

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `analyse-${article.slug || article.id}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col gap-3 p-3">

      {/* Score synthesis */}
      <ScoreSynthesisCard
        article={article}
        brief={brief}
        expertReview={expertReview}
        selected={selectedScore}
        onSelect={setSelectedScore}
      />

      {/* Score detail */}
      <ScoreDetailPanel
        selected={selectedScore}
        article={article}
        brief={brief}
        readiness={readiness}
        expertReview={expertReview}
        analysis={analysis}
      />

      {/* Error banner */}
      {error && (
        <div className="flex items-start gap-2 rounded-[8px] border border-danger/20 bg-danger/5 px-3 py-2.5 text-[11px] text-danger">
          <AlertCircle size={12} className="mt-0.5 shrink-0" />
          <span className="leading-snug">{error}</span>
        </div>
      )}

      {/* Accordions */}
      <ExpertReviewSection
        expertReview={expertReview}
        expertLoading={expertLoading}
        expertError={expertError}
        expertSuccess={expertSuccess}
        isOpen={expertOpen}
        onToggle={() => setExpertOpen(!expertOpen)}
        onRun={runExpertAnalysis}
      />

      <Accordion title="Commentaires & coûts">
        <CostPanel article={article} />
      </Accordion>

      <Accordion title="Données structurées">
        <StructuredDataPanel article={article} />
      </Accordion>

      <Accordion title="Analyse GEO">
        <GeoPanel article={article} />
      </Accordion>

      {/* Action buttons */}
      <div className="flex gap-2 pt-1">
        <Button
          size="sm"
          variant="ghost"
          icon={<Download size={12} />}
          className="flex-1 justify-center"
          onClick={handleExport}
        >
          Exporter le rapport
        </Button>
      </div>

      <p className="text-center text-[11px] text-tertiary pt-1">
        {loading
          ? 'Analyse en cours…'
          : 'Les scores se mettent à jour automatiquement à chaque sauvegarde.'}
      </p>
    </div>
  )
}
