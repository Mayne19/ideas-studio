import { useState, useEffect, useRef } from 'react'
import {
  AlertCircle, AlertTriangle, Info, RefreshCw, CheckCircle,
  HelpCircle, Download,
} from '@/components/ui/hugeIcons'
import { analyzeArticle, readyCheck, runSeoExpertReview } from '@/api/seo'
import { ApiError } from '@/api/client'
import type { AnalysisBrief, SeoAnalysis, SeoIssue, ReadyCheck, EditorArticle, SeoExpertReview } from '@/types'
import { finiteScore } from '@/lib/scoreBadge'
import Button from '@/components/ui/Button'
import { Gauge } from '@/lib/vercel-geistcn/components'

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
  { key: 'Présence humaine', label: 'Présence humaine' },
] as const

type ScoreKey = typeof SCORE_TILES[number]['key']

function getArtifact(article: EditorArticle, agentKey: string): Record<string, unknown> | null {
  return article.artifacts[agentKey] ?? null
}

function getOriginalityScore(article: EditorArticle): number | null {
  const report = getArtifact(article, 'originality_report')
  if (!report) return null
  const v2 = report.v2 as Record<string, unknown> | undefined
  const score = v2 && typeof v2 === 'object' ? v2.score : report.heuristic_score
  return typeof score === 'number' && Number.isFinite(score) ? score : null
}

function getGeoScoreFromArtifact(article: EditorArticle): number | null {
  const report = getArtifact(article, 'geo_optimization')
  if (!report) return null
  const score = report.geo_score ?? report.score
  return typeof score === 'number' && Number.isFinite(score) ? score : null
}

function getHumanPresenceScore(article: EditorArticle): number | null {
  const report = getArtifact(article, 'human_presence_report')
  if (!report) return null
  const score = report.score
  return typeof score === 'number' && Number.isFinite(score) ? score : null
}

function resolveScore(article: EditorArticle, brief: AnalysisBrief | SeoAnalysis | null, expertReview: SeoExpertReview | null, key: ScoreKey): number | null {
  switch (key) {
    case 'Synthèse': return finiteScore(article.latest_analysis?.global_score)
    case 'SEO': return finiteScore(brief?.seo_score ?? expertReview?.seo_score)
    case 'Qualité': return finiteScore(brief?.quality_score)
    case 'Lisibilité': return finiteScore(brief?.readability_score ?? expertReview?.readability_score)
    case 'Originalité': return getOriginalityScore(article)
    case 'GEO': return finiteScore(article.latest_analysis?.geo_score) ?? getGeoScoreFromArtifact(article)
    case 'EEAT': return finiteScore(brief?.eeat_score)
    case 'Présence humaine': return getHumanPresenceScore(article)
  }
}

function gaugeColor(score: number): string {
  if (score >= 80) return 'var(--color-success)'
  if (score >= 60) return 'var(--color-warning)'
  return 'var(--color-danger)'
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
  'Présence humaine': 'Le score Présence humaine détecte les signes d\'un texte écrit sans contrainte de style : ouvertures génériques, expressions usées, régularité mécanique des paragraphes, absence de marqueur de voix humaine ou de position assumée, conclusion qui résume au lieu de clore.',
  Synthèse: 'Le score Global est une pondération de 6 signaux : SEO (27%), EEAT (18%), Lisibilité (15%), Originalité (16%), Présence humaine (14%) et Valeur ajoutée (10%, non affichée séparément). GEO et Qualité sont informatifs mais ne comptent pas dans ce calcul. Il détermine si l\'article est prêt à être publié.',
}

/* ─── Score synthesis card ──────────────────────────────────── */

const SECONDARY_SCORE_KEYS: ScoreKey[] = ['SEO', 'EEAT', 'Lisibilité', 'Originalité', 'Présence humaine', 'GEO', 'Qualité']

const SCORE_LABEL: Record<ScoreKey, string> = {
  Synthèse: 'Global',
  SEO: 'SEO',
  Qualité: 'Qualité',
  Lisibilité: 'Lisibilité',
  Originalité: 'Originalité',
  GEO: 'GEO',
  EEAT: 'EEAT',
  'Présence humaine': 'Présence humaine',
}

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

  return (
    <>
      {/* Global — full width, gauge left + label right */}
      <div className="mb-3">
        <button
          type="button"
          onClick={() => onSelect('Synthèse')}
          className={`flex w-full items-center gap-4 rounded-[12px] border px-5 py-4 text-left transition-colors ${
            selected === 'Synthèse' ? 'border-border-strong bg-surface-soft' : 'border-border bg-transparent hover:bg-surface-soft'
          }`}
        >
          <Gauge showValue size="large" value={globalScore ?? 0} color={gaugeColor(globalScore ?? 0)} />
          <div className="flex-1">
            <p className="text-[17px] font-semibold text-primary">Global</p>
            <p className="text-[12px] text-tertiary">Vue d'ensemble de l'article</p>
          </div>
        </button>
      </div>

      {/* Secondary scores — grille auto-flow 2 colonnes (nombre de tuiles variable) */}
      <div className="grid grid-cols-2 gap-2">
        {SECONDARY_SCORE_KEYS.map((key) => {
          const score = resolveScore(article, brief, expertReview, key)
          return (
            <button
              key={key}
              type="button"
              onClick={() => onSelect(key)}
              className={`flex flex-col items-center gap-2 rounded-[12px] border px-2.5 py-3 text-center transition-colors ${
                selected === key ? 'border-border-strong bg-surface-soft' : 'border-border bg-transparent hover:bg-surface-soft'
              }`}
            >
              <span className="block text-[10px] font-medium uppercase tracking-wide text-tertiary">{SCORE_LABEL[key]}</span>
              {score === null ? (
                <span className="flex h-12 w-12 items-center justify-center text-[16px] font-semibold text-tertiary">—</span>
              ) : (
                <Gauge showValue size="small" value={score} color={gaugeColor(score)} />
              )}
            </button>
          )
        })}
      </div>
    </>
  )
}

/* ─── V2.1 signals breakdown ────────────────────────────────── */

type V2Signal = { value: number; weight: number; contribution?: number; [k: string]: unknown }
type V2Report = { score?: number; signals?: Record<string, V2Signal>; flags?: string[]; explanation?: string; confidence?: string; status?: string; version?: string }

function getV2Report(article: EditorArticle, key: ScoreKey): V2Report | null {
  const raw: Record<string, unknown> | null = (() => {
    switch (key) {
      case 'EEAT':              return getArtifact(article, 'eeat_checklist')
      case 'Originalité':       return getArtifact(article, 'originality_report')
      case 'GEO':                return getArtifact(article, 'geo_optimization')
      case 'Lisibilité':        return getArtifact(article, 'readability_report')
      case 'Présence humaine':  return getArtifact(article, 'human_presence_report')
      default:                  return null
    }
  })()
  if (!raw) return null
  // human_presence_report est resté en version "1.0" (forme stable depuis
  // toujours, jamais changée) — accepté sans condition. Les autres rapports
  // acceptent toute version majeure "2.x" : la forme (signals/flags/
  // explanation/confidence/status) est stable entre 2.1 et 2.2, seul le
  // contenu du calcul change (ex: originality_service est passé en 2.2 pour
  // le seuil des 500 mots — un check strict sur '2.1' masquait alors tout
  // le détail du score).
  if (key === 'Présence humaine') return raw as V2Report
  const isV2 = (v: unknown): v is string => typeof v === 'string' && v.startsWith('2.')
  const v2 = raw.v2 as V2Report | undefined
  return isV2(v2?.version) ? v2 : (isV2(raw.version as unknown) ? raw as V2Report : null)
}

const SIGNAL_LABELS: Record<string, string> = {
  external_links:    'Liens externes',
  cited_stats:       'Statistiques sourcées',
  heading_structure: 'Structure H2/H3',
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
  intro:             'Qualité de l\'introduction',
  vocabulaire:       'Vocabulaire',
  paragraphes:       'Variation des paragraphes',
  marqueurs_humains: 'Marqueurs humains',
  position_tranchee: 'Position tranchée',
  conclusion:        'Conclusion',
}

const FLAG_LABELS: Record<string, string> = {
  insufficient_external_links:   'Liens externes insuffisants',
  no_cited_statistics:           'Aucune statistique sourcée',
  no_nuance_markers:             'Pas de marqueurs de nuance',
  weak_heading_structure:        'Structure de titres faible',
  low_heading_diversity:         'Titres peu variés',
  no_sources_unverified:         'Aucune source fournie — score non vérifié',
  high_source_overlap:           'Fort chevauchement avec les sources',
  generic_ai_patterns_detected:  'Patterns IA génériques détectés',
  probable_internal_duplicate:   'Possible doublon interne',
  no_structured_data:            'Pas de données structurées (JSON-LD)',
  no_summary_block:              'Pas de bloc de synthèse',
  sections_lack_direct_answers:  'Sections sans réponse directe',
  high_lix_difficult_reading:    'LIX élevé — lecture difficile',
  paragraph_length_issue:        'Longueur des paragraphes problématique',
  intro_trop_longue:             'Introduction trop longue',
  tiret_cadratin_present:        'Tiret cadratin présent',
  paragraphes_longueur_uniforme: 'Paragraphes trop uniformes',
  aucune_phrase_courte_de_rythme:'Aucune phrase courte de rythme',
  aucun_marqueur_humain:         'Aucun marqueur de voix humaine',
  marqueurs_humains_en_exces:    'Marqueurs humains en excès (trop mécanique)',
}

// Certains flags portent un suffixe dynamique ("intro_generique:il est
// important de", "section_sans_position_tranchee:Titre H2...") — non
// mappables un par un dans FLAG_LABELS. On matche sur le préfixe pour leur
// donner un libellé lisible tout en gardant le détail après les deux points.
const FLAG_PREFIX_LABELS: [string, string][] = [
  ['intro_generique:', 'Ouverture générique'],
  ['expression_usee:', 'Expression usée'],
  ['superlatif_vide:', 'Superlatif vide'],
  ['section_sans_position_tranchee:', 'Section sans position tranchée'],
  ['conclusion_resume:', 'Conclusion qui résume au lieu de clore'],
  ['aucun_angle_original:', 'Aucun angle original'],
  ['phrase_remplissage:', 'Phrase de remplissage'],
]

function flagLabel(flag: string): string {
  if (FLAG_LABELS[flag]) return FLAG_LABELS[flag]
  const prefixed = FLAG_PREFIX_LABELS.find(([prefix]) => flag.startsWith(prefix))
  if (prefixed) {
    const detail = flag.slice(prefixed[0].length)
    return detail ? `${prefixed[1]} : « ${detail} »` : prefixed[1]
  }
  return flag
}

function V2SignalsBreakdown({ report }: { report: V2Report }) {
  const signals = report.signals ?? {}
  if (Object.keys(signals).length === 0) return null

  return (
    <div className="flex flex-col gap-2">
      {report.explanation && (
        <p className="text-[12px] leading-snug text-secondary italic">{report.explanation}</p>
      )}

      {report.flags && report.flags.length > 0 && (
        <div className="flex flex-col gap-1">
          {report.flags.map((flag) => (
            <div key={flag} className="flex items-start gap-1.5 rounded-[8px] bg-warning/5 px-2.5 py-1.5">
              <AlertTriangle size={10} className="mt-0.5 shrink-0 text-warning" />
              <span className="text-[12px] text-secondary">{flagLabel(flag)}</span>
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
    <div className="flex flex-col gap-3">
      <div className="flex items-start gap-4">
        <Gauge showValue size="medium" value={score ?? 0} color={gaugeColor(score ?? 0)} />
        <div className="flex-1 min-w-0 pt-1">
          <p className="text-[15px] font-semibold text-primary">{SCORE_LABEL[selected]}</p>
          <p className="mt-1 text-[12px] leading-snug text-secondary">{CALCULATION_TEXT[selected]}</p>
        </div>
      </div>

      <div className="flex flex-col gap-3">

        {whatWorks.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-success mb-1.5">Ce qui fonctionne</p>
            <div className="flex flex-col gap-1">
              {whatWorks.map((item, i) => (
                <div key={i} className="flex items-start gap-1.5 text-[12px]">
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
                    <p className="text-[12px] leading-snug text-primary">{issue.message}</p>
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
                <div key={i} className="flex items-start gap-1.5 text-[12px]">
                  <Info size={11} className="mt-0.5 shrink-0 text-accent" />
                  <div>
                    <p className="leading-snug text-secondary">{issue.message}</p>
                    {issue.suggestion && <p className="mt-0.5 text-[10px] text-tertiary">{issue.suggestion}</p>}
                  </div>
                </div>
              ))}
              {analysis?.suggestions?.map((s, i) => (
                <div key={`s-${i}`} className="flex items-start gap-1.5 text-[12px]">
                  <RefreshCw size={11} className="mt-0.5 shrink-0 text-accent" />
                  <span className="text-secondary">{s}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {!hasProblems && !hasActions && whatWorks.length === 0 && (
          <div className="flex items-center gap-2 rounded-[10px] bg-surface-soft px-3 py-2.5 text-[12px] text-tertiary">
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

/* ─── Main AnalysePanel ─────────────────────────────────────── */

type AnalysePanelProps = {
  article: EditorArticle
  projectId: string
  onBeforeAnalyze: () => Promise<void>
  initialAnalysis: SeoAnalysis | null
  initialReadiness: ReadyCheck | null
  onAnalysisUpdate: (analysis: SeoAnalysis) => void
  onReadinessUpdate: (check: ReadyCheck) => void
}

export default function AnalysePanel({
  article, projectId, onBeforeAnalyze,
  initialAnalysis = null, initialReadiness = null,
  onAnalysisUpdate, onReadinessUpdate,
}: AnalysePanelProps) {
  const [analysis, setAnalysis] = useState<SeoAnalysis | null>(initialAnalysis)
  const [readiness, setReadiness] = useState<ReadyCheck | null>(initialReadiness)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [selectedScore, setSelectedScore] = useState<ScoreKey>('Synthèse')

  const brief = analysis ?? article.latest_analysis
  const [expertReview, setExpertReview] = useState<SeoExpertReview | null>(null)

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
      try {
        const review = await runSeoExpertReview(projectId, article.id)
        setExpertReview(review)
      } catch {
        // audit SEO Expert optionnel — les scores restent basés sur l'analyse standard
      }
    } catch (err) {
      setError(translateError(err))
    } finally {
      setLoading(false)
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
        <div className="flex items-start gap-2 rounded-[8px] border border-danger/20 bg-danger/5 px-3 py-2.5 text-[12px] text-danger">
          <AlertCircle size={12} className="mt-0.5 shrink-0" />
          <span className="leading-snug">{error}</span>
        </div>
      )}

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

      <p className="text-center text-[12px] text-tertiary pt-1">
        {loading
          ? 'Analyse en cours…'
          : 'Les scores se mettent à jour automatiquement à chaque sauvegarde.'}
      </p>
    </div>
  )
}
