import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Lightbulb, Plus, Star, Pencil, X, ExternalLink, Loader2, RefreshCw, ChevronDown, ChevronUp, Search, Info, Sparkles, CheckCircle } from 'lucide-react'
import {
  listIdeas,
  generateIdea,
  rejectIdea,
  setIdeaPriority,
  startWriting,
  createManualDraft,
  autoGenerateIdeas,
} from '@/api/ideas'
import type { AutoGenerateIdeasResponse } from '@/api/ideas'
import { listCategories } from '@/api/categories'
import { ApiError } from '@/api/client'
import type { Article, Category } from '@/types'
import { formatDate } from '@/utils/format'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import Input from '@/components/ui/Input'
import Textarea from '@/components/ui/Textarea'
import ErrorState from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'

function translateIdeaError(err: unknown, context: 'action' | 'generate' | 'reject'): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 403: return 'Vous n\'avez pas la permission d\'effectuer cette action.'
      case 409:
        if (context === 'generate') return 'Une idée est déjà en cours de génération. Attendez quelques instants.'
        return 'Cette action n\'est pas possible dans l\'état actuel de l\'idée.'
      case 422: return 'Données invalides. Vérifiez les informations saisies.'
      case 503: return err.message || 'Provider IA indisponible, génération réelle impossible.'
      default: return err.message || `Erreur ${err.status}`
    }
  }
  return 'Une erreur inattendue est survenue.'
}

type PipelineColumn = {
  key: string
  label: string
  statuses: string[]
  color: string
  emptyLabel: string
}

const PIPELINE_COLUMNS: PipelineColumn[] = [
  {
    key: 'proposed',
    label: 'Idées',
    statuses: ['idea_proposed'],
    color: 'bg-blue-50 border-blue-100',
    emptyLabel: 'Utilisez "Générer" pour proposer des idées via l\'IA.',
  },
  {
    key: 'priority',
    label: 'Prioritaires',
    statuses: ['idea_priority'],
    color: 'bg-orange-50 border-orange-100',
    emptyLabel: 'Étoilez une idée pour la prioriser.',
  },
  {
    key: 'writing',
    label: 'En rédaction',
    statuses: ['outline_ready', 'writing_requested', 'writing_in_progress', 'draft_ready'],
    color: 'bg-purple-50 border-purple-100',
    emptyLabel: 'Cliquez "Rédiger" sur une idée pour commencer.',
  },
  {
    key: 'rejected',
    label: 'Rejetées',
    statuses: ['idea_rejected'],
    color: 'bg-[#fdf2f2] border-red-100',
    emptyLabel: 'Aucune idée rejetée.',
  },
]

const WRITING_STATUS_LABELS: Record<string, string> = {
  outline_ready: 'Plan prêt',
  writing_requested: 'Rédaction demandée',
  writing_in_progress: 'En rédaction',
  draft_ready: 'Brouillon prêt',
}

function OpportunityDot({ score }: { score: number | null }) {
  if (score === null) return null
  const pct = Math.round(score * 100)
  const color = pct >= 70 ? 'bg-success' : pct >= 40 ? 'bg-warning' : 'bg-[#c8c8cc]'
  return (
    <span className="inline-flex items-center gap-1 text-[11px] text-tertiary">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
      {pct}%
    </span>
  )
}

function IdeaCard({
  article,
  columnKey,
  categories,
  onAction,
}: {
  article: Article
  columnKey: string
  categories: Category[]
  onAction: (action: string, article: Article) => void
}) {
  const [loading, setLoading] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)

  async function doAction(action: string) {
    setLoading(action)
    await onAction(action, article)
    setLoading(null)
  }

  const isIdea = ['proposed', 'priority'].includes(columnKey)
  const isWriting = columnKey === 'writing'
  const isRejected = columnKey === 'rejected'
  const category = categories.find((c) => c.id === article.category_id)

  // Parse outline if available
  let outlineItems: string[] = []
  try {
    if ((article as Record<string, unknown>).outline_json) {
      const parsed = JSON.parse((article as Record<string, unknown>).outline_json as string)
      if (Array.isArray(parsed)) outlineItems = parsed.slice(0, 4).map((h: unknown) => String(h))
    }
  } catch { /* non-critical */ }

  return (
    <div className="rounded-[12px] border border-border bg-surface p-3 shadow-sm hover:shadow-card transition-shadow">
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-[12px] font-medium text-primary leading-snug flex-1">{article.title}</p>
        {isWriting && article.status in WRITING_STATUS_LABELS && (
          <span className="shrink-0 rounded-full bg-[#f0f0f2] px-1.5 py-0.5 text-[10px] text-secondary">
            {WRITING_STATUS_LABELS[article.status] ?? article.status}
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-1.5 mb-2">
        {article.keyword && (
          <span className="rounded-full bg-accent/8 px-2 py-0.5 text-[10px] text-accent truncate max-w-[120px]">
            {article.keyword}
          </span>
        )}
        {category && (
          <span className="rounded-full bg-[#f0f0f2] px-2 py-0.5 text-[10px] text-tertiary truncate max-w-[80px]">
            {category.name}
          </span>
        )}
        <OpportunityDot score={article.opportunity_score} />
        <span className="text-[10px] text-tertiary ml-auto">{formatDate(article.created_at)}</span>
      </div>

      {article.angle && (
        <p className="text-[11px] text-tertiary mb-2 leading-snug line-clamp-2">{article.angle}</p>
      )}

      {/* Expandable detail */}
      {(article.search_intent || article.audience || outlineItems.length > 0) && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-[10px] text-tertiary hover:text-secondary transition-colors mb-1"
        >
          {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          {expanded ? 'Moins' : 'Détails'}
        </button>
      )}

      {expanded && (
        <div className="mb-2 flex flex-col gap-1.5 border-t border-border pt-2">
          {article.search_intent && (
            <p className="text-[10px] text-tertiary">
              <span className="font-medium text-secondary">Intention :</span> {article.search_intent}
            </p>
          )}
          {article.audience && (
            <p className="text-[10px] text-tertiary">
              <span className="font-medium text-secondary">Audience :</span> {article.audience}
            </p>
          )}
          {outlineItems.length > 0 && (
            <div>
              <p className="text-[10px] font-medium text-secondary mb-0.5">Plan :</p>
              <ul className="flex flex-col gap-0.5">
                {outlineItems.map((h, i) => (
                  <li key={i} className="text-[10px] text-tertiary leading-snug">• {h}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="flex items-center gap-1 flex-wrap">
        {isWriting && (
          <Button
            size="sm"
            variant="secondary"
            icon={<ExternalLink size={11} />}
            className="text-[11px] h-6 px-2"
            onClick={() => onAction('open', article)}
          >
            Ouvrir
          </Button>
        )}
        {isIdea && (
          <>
            {columnKey === 'proposed' && (
              <button
                onClick={() => doAction('prioritize')}
                disabled={loading === 'prioritize'}
                className="flex items-center gap-1 rounded-[6px] px-2 py-1 text-[11px] text-secondary hover:bg-orange-50 hover:text-orange-600 transition-colors disabled:opacity-40"
              >
                {loading === 'prioritize' ? <Loader2 size={11} className="animate-spin" /> : <Star size={11} />}
                Prioriser
              </button>
            )}
            <button
              onClick={() => doAction('start-writing')}
              disabled={!!loading}
              className="flex items-center gap-1 rounded-[6px] px-2 py-1 text-[11px] text-secondary hover:bg-purple-50 hover:text-purple-600 transition-colors disabled:opacity-40"
            >
              {loading === 'start-writing' ? <Loader2 size={11} className="animate-spin" /> : <Pencil size={11} />}
              Rédiger
            </button>
            <button
              onClick={() => doAction('manual-draft')}
              disabled={!!loading}
              className="flex items-center gap-1 rounded-[6px] px-2 py-1 text-[11px] text-secondary hover:bg-[#f0f0f2] hover:text-primary transition-colors disabled:opacity-40"
            >
              {loading === 'manual-draft' ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />}
              Manuel
            </button>
            <button
              onClick={() => doAction('reject')}
              disabled={!!loading}
              className="flex items-center gap-1 rounded-[6px] px-2 py-1 text-[11px] text-tertiary hover:bg-danger/5 hover:text-danger transition-colors disabled:opacity-40"
            >
              {loading === 'reject' ? <Loader2 size={11} className="animate-spin" /> : <X size={11} />}
              Rejeter
            </button>
          </>
        )}
        {isRejected && article.rejection_reason && (
          <p className="text-[10px] text-tertiary italic truncate">{article.rejection_reason}</p>
        )}
      </div>
    </div>
  )
}

function KanbanColumn({
  column,
  articles,
  categories,
  onAction,
}: {
  column: PipelineColumn
  articles: Article[]
  categories: Category[]
  onAction: (action: string, article: Article) => void
}) {
  return (
    <div className={`flex flex-col rounded-[16px] border p-3 min-w-[220px] flex-1 max-w-[280px] ${column.color}`}>
      <div className="flex items-center justify-between mb-3 px-1">
        <span className="text-[12px] font-semibold text-secondary">{column.label}</span>
        <span className="rounded-full bg-white/70 px-1.5 py-0.5 text-[10px] font-medium text-tertiary">
          {articles.length}
        </span>
      </div>
      <div className="flex flex-col gap-2 overflow-y-auto max-h-[calc(100vh-280px)]">
        {articles.length === 0 ? (
          <p className="text-[11px] text-tertiary text-center py-6">{column.emptyLabel}</p>
        ) : (
          articles.map((a) => (
            <IdeaCard key={a.id} article={a} columnKey={column.key} categories={categories} onAction={onAction} />
          ))
        )}
      </div>
    </div>
  )
}

export default function IdeasPipelinePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [allIdeas, setAllIdeas] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)
  const [filterCategory, setFilterCategory] = useState('')
  const [filterSearch, setFilterSearch] = useState('')
  const [filterMinScore, setFilterMinScore] = useState(0)

  const [generateOpen, setGenerateOpen] = useState(false)
  const [contextHint, setContextHint] = useState('')
  const [preferredTitle, setPreferredTitle] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')

  const [rejectTarget, setRejectTarget] = useState<Article | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [rejectNote, setRejectNote] = useState('')
  const [rejecting, setRejecting] = useState(false)
  const [rejectError, setRejectError] = useState('')
  const [actionError, setActionError] = useState('')

  const [autoOpen, setAutoOpen] = useState(false)
  const [autoGenerating, setAutoGenerating] = useState(false)
  const [autoResult, setAutoResult] = useState<AutoGenerateIdeasResponse | null>(null)
  const [autoError, setAutoError] = useState('')
  const [autoCount, setAutoCount] = useState(3)

  useEffect(() => {
    if (!projectId) return
    listCategories(projectId).then(setCategories).catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setStatus('loading') })

    const IDEA_STATUSES_TO_FETCH = [
      'idea_proposed',
      'idea_priority',
      'idea_rejected',
      'outline_ready',
      'writing_requested',
      'writing_in_progress',
      'draft_ready',
    ]

    Promise.all(
      IDEA_STATUSES_TO_FETCH.map((s) => listIdeas(projectId, s))
    )
      .then((results) => {
        if (cancelled) return
        setAllIdeas(results.flat())
        setStatus('success')
      })
      .catch(() => { if (!cancelled) setStatus('error') })

    return () => { cancelled = true }
  }, [projectId, tick])

  function getColumn(col: PipelineColumn): Article[] {
    return allIdeas.filter((a) => {
      if (!col.statuses.includes(a.status)) return false
      if (filterCategory && a.category_id !== filterCategory) return false
      if (filterSearch) {
        const q = filterSearch.toLowerCase()
        if (!a.title.toLowerCase().includes(q) && !(a.keyword ?? '').toLowerCase().includes(q)) return false
      }
      if (filterMinScore > 0) {
        const score = a.opportunity_score !== null ? Math.round(a.opportunity_score * 100) : 0
        if (score < filterMinScore) return false
      }
      return true
    })
  }

  async function handleAction(action: string, article: Article) {
    if (!projectId) return
    if (action === 'open') {
      navigate(`/projects/${projectId}/articles/${article.id}/edit`)
      return
    }
    if (action === 'reject') {
      setRejectTarget(article)
      return
    }
    try {
      setActionError('')
      if (action === 'prioritize') {
        await setIdeaPriority(article.id, 1)
      } else if (action === 'start-writing') {
        const res = await startWriting(article.id)
        navigate(`/projects/${projectId}/articles/${res.id}/edit`)
        return
      } else if (action === 'manual-draft') {
        const res = await createManualDraft(article.id)
        navigate(`/projects/${projectId}/articles/${res.id}/edit`)
        return
      }
      setTick((t) => t + 1)
    } catch (err) {
      setActionError(translateIdeaError(err, 'action'))
    }
  }

  async function handleReject(e: React.FormEvent) {
    e.preventDefault()
    if (!rejectTarget) return
    setRejecting(true)
    try {
      await rejectIdea(rejectTarget.id, {
        rejection_reason: rejectReason.trim() || null,
        rejection_note: rejectNote.trim() || null,
      })
      setRejectTarget(null)
      setRejectReason('')
      setRejectNote('')
      setTick((t) => t + 1)
    } catch (err) {
      setRejectError(translateIdeaError(err, 'reject'))
    } finally {
      setRejecting(false)
    }
  }

  async function handleAutoGenerate() {
    if (!projectId) return
    setAutoError('')
    setAutoResult(null)
    setAutoGenerating(true)
    try {
      const res = await autoGenerateIdeas(projectId, autoCount)
      setAutoResult(res)
      setTick((t) => t + 1)
    } catch (err) {
      setAutoError(err instanceof Error ? err.message : 'Erreur lors de la génération automatique')
    } finally {
      setAutoGenerating(false)
    }
  }

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId) return
    setGenerateError('')
    setGenerating(true)
    try {
      await generateIdea(projectId, {
        context_hint: contextHint.trim() || null,
        preferred_title: preferredTitle.trim() || null,
      })
      setGenerateOpen(false)
      setContextHint('')
      setPreferredTitle('')
      setTick((t) => t + 1)
    } catch (err) {
      setGenerateError(translateIdeaError(err, 'generate'))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between shrink-0">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Pipeline d'idées</h1>
            <p className="mt-0.5 text-[13px] text-secondary">
              De l'idée à la publication — gérez votre cycle éditorial.
            </p>
            <div className="mt-4 flex items-start gap-2.5 rounded-[12px] border border-border bg-[#f9f9fb] px-4 py-3">
              <Info size={14} className="mt-0.5 shrink-0 text-tertiary" />
              <div className="flex-1 min-w-0">
                <p className="text-[13px] text-secondary leading-snug">
                  Générez et sélectionnez ici les idées à transformer en articles. Le suivi de production complet se fait dans le{' '}
                  <button
                    onClick={() => navigate(`/projects/${projectId}/kanban`)}
                    className="text-accent hover:underline"
                  >
                    Kanban
                  </button>.
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              icon={<RefreshCw size={13} />}
              onClick={() => setTick((t) => t + 1)}
            >
              Rafraîchir
            </Button>
            <Button
              size="sm"
              variant="secondary"
              icon={<Sparkles size={14} />}
              onClick={() => { setAutoOpen(true); setAutoResult(null); setAutoError(''); setAutoCount(3) }}
            >
              Mode automatique
            </Button>
            <Button
              size="sm"
              icon={<Plus size={14} />}
              onClick={() => setGenerateOpen(true)}
            >
              Générer une idée
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-2 shrink-0">
          <div className="flex items-center gap-1.5 rounded-[10px] border border-border bg-surface px-3 py-1.5">
            <Search size={12} className="text-tertiary" />
            <input
              type="text"
              value={filterSearch}
              onChange={(e) => setFilterSearch(e.target.value)}
              placeholder="Rechercher..."
              className="w-32 bg-transparent text-[12px] text-primary outline-none placeholder:text-tertiary"
            />
          </div>
          {categories.length > 0 && (
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="rounded-[10px] border border-border bg-surface px-3 py-1.5 text-[12px] text-secondary cursor-pointer"
            >
              <option value="">Toutes les catégories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          )}
          <select
            value={filterMinScore}
            onChange={(e) => setFilterMinScore(Number(e.target.value))}
            className="rounded-[10px] border border-border bg-surface px-3 py-1.5 text-[12px] text-secondary cursor-pointer"
          >
            <option value={0}>Tous les scores</option>
            <option value={70}>Score ≥ 70%</option>
            <option value={50}>Score ≥ 50%</option>
            <option value={30}>Score ≥ 30%</option>
          </select>
          {(filterCategory || filterSearch || filterMinScore > 0) && (
            <button
              onClick={() => { setFilterCategory(''); setFilterSearch(''); setFilterMinScore(0) }}
              className="text-[11px] text-accent hover:underline"
            >
              Réinitialiser
            </button>
          )}
        </div>

        {/* Action error banner */}
        {actionError && (
          <div className="mb-4 flex items-center justify-between rounded-[10px] border border-danger/20 bg-danger/5 px-4 py-2.5 text-[13px] text-danger shrink-0">
            <span>{actionError}</span>
            <button onClick={() => setActionError('')} className="ml-3 shrink-0 text-danger/60 hover:text-danger transition-colors">✕</button>
          </div>
        )}

        {/* Content */}
        {status === 'loading' && (
          <div className="flex gap-3">
            {PIPELINE_COLUMNS.map((col) => (
              <div key={col.key} className="flex-1 min-w-[200px]">
                <Skeleton className="h-8 w-full rounded-[10px] mb-2" />
                <Skeleton className="h-24 w-full rounded-[12px] mb-2" />
                <Skeleton className="h-24 w-full rounded-[12px]" />
              </div>
            ))}
          </div>
        )}

        {status === 'error' && (
          <ErrorState
            message="Impossible de charger le pipeline d'idées."
            onRetry={() => setTick((t) => t + 1)}
          />
        )}

        {status === 'success' && allIdeas.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-[#f0f0f2] text-tertiary">
              <Lightbulb size={22} />
            </div>
            <p className="text-[15px] font-medium text-primary">Aucune idée pour l'instant</p>
            <p className="max-w-xs text-[13px] text-secondary">
              Générez votre première idée d'article avec l'IA.
            </p>
            <Button size="sm" icon={<Plus size={14} />} onClick={() => setGenerateOpen(true)}>
              Générer une idée
            </Button>
          </div>
        )}

        {status === 'success' && allIdeas.length > 0 && (
          <div className="flex gap-3 overflow-x-auto pb-4">
            {PIPELINE_COLUMNS.map((col) => (
              <KanbanColumn
                key={col.key}
                column={col}
                articles={getColumn(col)}
                categories={categories}
                onAction={handleAction}
              />
            ))}
          </div>
        )}
      </div>

      {/* Generate idea modal */}
      <Modal
        open={generateOpen}
        onClose={() => { setGenerateOpen(false); setContextHint(''); setPreferredTitle(''); setGenerateError('') }}
        title="Générer une idée"
        size="sm"
      >
        <form onSubmit={handleGenerate} className="flex flex-col gap-4">
          {generateError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
              {generateError}
            </div>
          )}
          <Input
            label="Titre souhaité (optionnel)"
            value={preferredTitle}
            onChange={(e) => setPreferredTitle(e.target.value)}
            placeholder="ex : Comment optimiser les images pour le SEO"
            hint="Si vous laissez vide, l'IA proposera un titre."
          />
          <Input
            label="Contexte (optionnel)"
            value={contextHint}
            onChange={(e) => setContextHint(e.target.value)}
            placeholder="ex : tutoriel SEO technique, optimisation images..."
            hint="Précisions supplémentaires pour l'IA."
          />
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 justify-center"
              onClick={() => setGenerateOpen(false)}
            >
              Annuler
            </Button>
            <Button type="submit" size="sm" loading={generating} className="flex-1 justify-center">
              Générer
            </Button>
          </div>
        </form>
      </Modal>

      {/* Auto-generate ideas modal */}
      <Modal
        open={autoOpen}
        onClose={() => { setAutoOpen(false); setAutoResult(null); setAutoError('') }}
        title="Mode automatique : proposer des idées"
        size="md"
      >
        <div className="flex flex-col gap-4">
          {autoError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
              {autoError}
            </div>
          )}

          {autoResult ? (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2 text-[#1a7a3a]">
                <CheckCircle size={15} />
                <p className="text-[13px] font-semibold">{autoResult.generated} idée(s) proposée(s)</p>
              </div>
              <div className="flex flex-col gap-2 max-h-80 overflow-y-auto">
                {autoResult.ideas.map((idea) => (
                  <div key={idea.id} className="rounded-[10px] border border-border bg-[#f9f9fb] p-3">
                    <p className="text-[13px] font-medium text-primary">{idea.title}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                      {idea.keyword && (
                        <span className="rounded-full bg-accent/8 px-2 py-0.5 text-[10px] text-accent">
                          {idea.keyword}
                        </span>
                      )}
                      {idea.opportunity_score !== null && (
                        <span className="text-[10px] text-tertiary">
                          Score: {Math.round(idea.opportunity_score * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2 pt-1">
                <Button
                  variant="secondary"
                  size="sm"
                  className="flex-1 justify-center"
                  onClick={() => { setAutoOpen(false); setAutoResult(null) }}
                >
                  Fermer
                </Button>
                <Button
                  size="sm"
                  className="flex-1 justify-center"
                  onClick={() => { setAutoOpen(false); setAutoResult(null); navigate(`/projects/${projectId}/ideas`) }}
                >
                  Voir dans le pipeline
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-start gap-3 rounded-[12px] border border-border bg-[#f9f9fb] px-3.5 py-3">
                <Sparkles size={15} className="mt-0.5 shrink-0 text-accent" />
                <div>
                  <p className="text-[13px] font-medium text-primary">Génération automatique</p>
                  <p className="mt-0.5 text-[12px] text-secondary leading-snug">
                    L'IA va proposer plusieurs idées d'articles basées sur le contexte de votre projet. Les idées seront ajoutées directement dans le pipeline.
                  </p>
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[12px] font-medium text-secondary">Nombre d'idées</label>
                <select
                  value={autoCount}
                  onChange={(e) => setAutoCount(Number(e.target.value))}
                  className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[13px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
                >
                  <option value={1}>1 idée</option>
                  <option value={3}>3 idées</option>
                  <option value={5}>5 idées</option>
                  <option value={10}>10 idées</option>
                </select>
              </div>
              <div className="flex gap-2 pt-1">
                <Button
                  variant="secondary"
                  size="sm"
                  className="flex-1 justify-center"
                  onClick={() => { setAutoOpen(false); setAutoResult(null) }}
                >
                  Annuler
                </Button>
                <Button
                  size="sm"
                  loading={autoGenerating}
                  className="flex-1 justify-center"
                  onClick={handleAutoGenerate}
                >
                  Proposer des idées
                </Button>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Reject modal */}
      <Modal
        open={!!rejectTarget}
        onClose={() => { setRejectTarget(null); setRejectReason(''); setRejectNote(''); setRejectError('') }}
        title="Rejeter cette idée"
        size="sm"
      >
        <form onSubmit={handleReject} className="flex flex-col gap-4">
          {rejectError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
              {rejectError}
            </div>
          )}
          <p className="text-[13px] text-secondary">
            Idée : <strong className="text-primary">{rejectTarget?.title}</strong>
          </p>
          <Input
            label="Raison (optionnel)"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="Hors sujet, doublon..."
          />
          <Textarea
            label="Note détaillée (optionnel)"
            value={rejectNote}
            onChange={(e) => setRejectNote(e.target.value)}
            rows={2}
            placeholder="Explications supplémentaires..."
          />
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 justify-center"
              onClick={() => { setRejectTarget(null); setRejectError('') }}
            >
              Annuler
            </Button>
            <Button
              type="submit"
              variant="danger"
              size="sm"
              loading={rejecting}
              className="flex-1 justify-center"
            >
              Rejeter
            </Button>
          </div>
        </form>
      </Modal>
    </>
  )
}
