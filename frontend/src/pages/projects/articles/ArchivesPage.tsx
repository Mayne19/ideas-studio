import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FileText, Pencil, Trash2, RotateCcw, Send } from '@/components/ui/hugeIcons'
import { listArticles, publishArticle, unarchiveArticle, deleteArticle } from '@/api/articles'
import { listCategories } from '@/api/categories'
import type { Article, Category } from '@/types'
import { formatDate } from '@/utils/format'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import StatusBadge from '@/components/ui/StatusBadge'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'
import Toolbar from '@/components/ui/Toolbar'
import ArticleScoreBadges from '@/components/ui/ArticleScoreBadges'
import { finiteScore, getGeoScore, getOriginalityScore } from '@/lib/scoreBadge'

const PAGE_SIZE = 20

type ScoreFilter = '' | 'global_gte_90' | 'global_lt_90' | 'seo_lt_85' | 'quality_lt_85' | 'readability_lt_80' | 'geo_lt_80' | 'originality_lt_85' | 'critical'

function getCost(article: Article): number | null {
  const costJson = article.estimated_cost_json
  if (!costJson || typeof costJson !== 'object') return null
  const cost = (costJson as Record<string, unknown>).estimated_cost_eur
  return typeof cost === 'number' && Number.isFinite(cost) ? cost : null
}

const TABLE_GRID = 'lg:grid-cols-[minmax(240px,1.2fr)_minmax(300px,auto)_80px_90px_130px]'

function ArticleRow({
  article,
  categories,
  onEdit,
  onAction,
}: {
  article: Article
  categories: Category[]
  onEdit: (a: Article) => void
  onAction: (key: string, a: Article) => void
}) {
  const category = categories.find((c) => c.id === article.category_id)

  return (
    <div className={`grid gap-2.5 rounded-[12px] bg-surface px-3 py-3 transition-colors hover:bg-[#f5f5f7] lg:items-center ${TABLE_GRID}`}>
      <div className="min-w-0">
        <button
          type="button"
          className="block w-full truncate text-left text-[13px] font-medium leading-snug text-primary transition-colors hover:text-accent"
          onClick={() => onEdit(article)}
          title={article.title}
        >
          {article.title}
        </button>
        <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-tertiary">
          <span
            className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium whitespace-nowrap ${category?.color ? '' : 'bg-surface-soft text-tertiary'}`}
            style={category?.color ? { backgroundColor: `${category.color}20`, color: category.color } : undefined}
          >
            {category?.name ?? 'Sans catégorie'}
          </span>
          <span>·</span>
          <span>{article.published_at ? formatDate(article.published_at) : formatDate(article.updated_at)}</span>
          <span>·</span>
          <span>{article.author_name ?? 'Auteur —'}</span>
          <span>·</span>
          <span>{article.word_count > 0 ? `${article.word_count} mots` : '— mots'}</span>
        </div>
      </div>
      <ArticleScoreBadges article={article} />
      <div className="flex items-center">
        {(() => {
          const cost = getCost(article)
          return cost !== null ? (
            <span className="inline-flex items-center rounded-full bg-[#eef2ff] px-1.5 py-0.5 text-[10px] font-medium text-[#4f46e5]">
              {cost.toFixed(4)} €
            </span>
          ) : (
            <span className="inline-flex items-center rounded-full bg-surface-soft px-1.5 py-0.5 text-[10px] font-medium text-tertiary">
              — €
            </span>
          )
        })()}
      </div>
      <div className="flex items-center">
        <StatusBadge status={article.status} />
      </div>
      <div className="flex items-center gap-3 lg:justify-end">
        <button
          type="button"
          onClick={() => onEdit(article)}
          className="flex h-8 shrink-0 items-center justify-center gap-1.5 rounded-[8px] bg-accent px-3 text-[12px] font-medium text-white transition-colors hover:bg-accent/90"
          title="Éditer"
        >
          <Pencil size={12} />
          Éditer
        </button>
        <select
          onChange={(e) => { if (e.target.value) { onAction(e.target.value, article); e.target.value = '' } }}
          className="h-8 w-[82px] cursor-pointer rounded-[8px] border border-border bg-surface px-1.5 text-[11px] text-secondary transition-colors hover:bg-surface-muted"
          defaultValue=""
          aria-label={`Actions pour ${article.title}`}
        >
          <option value="" disabled>Actions</option>
          <option value="preview">Voir aperçu</option>
          <option value="restore">Restaurer en production</option>
          <option value="republish">Republier directement</option>
          <option value="delete">Supprimer</option>
        </select>
      </div>
    </div>
  )
}

export default function ArchivesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [articles, setArticles] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const [filterCategory, setFilterCategory] = useState('')
  const [filterSearch, setFilterSearch] = useState('')
  const [filterScore, setFilterScore] = useState<ScoreFilter>('')
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [debouncedSearch, setDebouncedSearch] = useState('')

  const [tick, setTick] = useState(0)
  const [actionError, setActionError] = useState('')

  const [deleteTarget, setDeleteTarget] = useState<Article | null>(null)
  const [deleting, setDeleting] = useState(false)

  const [restoreTarget, setRestoreTarget] = useState<Article | null>(null)
  const [restoring, setRestoring] = useState(false)

  const [republishTarget, setRepublishTarget] = useState<Article | null>(null)
  const [republishing, setRepublishing] = useState(false)

  useEffect(() => {
    if (!projectId) return
    listCategories(projectId).then(setCategories).catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setStatus('loading') })
    listArticles(projectId, {
      archived: true,
      category_id: filterCategory || undefined,
      search: debouncedSearch || undefined,
      skip: 0,
      limit: PAGE_SIZE,
    })
      .then((data) => {
        if (!cancelled) {
          setArticles(data)
          setHasMore(data.length === PAGE_SIZE)
          setStatus('success')
        }
      })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }, [projectId, filterCategory, debouncedSearch, tick])

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFilterSearch(e.target.value)
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => setDebouncedSearch(e.target.value), 400)
  }

  function loadMore() {
    if (!projectId) return
    setLoadingMore(true)
    listArticles(projectId, {
      archived: true,
      category_id: filterCategory || undefined,
      search: debouncedSearch || undefined,
      skip: articles.length,
      limit: PAGE_SIZE,
    })
      .then((data) => {
        setArticles((prev) => [...prev, ...data])
        setHasMore(data.length === PAGE_SIZE)
        setLoadingMore(false)
      })
      .catch(() => setLoadingMore(false))
  }

  async function handleAction(key: string, article: Article) {
    if (!projectId) return
    if (key === 'delete') {
      setDeleteTarget(article)
      return
    }
    if (key === 'restore') {
      setRestoreTarget(article)
      return
    }
    if (key === 'republish') {
      setRepublishTarget(article)
      return
    }
    if (key === 'preview') {
      navigate(`/projects/${projectId}/articles/${article.id}/preview`)
      return
    }
  }

  async function handleRestoreConfirm() {
    if (!projectId || !restoreTarget) return
    setRestoring(true)
    try {
      await unarchiveArticle(projectId, restoreTarget.id)
      setArticles((prev) => prev.filter((a) => a.id !== restoreTarget.id))
      setRestoreTarget(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de la restauration.')
      setRestoreTarget(null)
    } finally {
      setRestoring(false)
    }
  }

  async function handleRepublishConfirm() {
    if (!projectId || !republishTarget) return
    setRepublishing(true)
    try {
      const updated = await publishArticle(projectId, republishTarget.id)
      setArticles((prev) => prev.filter((a) => a.id !== updated.id))
      setRepublishTarget(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de la republication.')
      setRepublishTarget(null)
    } finally {
      setRepublishing(false)
    }
  }

  async function handleDeleteConfirm() {
    if (!projectId || !deleteTarget) return
    setDeleting(true)
    try {
      await deleteArticle(projectId, deleteTarget.id)
      setArticles((prev) => prev.filter((a) => a.id !== deleteTarget.id))
      setDeleteTarget(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de la suppression.')
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  const categoryOptions = [
    { value: '', label: 'Toutes les catégories' },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ]

  const scoreOptions = [
    { value: '', label: 'Tous les scores' },
    { value: 'global_gte_90', label: 'Global ≥ 90' },
    { value: 'global_lt_90', label: 'Global < 90' },
    { value: 'seo_lt_85', label: 'SEO < 85' },
    { value: 'quality_lt_85', label: 'Qualité < 85' },
    { value: 'readability_lt_80', label: 'Lisibilité < 80' },
    { value: 'geo_lt_80', label: 'GEO < 80' },
    { value: 'originality_lt_85', label: 'Originalité < 85' },
  ]

  function matchesScoreFilter(article: Article) {
    const g = finiteScore(article.global_score)
    const s = finiteScore(article.seo_score)
    const q = finiteScore(article.quality_score)
    const geo = getGeoScore(article)
    const o = getOriginalityScore(article)
    const r = finiteScore(article.readability_score)
    if (filterScore === 'global_gte_90') return g !== null && g >= 90
    if (filterScore === 'global_lt_90') return g === null || g < 90
    if (filterScore === 'seo_lt_85') return s === null || s < 85
    if (filterScore === 'quality_lt_85') return q === null || q < 85
    if (filterScore === 'readability_lt_80') return r === null || r < 80
    if (filterScore === 'geo_lt_80') return geo === null || geo < 80
    if (filterScore === 'originality_lt_85') return o === null || o < 85
    return true
  }

  const visibleArticles = articles.filter(matchesScoreFilter)

  return (
    <>
      <div className="project-page project-page--wide">
        {/* Header */}
        <div className="project-page-header">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Archives</h1>
            <p className="mt-0.5 text-[13px] text-secondary">
              Articles retirés du site et rangés hors production.
            </p>
          </div>
        </div>

        {/* Action error banner */}
        {actionError && (
          <div className="mb-4 flex items-center justify-between rounded-[10px] border border-danger/20 bg-danger/5 px-4 py-2.5 text-[13px] text-danger">
            <span>{actionError}</span>
            <button onClick={() => setActionError('')} className="ml-3 shrink-0 text-danger/60 hover:text-danger transition-colors">✕</button>
          </div>
        )}

        {/* Filters */}
        <Toolbar>
          <Input
            placeholder="Rechercher..."
            value={filterSearch}
            onChange={handleSearchChange}
            className="w-[440px] max-w-full"
          />
          <Select
            options={scoreOptions}
            value={filterScore}
            onChange={(e) => setFilterScore(e.target.value as ScoreFilter)}
            className="w-[185px]"
          />
          {categories.length > 0 && (
            <Select
              options={categoryOptions}
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="w-[185px]"
            />
          )}
        </Toolbar>

        {/* Content */}
        {status === 'loading' && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-[12px]" />
            ))}
          </div>
        )}
        {status === 'error' && (
          <ErrorState message="Impossible de charger les archives." onRetry={() => setTick((t) => t + 1)} />
        )}
        {status === 'success' && visibleArticles.length === 0 && (
          <EmptyState
            icon={<FileText size={22} />}
            title="Aucun article archivé"
            description="Les articles archivés apparaîtront ici."
          />
        )}
        {status === 'success' && visibleArticles.length > 0 && (
          <>
            <div className={`hidden gap-2.5 px-3 pb-1.5 text-[11px] font-medium uppercase tracking-wide text-tertiary lg:grid ${TABLE_GRID}`}>
              <div>Titre</div>
              <div>Scores</div>
              <div>Coût</div>
              <div>Statut</div>
              <div className="text-right">Actions</div>
            </div>
            <div className="flex flex-col gap-1.5">
              {visibleArticles.map((article) => (
                <ArticleRow
                  key={article.id}
                  article={article}
                  categories={categories}
                  onEdit={(a) => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
                  onAction={handleAction}
                />
              ))}
            </div>
            {hasMore && (
              <div className="mt-4 flex justify-center">
                <Button variant="secondary" size="sm" loading={loadingMore} onClick={loadMore}>
                  Charger plus
                </Button>
              </div>
            )}
          </>
        )}
      </div>

      {/* Restore confirm modal */}
      <Modal
        open={!!restoreTarget}
        onClose={() => setRestoreTarget(null)}
        title="Restaurer en production ?"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 rounded-[12px] border border-accent/20 bg-accent/5 px-3.5 py-3">
            <RotateCcw size={15} className="mt-0.5 shrink-0 text-accent" />
            <div>
              <p className="text-[13px] font-medium text-primary">{restoreTarget?.title}</p>
              <p className="mt-0.5 text-[12px] text-secondary leading-snug">
                L'article sera restauré en Production et pourra être retravaillé avant publication.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setRestoreTarget(null)}>
              Annuler
            </Button>
            <Button size="sm" loading={restoring} className="flex-1 justify-center" onClick={handleRestoreConfirm}>
              Restaurer
            </Button>
          </div>
        </div>
      </Modal>

      {/* Republish confirm modal */}
      <Modal
        open={!!republishTarget}
        onClose={() => setRepublishTarget(null)}
        title="Republier directement ?"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 rounded-[12px] border border-success/20 bg-success/5 px-3.5 py-3">
            <Send size={15} className="mt-0.5 shrink-0 text-[#1a7a3a]" />
            <div>
              <p className="text-[13px] font-medium text-primary">{republishTarget?.title}</p>
              <p className="mt-0.5 text-[12px] text-secondary leading-snug">
                L'article sera remis en ligne immédiatement sur le site public.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setRepublishTarget(null)}>
              Annuler
            </Button>
            <Button size="sm" variant="primary" loading={republishing} className="flex-1 justify-center" onClick={handleRepublishConfirm}>
              Republier
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete confirm modal */}
      <Modal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Supprimer cet article ?"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 rounded-[12px] border border-danger/20 bg-danger/5 px-3.5 py-3">
            <Trash2 size={15} className="mt-0.5 shrink-0 text-danger" />
            <div>
              <p className="text-[13px] font-medium text-primary">{deleteTarget?.title}</p>
              <p className="mt-0.5 text-[12px] text-secondary leading-snug">
                Cette action est critique. L'article sera supprimé selon la logique de suppression existante.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setDeleteTarget(null)}>
              Annuler
            </Button>
            <Button size="sm" variant="danger" loading={deleting} className="flex-1 justify-center" onClick={handleDeleteConfirm}>
              Supprimer
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}
