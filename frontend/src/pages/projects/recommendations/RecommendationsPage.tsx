import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Sparkles, RefreshCw, Pencil, Check, X, Zap, Loader2, FileText } from '@/components/ui/hugeIcons'
import {
  listRecommendations,
  triggerReview,
  acceptRecommendation,
  rejectRecommendation,
  applyRecommendation,
} from '@/api/recommendations'
import { listArticles } from '@/api/articles'
import { ApiError } from '@/api/client'
import type { OptimizationRecommendation, RecommendationStatus } from '@/types'
import { formatDate } from '@/utils/format'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'

// ── Labels ─────────────────────────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  improve_title: 'Améliorer le titre',
  improve_meta_description: 'Améliorer la meta description',
  add_faq: 'Ajouter une FAQ',
  add_internal_links: 'Ajouter des liens internes',
  refresh_content: 'Rafraîchir le contenu',
  improve_intro: "Améliorer l'introduction",
  improve_eeat: 'Renforcer l\'EEAT',
  expand_section: 'Développer une section',
  fix_low_traffic: 'Corriger le trafic faible',
  update_keywords: 'Mettre à jour les mots-clés',
}

const STATUS_LABELS: Record<RecommendationStatus, string> = {
  pending: 'En attente',
  accepted: 'Acceptée',
  rejected: 'Rejetée',
  applied: 'Appliquée',
}

const STATUS_CLASSES: Record<RecommendationStatus, string> = {
  pending: 'bg-accent/8 text-accent',
  accepted: 'bg-success/8 text-success',
  rejected: 'bg-surface-soft text-tertiary',
  applied: 'bg-success/15 text-success font-medium',
}

function priorityDot(priority: number) {
  const color = priority >= 3 ? 'bg-danger' : priority === 2 ? 'bg-warning' : 'bg-[#c8c8cc]'
  const label = priority >= 3 ? 'Haute' : priority === 2 ? 'Normale' : 'Basse'
  return (
    <span className="inline-flex items-center gap-1 text-[12px] text-tertiary">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
      {label}
    </span>
  )
}

function translateRecError(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 403: return 'Vous n\'avez pas la permission d\'effectuer cette action.'
      case 409:
      case 400: return err.message || 'Cette action n\'est pas possible dans l\'état actuel.'
      case 422: return 'Données invalides.'
      default: return err.message || `Erreur ${err.status}`
    }
  }
  return 'Une erreur inattendue est survenue.'
}

// ── Card ───────────────────────────────────────────────────────────────────

function RecommendationCard({
  rec,
  articleTitle,
  onUpdate,
  onNavigate,
}: {
  rec: OptimizationRecommendation
  articleTitle?: string
  onUpdate: (updated: OptimizationRecommendation) => void
  onNavigate: (articleId: string) => void
}) {
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [error, setError] = useState('')

  const status = rec.status as RecommendationStatus

  async function doAction(action: 'accept' | 'reject' | 'apply') {
    setLoadingAction(action)
    setError('')
    try {
      let updated: OptimizationRecommendation
      if (action === 'accept') updated = await acceptRecommendation(rec.id)
      else if (action === 'reject') updated = await rejectRecommendation(rec.id)
      else updated = await applyRecommendation(rec.id)
      onUpdate(updated)
    } catch (err) {
      setError(translateRecError(err))
    } finally {
      setLoadingAction(null)
    }
  }

  const busy = loadingAction !== null
  const isPending = status === 'pending'
  const isAccepted = status === 'accepted'

  return (
    <div className="rounded-[16px] border-2 border-border bg-transparent p-4 shadow-none hover:shadow-none transition-shadow">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex flex-col gap-1 flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[12px] font-medium text-secondary bg-surface-soft rounded-full px-2 py-0.5">
              {TYPE_LABELS[rec.type] ?? rec.type}
            </span>
            {priorityDot(rec.priority)}
            {articleTitle && (
              <span className="flex items-center gap-1 text-[12px] text-tertiary truncate max-w-[160px]">
                <FileText size={10} />
                {articleTitle}
              </span>
            )}
          </div>
          <p className="text-[14px] font-medium text-primary leading-snug mt-1">{rec.reason}</p>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] ${STATUS_CLASSES[status] ?? 'bg-surface-soft text-tertiary'}`}>
          {STATUS_LABELS[status] ?? rec.status}
        </span>
      </div>

      <p className="text-[12px] text-secondary leading-snug mb-3">{rec.suggestion}</p>

      {error && (
        <p className="mb-2 rounded-[8px] bg-danger/5 px-2.5 py-1.5 text-[12px] text-danger">{error}</p>
      )}

      <div className="flex items-center gap-2 flex-wrap">
        {rec.article_id && (
          <button
            onClick={() => onNavigate(rec.article_id!)}
            className="inline-flex items-center gap-1 rounded-full border border-primary bg-primary px-2.5 py-1 text-[12px] font-medium text-white transition-colors hover:opacity-90"
          >
            <Pencil size={11} />
            Voir l'article
          </button>
        )}
        {(isPending || isAccepted) && (
          <button
            onClick={() => doAction('apply')}
            disabled={busy}
            className="inline-flex items-center gap-1 rounded-full border border-accent/20 bg-accent/8 px-2.5 py-1 text-[12px] font-medium text-accent transition-colors hover:bg-accent/12 disabled:opacity-40"
          >
            {loadingAction === 'apply' ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />}
            Appliquer
          </button>
        )}
        {isPending && (
          <>
            <button
              onClick={() => doAction('accept')}
              disabled={busy}
              className="inline-flex items-center gap-1 rounded-full border border-success/20 bg-success/8 px-2.5 py-1 text-[12px] font-medium text-success transition-colors hover:bg-success/12 disabled:opacity-40"
            >
              {loadingAction === 'accept' ? <Loader2 size={11} className="animate-spin" /> : <Check size={11} />}
              Accepter
            </button>
            <button
              onClick={() => doAction('reject')}
              disabled={busy}
              className="inline-flex items-center gap-1 rounded-full border border-danger/20 bg-danger/5 px-2.5 py-1 text-[12px] font-medium text-danger transition-colors hover:bg-danger/10 disabled:opacity-40"
            >
              {loadingAction === 'reject' ? <Loader2 size={11} className="animate-spin" /> : <X size={11} />}
              Rejeter
            </button>
          </>
        )}
        <span className="ml-auto text-[10px] text-tertiary">{formatDate(rec.created_at)}</span>
      </div>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────

type FilterStatus = 'all' | RecommendationStatus

export default function RecommendationsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [recs, setRecs] = useState<OptimizationRecommendation[]>([])
  const [articleTitles, setArticleTitles] = useState<Record<string, string>>({})
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all')
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewError, setReviewError] = useState('')
  const [reviewSuccess, setReviewSuccess] = useState('')

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    Promise.all([
      listRecommendations(projectId),
      listArticles(projectId, { status: 'published', limit: 500 }),
    ])
      .then(([data, articles]) => {
        if (!cancelled) {
          setRecs(data)
          const titles: Record<string, string> = {}
          for (const a of articles) titles[a.id] = a.title
          setArticleTitles(titles)
          setLoadStatus('success')
        }
      })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, tick])

  async function handleReview() {
    if (!projectId) return
    setReviewLoading(true)
    setReviewError('')
    setReviewSuccess('')
    try {
      const result = await triggerReview(projectId)
      const n = result.generated ?? 0
      setReviewSuccess(n > 0 ? `${n} recommandation${n > 1 ? 's' : ''} générée${n > 1 ? 's' : ''}.` : 'Aucune nouvelle recommandation.')
      setTick((t) => t + 1)
    } catch (err) {
      setReviewError(translateRecError(err))
    } finally {
      setReviewLoading(false)
    }
  }

  function handleUpdate(updated: OptimizationRecommendation) {
    setRecs((prev) => prev.map((r) => r.id === updated.id ? updated : r))
  }

  const filtered = filterStatus === 'all' ? recs : recs.filter((r) => r.status === filterStatus)

  const STATUS_FILTERS: { value: FilterStatus; label: string }[] = [
    { value: 'all', label: 'Toutes' },
    { value: 'pending', label: 'En attente' },
    { value: 'accepted', label: 'Acceptées' },
    { value: 'applied', label: 'Appliquées' },
    { value: 'rejected', label: 'Rejetées' },
  ]

  return (
    <div className="mx-auto max-w-3xl">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-[20px] font-semibold text-primary tracking-tight">Optimisations</h1>
          <p className="mt-0.5 text-[14px] text-secondary">Optimisez vos contenus publiés.</p>
        </div>
        <Button
          size="sm"
          variant="secondary"
          icon={<RefreshCw size={13} />}
          loading={reviewLoading}
          onClick={handleReview}
        >
          Analyser les articles
        </Button>
      </div>

      {/* Feedback banners */}
      {reviewError && (
        <div className="mb-4 rounded-[10px] border border-danger/20 bg-danger/5 px-4 py-2.5 text-[14px] text-danger">
          {reviewError}
        </div>
      )}
      {reviewSuccess && (
        <div className="mb-4 rounded-[10px] border border-success/20 bg-success/8 px-4 py-2.5 text-[14px] text-success">
          {reviewSuccess}
        </div>
      )}

      {/* Status filters */}
      {loadStatus === 'success' && recs.length > 0 && (
        <div className="mb-5 flex gap-1.5 flex-wrap">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilterStatus(f.value)}
              className={`rounded-full px-3 py-1 text-[12px] font-medium transition-colors ${
                filterStatus === f.value
                  ? 'bg-accent text-white'
                  : 'bg-surface-soft text-secondary hover:bg-surface-muted hover:text-primary'
              }`}
            >
              {f.label}
              {f.value === 'all' && ` (${recs.length})`}
              {f.value !== 'all' && ` (${recs.filter(r => r.status === f.value).length})`}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {loadStatus === 'loading' && <LoadingState />}
      {loadStatus === 'error' && (
        <ErrorState
          message="Impossible de charger les recommandations."
          onRetry={() => setTick((t) => t + 1)}
        />
      )}
      {loadStatus === 'success' && recs.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-20 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-[16px] border border-border bg-transparent text-tertiary">
            <Sparkles size={22} />
          </div>
          <div>
            <p className="text-[15px] font-medium text-primary">Aucune recommandation pour l'instant</p>
            <p className="mt-1 max-w-sm text-[14px] text-secondary">
              Cliquez sur "Analyser les articles" pour que l'IA détecte les améliorations à apporter à vos contenus publiés.
            </p>
          </div>
        </div>
      )}
      {loadStatus === 'success' && recs.length > 0 && filtered.length === 0 && (
        <div className="py-12 text-center text-[14px] text-tertiary">
          Aucune recommandation avec ce filtre.
        </div>
      )}
      {loadStatus === 'success' && filtered.length > 0 && (() => {
        const high   = filtered.filter((r) => r.priority >= 3)
        const normal = filtered.filter((r) => r.priority === 2)
        const low    = filtered.filter((r) => r.priority <= 1)
        const groups = [
          { key: 'high',   label: 'Haute priorité',   recs: high },
          { key: 'normal', label: 'Priorité normale', recs: normal },
          { key: 'low',    label: 'Basse priorité',   recs: low },
        ].filter((g) => g.recs.length > 0)

        return (
          <div className="flex flex-col gap-6">
            {groups.map((group) => (
              <div key={group.key}>
                <p className="mb-2.5 text-[12px] font-semibold text-secondary uppercase tracking-wide">
                  {group.label} <span className="ml-1 normal-case font-normal text-tertiary">({group.recs.length})</span>
                </p>
                <div className="flex flex-col gap-3">
                  {group.recs.map((rec) => (
                    <RecommendationCard
                      key={rec.id}
                      rec={rec}
                      articleTitle={rec.article_id ? articleTitles[rec.article_id] : undefined}
                      onUpdate={handleUpdate}
                      onNavigate={(aid) => navigate(`/projects/${projectId}/articles/${aid}/edit`)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )
      })()}
    </div>
  )
}
