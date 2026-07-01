import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus, FileText, Edit3, Trash2, Sparkles, Zap, Loader2, CheckCircle, Archive, EyeOff } from '@/components/ui/hugeIcons'
import { listArticles, createArticle, unpublishArticle, archiveArticle, analyzeSeoArticle, deleteArticle, generateArticle } from '@/api/articles'
import type { CreateArticlePayload, GenerateArticleRequest } from '@/api/articles'
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
import ToggleSwitch from '@/components/ui/ToggleSwitch'
import { TableRoot, Table, TableHeader, TableHead, TableBody, TableRow, TableCell } from '@/components/ui/Table'
import { finiteScore, getGeoScore, getOriginalityScore } from '@/lib/scoreBadge'
import ScoreBadge from '@/components/ui/ScoreBadge'
import { useProject } from '@/context/ProjectContext'
import { Combobox, ComboboxContent, ComboboxEmpty, ComboboxInput, ComboboxList, ComboboxItem } from '@/components/ui/combobox'

const PAGE_SIZE = 20

type ScoreFilter = '' | 'global_gte_90' | 'global_lt_90' | 'seo_lt_85' | 'quality_lt_85' | 'readability_lt_80' | 'geo_lt_80' | 'originality_lt_85' | 'critical'

function getPublicUrl(domain: string | undefined | null, slug: string): string {
  if (!domain) return ''
  const base = domain.startsWith('http') ? domain : `https://${domain}`
  return `${base}/${slug}`
}

function getUniqueAuthors(articles: Article[]): string[] {
  const names = new Set<string>()
  articles.forEach((a) => { if (a.author_name) names.add(a.author_name) })
  return Array.from(names).sort()
}

const PUBLISHED_STATUSES = new Set(['published', 'scheduled'])
const EDITABLE_STATUSES = new Set([
  'draft', 'outline_ready', 'writing_requested', 'writing_in_progress',
  'draft_ready', 'review_needed', 'correction_needed', 'ready_to_publish',
  'update_recommended', 'failed',
])

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
  const isPublished = PUBLISHED_STATUSES.has(article.status)
  const isEditable = EDITABLE_STATUSES.has(article.status)
  const [actionValue, setActionValue] = useState('')
  const actionItems = [
    ...(isPublished ? [{ value: 'view-site', label: 'Voir sur le site' }] : []),
    ...(isEditable ? [{ value: 'analyze-seo', label: 'Analyser SEO' }] : []),
    ...(isPublished ? [{ value: 'unpublish', label: 'Dépublier' }] : []),
    ...(!isPublished ? [{ value: 'archive', label: 'Archiver' }] : []),
    { value: 'delete', label: 'Supprimer' },
  ]
  const originalityScore = getOriginalityScore(article)
  const rowCellClass = 'border-y-2 border-border bg-transparent py-2.5 transition-colors first:rounded-l-[12px] first:border-l-2 last:rounded-r-[12px] last:border-r-2 group-hover:bg-surface-soft'
  const scoreCellClass = `w-[40px] px-1 text-center ${rowCellClass}`

  return (
    <TableRow className="group hover:bg-transparent">
      <TableCell className={`min-w-0 ${rowCellClass} pr-8`}>
        <button
          type="button"
          className="block w-full truncate text-left text-[14px] font-medium leading-snug text-primary transition-colors hover:text-accent"
          onClick={() => onEdit(article)}
          title={article.title}
        >
          {article.title}
        </button>
        <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[12px] text-tertiary">
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
      </TableCell>
      <TableCell className={`${scoreCellClass} pl-4`}>
        <ScoreBadge label="G" value={finiteScore(article.global_score)} compact showLabel={false} />
      </TableCell>
      <TableCell className={scoreCellClass}>
        <ScoreBadge label="S" value={finiteScore(article.seo_score)} compact showLabel={false} />
      </TableCell>
      <TableCell className={scoreCellClass}>
        <ScoreBadge label="GEO" value={getGeoScore(article)} compact showLabel={false} />
      </TableCell>
      <TableCell className={scoreCellClass}>
        <ScoreBadge label="Q" value={finiteScore(article.quality_score)} compact showLabel={false} />
      </TableCell>
      <TableCell className={scoreCellClass}>
        <ScoreBadge label="L" value={finiteScore(article.readability_score)} compact showLabel={false} />
      </TableCell>
      <TableCell className={scoreCellClass}>
        <ScoreBadge label="O" value={originalityScore} compact showLabel={false} />
      </TableCell>
      <TableCell className={`${scoreCellClass} pr-4`}>
        <ScoreBadge label="E" value={finiteScore(article.eeat_score)} compact showLabel={false} />
      </TableCell>
      <TableCell className={`w-[124px] text-center ${rowCellClass} px-5`}>
        <StatusBadge status={article.status} />
      </TableCell>
      <TableCell className={`w-[206px] ${rowCellClass} pl-5`}>
        <div className="flex items-center justify-end gap-2">
          <Button
            size="sm"
            icon={<Edit3 size={12} />}
            onClick={() => onEdit(article)}
            title="Éditer"
            className="h-8 px-2.5 text-[12px]"
          >
            Éditer
          </Button>
          <div className="relative">
            <Combobox items={actionItems} value={actionValue} onValueChange={(v) => { onAction(v, article); setActionValue('') }}>
              <ComboboxInput placeholder="Actions" className="h-8 w-[92px] text-[12px]" />
              <ComboboxContent>
                <ComboboxEmpty>Aucune action</ComboboxEmpty>
                <ComboboxList>
                  {(item) => (
                    <ComboboxItem key={item.value} value={item.value}>
                      {item.label}
                    </ComboboxItem>
                  )}
                </ComboboxList>
              </ComboboxContent>
            </Combobox>
          </div>
        </div>
      </TableCell>
    </TableRow>
  )
}

export default function ArticlesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { project } = useProject()

  const [articles, setArticles] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [hasMore, setHasMore] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const [filterCategory, setFilterCategory] = useState('')
  const [filterSearch, setFilterSearch] = useState('')
  const [filterAuthor, setFilterAuthor] = useState('')
  const [filterScore, setFilterScore] = useState<ScoreFilter>('')
  const [filterStatus, setFilterStatus] = useState('')
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [debouncedSearch, setDebouncedSearch] = useState('')

  const [tick, setTick] = useState(0)
  const [actionError, setActionError] = useState('')

  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState({ title: '', keyword: '', category_id: '' })
  const [createError, setCreateError] = useState('')
  const [creating, setCreating] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState<Article | null>(null)
  const [deleting, setDeleting] = useState(false)

  const [unpublishTarget, setUnpublishTarget] = useState<Article | null>(null)
  const [unpublishing, setUnpublishing] = useState(false)

  const [archiveTarget, setArchiveTarget] = useState<Article | null>(null)
  const [archiving, setArchiving] = useState(false)

  const [generateOpen, setGenerateOpen] = useState(false)
  const [generateForm, setGenerateForm] = useState<GenerateArticleRequest>({})
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')
  const [generateResult, setGenerateResult] = useState<{ id: string; title: string } | null>(null)

  useEffect(() => {
    if (!projectId) return
    listCategories(projectId).then(setCategories).catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setStatus('loading') })
    listArticles(projectId, {
      status: filterStatus || undefined,
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
  }, [projectId, filterCategory, filterStatus, debouncedSearch, tick])

  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    setFilterSearch(e.target.value)
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => setDebouncedSearch(e.target.value), 400)
  }

  function loadMore() {
    if (!projectId) return
    setLoadingMore(true)
    listArticles(projectId, {
      status: filterStatus || undefined,
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

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || !createForm.title.trim()) return
    setCreateError('')
    setCreating(true)
    try {
      const payload: CreateArticlePayload = {
        title: createForm.title.trim(),
        keyword: createForm.keyword.trim() || undefined,
        category_id: createForm.category_id || undefined,
      }
      const article = await createArticle(projectId, payload)
      setCreateOpen(false)
      setCreateForm({ title: '', keyword: '', category_id: '' })
      navigate(`/projects/${projectId}/articles/${article.id}/edit`)
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Erreur lors de la création')
    } finally {
      setCreating(false)
    }
  }

  async function handleAction(key: string, article: Article) {
    if (!projectId) return
    if (key === 'delete') {
      setDeleteTarget(article)
      return
    }
    if (key === 'unpublish') {
      setUnpublishTarget(article)
      return
    }
    if (key === 'archive') {
      setArchiveTarget(article)
      return
    }
    if (key === 'view-site') {
      const url = getPublicUrl(project?.domain ?? project?.public_site_url, article.slug)
      if (url) window.open(url, '_blank', 'noopener,noreferrer')
      return
    }
    setActionError('')
    try {
      if (key === 'analyze-seo') {
        await analyzeSeoArticle(projectId, article.id)
        setTick((t) => t + 1)
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de l\'action.')
    }
  }

  async function handleUnpublishConfirm() {
    if (!projectId || !unpublishTarget) return
    setUnpublishing(true)
    try {
      const updated = await unpublishArticle(projectId, unpublishTarget.id)
      setArticles((prev) => prev.filter((a) => a.id !== updated.id))
      setUnpublishTarget(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de la dépublication.')
      setUnpublishTarget(null)
    } finally {
      setUnpublishing(false)
    }
  }

  async function handleArchiveConfirm() {
    if (!projectId || !archiveTarget) return
    setArchiving(true)
    try {
      const updated = await archiveArticle(projectId, archiveTarget.id)
      setArticles((prev) => prev.filter((a) => a.id !== updated.id))
      setArchiveTarget(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de l\'archivage.')
      setArchiveTarget(null)
    } finally {
      setArchiving(false)
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

  async function handleGenerate(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId) return
    setGenerateError('')
    setGenerateResult(null)
    setGenerating(true)
    try {
      const res = await generateArticle(projectId, generateForm)
      setGenerateResult({ id: res.id, title: res.title })
      setTick((t) => t + 1)
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : 'Erreur lors de la génération')
    } finally {
      setGenerating(false)
    }
  }

  const statusOptions = [
    { value: '', label: 'Tous les statuts' },
    { value: 'draft', label: 'Brouillon' },
    { value: 'outline_ready', label: 'Plan prêt' },
    { value: 'writing_requested', label: 'Rédaction demandée' },
    { value: 'writing_in_progress', label: 'En rédaction' },
    { value: 'draft_ready', label: 'Brouillon prêt' },
    { value: 'review_needed', label: 'Révision requise' },
    { value: 'correction_needed', label: 'Correction requise' },
    { value: 'ready_to_publish', label: 'Prêt à publier' },
    { value: 'scheduled', label: 'Programmé' },
    { value: 'published', label: 'Publié' },
    { value: 'update_recommended', label: 'Mise à jour conseillée' },
    { value: 'failed', label: 'Échec' },
  ]

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
    { value: 'critical', label: 'Warnings critiques' },
  ]

  const authors = getUniqueAuthors(articles)
  const authorOptions = [
    { value: '', label: 'Tous les auteurs' },
    ...authors.map((a) => ({ value: a, label: a })),
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
    if (filterScore === 'critical') return article.critical_warnings.length > 0
    return true
  }

  function matchesAuthorFilter(article: Article) {
    if (!filterAuthor) return true
    return article.author_name === filterAuthor
  }

  const visibleArticles = articles.filter((a) => matchesScoreFilter(a) && matchesAuthorFilter(a))

  return (
    <>
      <div className="project-page project-page--wide">
        {/* Header */}
        <div className="project-page-header">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Articles</h1>
            <p className="mt-0.5 text-[14px] text-secondary">
              Gérez l'ensemble de votre contenu éditorial.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              icon={<Sparkles size={14} />}
              size="sm"
              variant="secondary"
              onClick={() => { setGenerateOpen(true); setGenerateForm({}); setGenerateError(''); setGenerateResult(null) }}
            >
              Générer un article
            </Button>
            <Button icon={<Plus size={14} />} size="sm" onClick={() => setCreateOpen(true)}>
              Créer un article
            </Button>
          </div>
        </div>

        {/* Action error banner */}
        {actionError && (
          <div className="mb-4 flex items-center justify-between rounded-[10px] border border-danger/20 bg-danger/5 px-4 py-2.5 text-[14px] text-danger">
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
            options={statusOptions}
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="w-[185px]"
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
          {authors.length > 0 ? (
            <Select
              options={authorOptions}
              value={filterAuthor}
              onChange={(e) => setFilterAuthor(e.target.value)}
              className="w-[185px]"
            />
          ) : (
            <div className="flex h-10 w-[185px] cursor-not-allowed select-none items-center rounded-[12px] border border-border bg-surface/50 px-3.5 text-[14px] text-tertiary">
              Auteurs indisponibles
            </div>
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
          <ErrorState message="Impossible de charger les articles." onRetry={() => setTick((t) => t + 1)} />
        )}
        {status === 'success' && visibleArticles.length === 0 && (
          <EmptyState
            icon={<FileText size={22} />}
            title="Aucun article"
            description={filterStatus || filterCategory || debouncedSearch ? 'Aucun article ne correspond aux filtres sélectionnés.' : 'Créez votre premier article pour commencer.'}
            action={!filterStatus && !filterCategory && !debouncedSearch ? { label: 'Créer un article', onClick: () => setCreateOpen(true) } : undefined}
          />
        )}
        {status === 'success' && visibleArticles.length > 0 && (
          <>
            <TableRoot className="overflow-visible rounded-none border-0">
              <Table className="border-separate border-spacing-y-2">
                <TableHeader className="border-0">
                  <TableRow className="hover:bg-transparent">
                  <TableHead className="pr-8">Titre</TableHead>
                  <TableHead className="w-[40px] px-1 pl-4 text-center">Glob.</TableHead>
                  <TableHead className="w-[40px] px-1 text-center">SEO</TableHead>
                  <TableHead className="w-[40px] px-1 text-center">GEO</TableHead>
                  <TableHead className="w-[40px] px-1 text-center">Qual.</TableHead>
                  <TableHead className="w-[40px] px-1 text-center">Lisi.</TableHead>
                  <TableHead className="w-[40px] px-1 text-center">Orig.</TableHead>
                  <TableHead className="w-[40px] px-1 pr-4 text-center">EEAT</TableHead>
                  <TableHead className="w-[124px] px-5 text-center">Statut</TableHead>
                  <TableHead className="w-[206px] pl-5 text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleArticles.map((article) => (
                    <ArticleRow
                      key={article.id}
                      article={article}
                      categories={categories}
                      onEdit={(a) => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
                      onAction={handleAction}
                    />
                  ))}
                </TableBody>
              </Table>
            </TableRoot>
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

      {/* Unpublish confirm modal */}
      <Modal
        open={!!unpublishTarget}
        onClose={() => setUnpublishTarget(null)}
        title="Dépublier cet article ?"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 rounded-[12px] border border-warning/20 bg-warning/5 px-3.5 py-3">
            <EyeOff size={15} className="mt-0.5 shrink-0 text-warning" />
            <div>
              <p className="text-[14px] font-medium text-primary">{unpublishTarget?.title}</p>
              <p className="mt-0.5 text-[12px] text-secondary leading-snug">
                L'article sera retiré du site public et renvoyé en Production.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setUnpublishTarget(null)}>
              Annuler
            </Button>
            <Button size="sm" variant="danger" loading={unpublishing} className="flex-1 justify-center" onClick={handleUnpublishConfirm}>
              Dépublier
            </Button>
          </div>
        </div>
      </Modal>

      {/* Archive confirm modal */}
      <Modal
        open={!!archiveTarget}
        onClose={() => setArchiveTarget(null)}
        title="Archiver cet article ?"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 rounded-[12px] border border-danger/20 bg-danger/5 px-3.5 py-3">
            <Archive size={15} className="mt-0.5 shrink-0 text-danger" />
            <div>
              <p className="text-[14px] font-medium text-primary">{archiveTarget?.title}</p>
              <p className="mt-0.5 text-[12px] text-secondary leading-snug">
                L'article sera retiré du site public et déplacé dans les Archives.
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setArchiveTarget(null)}>
              Annuler
            </Button>
            <Button size="sm" variant="danger" loading={archiving} className="flex-1 justify-center" onClick={handleArchiveConfirm}>
              Archiver
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
              <p className="text-[14px] font-medium text-primary">{deleteTarget?.title}</p>
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

      {/* Create modal */}
      <Modal
        open={createOpen}
        onClose={() => { setCreateOpen(false); setCreateError('') }}
        title="Créer un article"
        size="sm"
      >
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          {createError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">
              {createError}
            </div>
          )}
          <Input
            label="Titre"
            value={createForm.title}
            onChange={(e) => setCreateForm((f) => ({ ...f, title: e.target.value }))}
            placeholder="Comment optimiser son SEO en 2025"
            required
            autoFocus
          />
          <Input
            label="Mot-clé principal"
            value={createForm.keyword}
            onChange={(e) => setCreateForm((f) => ({ ...f, keyword: e.target.value }))}
            placeholder="optimisation seo"
          />
          {categories.length > 0 && (
            <Select
              label="Catégorie"
              options={[{ value: '', label: 'Aucune catégorie' }, ...categories.map((c) => ({ value: c.id, label: c.name }))]}
              value={createForm.category_id}
              onChange={(e) => setCreateForm((f) => ({ ...f, category_id: e.target.value }))}
            />
          )}
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setCreateOpen(false)}>
              Annuler
            </Button>
            <Button type="submit" size="sm" loading={creating} className="flex-1 justify-center">
              Créer
            </Button>
          </div>
        </form>
      </Modal>

      {/* Generate article modal */}
      <Modal
        open={generateOpen}
        onClose={() => { setGenerateOpen(false); setGenerateForm({}); setGenerateError(''); setGenerateResult(null) }}
        title="Générer un article complet"
        size="md"
      >
        {generateResult ? (
          <div className="flex flex-col gap-4">
            <div className="flex items-start gap-3 rounded-[12px] border border-success/20 bg-success/8 px-3.5 py-3">
              <CheckCircle size={15} className="mt-0.5 shrink-0 text-success" />
              <div>
                <p className="text-[14px] font-medium text-primary">{generateResult.title}</p>
                <p className="mt-0.5 text-[12px] text-secondary">Article généré avec succès</p>
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => { setGenerateOpen(false); setGenerateResult(null); setGenerateForm({}) }}>
                Fermer
              </Button>
              <Button size="sm" className="flex-1 justify-center" onClick={() => { navigate(`/projects/${projectId}/articles/${generateResult.id}/edit`); setGenerateOpen(false) }}>
                Ouvrir dans l'éditeur
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleGenerate} className="flex flex-col gap-4">
            {generateError && (
              <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">
                {generateError}
              </div>
            )}
            <Input
              label="Titre souhaité"
              value={generateForm.preferred_title ?? ''}
              onChange={(e) => setGenerateForm((f) => ({ ...f, preferred_title: e.target.value || null }))}
              placeholder="Comment optimiser son SEO en 2025"
              hint="Laissez vide pour que l'IA propose un titre"
            />
            <Input
              label="Mot-clé principal"
              value={generateForm.keyword ?? ''}
              onChange={(e) => setGenerateForm((f) => ({ ...f, keyword: e.target.value || null }))}
              placeholder="optimisation seo"
            />
            {categories.length > 0 && (
              <Select
                label="Catégorie"
                options={[{ value: '', label: 'Aucune catégorie' }, ...categories.map((c) => ({ value: c.id, label: c.name }))]}
                value={generateForm.category_id ?? ''}
                onChange={(e) => setGenerateForm((f) => ({ ...f, category_id: e.target.value || null }))}
              />
            )}
            <Input
              label="Audience cible (optionnel)"
              value={generateForm.audience ?? ''}
              onChange={(e) => setGenerateForm((f) => ({ ...f, audience: e.target.value || null }))}
              placeholder="Développeurs web"
            />
            <Input
              label="Angle éditorial (optionnel)"
              value={generateForm.angle ?? ''}
              onChange={(e) => setGenerateForm((f) => ({ ...f, angle: e.target.value || null }))}
              placeholder="Guide pratique avec exemples"
            />
            <div className="flex flex-wrap items-center gap-4">
              <ToggleSwitch
                checked={generateForm.include_faq ?? false}
                onChange={(checked) => setGenerateForm((f) => ({ ...f, include_faq: checked }))}
                label="Inclure FAQ"
              />
              <ToggleSwitch
                checked={generateForm.include_callouts ?? false}
                onChange={(checked) => setGenerateForm((f) => ({ ...f, include_callouts: checked }))}
                label="Inclure callouts"
              />
            </div>
            <div className="flex gap-2 pt-1">
              <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => { setGenerateOpen(false); setGenerateForm({}); setGenerateError('') }}>
                Annuler
              </Button>
              <Button type="submit" size="sm" loading={generating} icon={generating ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />} className="flex-1 justify-center">
                Générer
              </Button>
            </div>
          </form>
        )}
      </Modal>
    </>
  )
}
