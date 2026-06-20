import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
  useDroppable,
} from '@dnd-kit/core'
import type { DragStartEvent, DragEndEvent, DragOverEvent } from '@dnd-kit/core'
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { CalendarClock, ExternalLink, FileText, Loader2, Plus, RefreshCw } from 'lucide-react'
import {
  listArticles, createArticle, publishArticle, unpublishArticle, markReadyArticle, archiveArticle,
  scheduleArticle, patchArticle,
} from '@/api/articles'
import { listCategories } from '@/api/categories'
import { listKanbanColumns, createKanbanColumn, deleteKanbanColumn } from '@/api/kanbanColumns'
import type { Article, ArticleStatus, Category } from '@/types'
import { formatDate } from '@/utils/format'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import StatusBadge from '@/components/ui/StatusBadge'

type ColumnDef = {
  status: string
  label: string
  color: string
  custom?: boolean
}

const COLUMNS: ColumnDef[] = [
  { status: 'writing_requested',   label: 'Rédaction dem.', color: '#007aff' },
  { status: 'writing_in_progress', label: 'En rédaction',   color: '#007aff' },
  { status: 'draft_ready',         label: 'Brouillons',     color: '#5856d6' },
  { status: 'review_needed',       label: 'À relire',       color: '#ff9500' },
  { status: 'correction_needed',   label: 'À corriger',     color: '#ff3b30' },
  { status: 'ready_to_publish',    label: 'Prêts',          color: '#34c759' },
  { status: 'scheduled',           label: 'Programmés',     color: '#5856d6' },
  { status: 'published',           label: 'Publiés',        color: '#34c759' },
  { status: 'failed',              label: 'Échecs',         color: '#ff3b30' },
  { status: 'archived',            label: 'Archivés',       color: '#8e8e93' },
]

const QUICK_ACTIONS: Partial<Record<ArticleStatus, { key: string; label: string }[]>> = {
  draft_ready:       [{ key: 'mark-ready', label: 'Marquer prêt' }],
  review_needed:     [{ key: 'mark-ready', label: 'Marquer prêt' }],
  correction_needed: [{ key: 'mark-ready', label: 'Marquer prêt' }],
  ready_to_publish:  [{ key: 'publish',    label: 'Publier' }],
  published:         [{ key: 'unpublish',  label: 'Dépublier' }],
  scheduled:         [{ key: 'publish',    label: 'Publier' }],
}

function scoreTone(value: number | null) {
  if (value === null) return 'bg-[#f0f0f2] text-tertiary'
  return value >= 70 ? 'bg-success/10 text-[#1a7a3a]' : value >= 40 ? 'bg-warning/10 text-[#c07000]' : 'bg-danger/10 text-danger'
}

function ScorePill({ label, value }: { label: string; value: number | null }) {
  return (
    <span className={`inline-flex min-w-0 flex-1 items-center justify-center whitespace-nowrap rounded-full px-1 py-0.5 text-[8px] font-medium ${scoreTone(value)}`}>
      {label} {value === null ? '—' : Math.round(value)}
    </span>
  )
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
}

function getWordCount(article: Article): number | null {
  if (article.word_count > 0) return article.word_count
  if (article.content?.trim()) {
    const words = stripHtml(article.content).split(/\s+/).filter(Boolean)
    return words.length > 0 ? words.length : null
  }
  return null
}

function formatWordCount(value: number): string {
  return `${value.toLocaleString('fr-FR')} mots`
}

function getUsefulDate(article: Article): { label: string; value: string } {
  if (article.published_at) return { label: 'Publié', value: article.published_at }
  if (article.scheduled_at) return { label: 'Planifié', value: article.scheduled_at }
  if (article.updated_at) return { label: 'Maj', value: article.updated_at }
  return { label: 'Créé', value: article.created_at }
}

function fallbackColumnLabel(status: string): string {
  return status
    .replace(/^custom_/, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function CardContent({
  article,
  categories,
  onEdit,
  onAction,
  isDragging = false,
}: {
  article: Article
  categories: Category[]
  onEdit: () => void
  onAction: (key: string, article: Article) => void
  isDragging?: boolean
}) {
  const quickActions = QUICK_ACTIONS[article.status] ?? []
  const category = categories.find((c) => c.id === article.category_id)
  const wordCount = getWordCount(article)
  const usefulDate = getUsefulDate(article)

  return (
    <div className={`rounded-[16px] bg-surface p-3 ${isDragging ? 'opacity-50' : 'hover:bg-white'} transition-colors`}>
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <p
          className="text-[12px] font-medium text-primary leading-snug cursor-pointer hover:text-accent transition-colors line-clamp-2 flex-1"
          onClick={onEdit}
        >
          {article.title}
        </p>
        <button
          onClick={onEdit}
          className="shrink-0 flex h-5 w-5 items-center justify-center rounded-[6px] text-tertiary hover:bg-[#e5e5e7] hover:text-primary transition-colors mt-0.5"
        >
          <ExternalLink size={10} />
        </button>
      </div>

      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-[10px] font-medium text-accent/80">
            {category?.name ?? 'Sans catégorie'}
          </p>
          {article.keyword && (
            <p className="mt-0.5 truncate text-[10px] text-tertiary">{article.keyword}</p>
          )}
        </div>
        <StatusBadge status={article.status} className="shrink-0" />
      </div>

      <div className="mb-2 flex items-center gap-1">
        <ScorePill label="SEO" value={article.seo_score} />
        <ScorePill label="Lis." value={article.readability_score} />
        <ScorePill label="Qual." value={article.quality_score} />
        <ScorePill label="EEAT" value={article.eeat_score} />
      </div>

      <div className="flex items-center justify-between gap-2 text-[10px] text-tertiary">
        {wordCount !== null ? (
          <span className="flex min-w-0 items-center gap-1">
            <FileText size={10} />
            {formatWordCount(wordCount)}
          </span>
        ) : (
          <span />
        )}
        <span className="flex shrink-0 items-center gap-1">
          <CalendarClock size={10} />
          {usefulDate.label} {formatDate(usefulDate.value)}
        </span>
      </div>

      {quickActions.length > 0 && (
        <div className="flex gap-1 mt-2 pt-2 border-t border-border">
          {quickActions.map((action) => (
            <button
              key={action.key}
              onClick={(e) => { e.stopPropagation(); onAction(action.key, article) }}
              className="flex-1 rounded-[8px] bg-[#f0f0f2] px-2 py-1 text-[10px] font-medium text-secondary hover:bg-accent hover:text-white transition-colors"
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function SortableCard({
  article,
  categories,
  onEdit,
  onAction,
}: {
  article: Article
  categories: Category[]
  onEdit: () => void
  onAction: (key: string, article: Article) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: article.id,
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    cursor: isDragging ? 'grabbing' : 'grab',
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
    >
      <CardContent article={article} categories={categories} onEdit={onEdit} onAction={onAction} isDragging={isDragging} />
    </div>
  )
}

function KanbanColumn({
  column,
  articles,
  categories,
  onEdit,
  onAction,
  onAddArticle,
  onRemoveColumn,
}: {
  column: ColumnDef
  articles: Article[]
  categories: Category[]
  onEdit: (a: Article) => void
  onAction: (key: string, a: Article) => void
  onAddArticle: (status: string) => void
  onRemoveColumn?: (status: string) => void
}) {
  const articleIds = articles.map((a) => a.id)
  const { setNodeRef, isOver } = useDroppable({ id: column.status })
  const columnBackground = `linear-gradient(180deg, ${column.color}1c 0%, ${column.color}0d 42%, rgba(255,255,255,0) 100%)`

  return (
    <div className="flex min-w-[220px] max-w-[220px] flex-col rounded-t-[16px] px-2 pb-2 pt-2" style={{ background: columnBackground }}>
      <div className="relative mb-3 flex items-center gap-2 rounded-t-[14px] px-1 py-2 shadow-[0_18px_26px_-26px_rgba(15,23,42,0.45)] after:absolute after:bottom-[-10px] after:left-0 after:right-0 after:h-3 after:bg-gradient-to-b after:from-black/[0.035] after:to-transparent after:content-['']">
        <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: column.color }} />
        <span className="text-[12px] font-semibold text-primary">{column.label}</span>
        {column.custom && onRemoveColumn && (
          <button
            onClick={() => onRemoveColumn(column.status)}
            className="ml-1 flex h-4 w-4 items-center justify-center rounded-[4px] text-tertiary hover:bg-danger/10 hover:text-danger transition-colors"
            title="Supprimer cette colonne"
          >
            ✕
          </button>
        )}
        <span className="text-[11px] text-tertiary bg-[#f0f0f2] rounded-full px-1.5 py-0.5">
          {articles.length}
        </span>
      </div>
      <SortableContext items={articleIds} strategy={verticalListSortingStrategy}>
        <div
          ref={setNodeRef}
          className={`flex min-h-[90px] flex-col gap-2 rounded-b-[14px] transition-colors ${isOver ? 'bg-accent/5' : ''}`}
        >
          {articles.length === 0 ? (
            <div className="flex items-center justify-center rounded-[12px] border border-dashed border-border h-20">
              <p className="text-[11px] text-tertiary">Vide</p>
            </div>
          ) : (
            articles.map((article) => (
              <SortableCard
                key={article.id}
                article={article}
                categories={categories}
                onEdit={() => onEdit(article)}
                onAction={onAction}
              />
            ))
          )}
          <button
            onClick={() => onAddArticle(column.status)}
            className="flex items-center justify-center gap-1 rounded-[12px] border border-dashed border-border py-2 text-[11px] text-tertiary hover:border-accent/40 hover:text-accent transition-colors"
          >
            <Plus size={12} /> Ajouter un article
          </button>
        </div>
      </SortableContext>
    </div>
  )
}

export default function KanbanPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [articles, setArticles] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [actionError, setActionError] = useState('')
  const [loadingAction, setLoadingAction] = useState(false)
  const [tick, setTick] = useState(0)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [customColumns, setCustomColumns] = useState<ColumnDef[]>([])
  const [customColumnIds, setCustomColumnIds] = useState<Map<string, string>>(new Map())
  const [columnModalOpen, setColumnModalOpen] = useState(false)
  const [newColumnName, setNewColumnName] = useState('')

  // Create article modal state
  const [createStatus, setCreateStatus] = useState('')
  const [createTitle, setCreateTitle] = useState('')
  const [createKeyword, setCreateKeyword] = useState('')
  const [createCategoryId, setCreateCategoryId] = useState('')
  const [creating, setCreating] = useState(false)

  // Schedule modal state
  const [scheduleTarget, setScheduleTarget] = useState<Article | null>(null)
  const [scheduleDate, setScheduleDate] = useState('')
  const [scheduling, setScheduling] = useState(false)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  )

  useEffect(() => {
    if (!projectId) return
    listCategories(projectId).then(setCategories).catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    listKanbanColumns(projectId).then((cols) => {
      if (cancelled) return
      const idMap = new Map<string, string>()
      const defs: ColumnDef[] = cols.map((c) => {
        idMap.set(c.status, c.id)
        return { status: c.status, label: c.label, color: c.color, custom: true }
      })
      setCustomColumns(defs)
      setCustomColumnIds(idMap)
    }).catch(() => {})
    return () => { cancelled = true }
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    listArticles(projectId, { limit: 500 })
      .then((data) => { if (!cancelled) { setArticles(data); setLoadStatus('success') } })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, tick])

  async function handleAction(key: string, article: Article) {
    if (!projectId) return
    if (key === 'schedule') {
      setScheduleTarget(article)
      setScheduleDate('')
      return
    }
    setLoadingAction(true)
    setActionError('')
    try {
      let updated: Article | undefined
      if (key === 'publish') updated = await publishArticle(projectId, article.id)
      else if (key === 'unpublish') updated = await unpublishArticle(projectId, article.id)
      else if (key === 'mark-ready') updated = await markReadyArticle(projectId, article.id)
      else if (key === 'archive') updated = await archiveArticle(projectId, article.id)
      if (updated) {
        setArticles((prev) => prev.map((a) => a.id === updated!.id ? updated! : a))
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Erreur lors de l'action.")
    } finally {
      setLoadingAction(false)
    }
  }

  async function handleScheduleConfirm() {
    if (!projectId || !scheduleTarget || !scheduleDate) return
    setScheduling(true)
    try {
      const updated = await scheduleArticle(projectId, scheduleTarget.id, new Date(scheduleDate).toISOString())
      setArticles((prev) => prev.map((a) => a.id === updated.id ? updated : a))
      setScheduleTarget(null)
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Erreur lors de la programmation.')
    } finally {
      setScheduling(false)
    }
  }

  function handleCreateColumn(event: React.FormEvent) {
    event.preventDefault()
    if (!projectId) return
    const label = newColumnName.trim()
    if (!label) return
    createKanbanColumn(projectId, { label }).then((col) => {
      setCustomColumnIds((prev) => { const m = new Map(prev); m.set(col.status, col.id); return m })
      setCustomColumns((prev) => [...prev, {
        status: col.status,
        label: col.label,
        color: col.color,
        custom: true,
      }])
    }).catch((err) => {
      setActionError(err instanceof Error ? err.message : "Erreur lors de la création de la colonne.")
    })
    setNewColumnName('')
    setColumnModalOpen(false)
  }

  async function handleRemoveColumn(status: string) {
    if (!projectId) return
    const colId = customColumnIds.get(status)
    if (!colId) return
    setCustomColumns((prev) => prev.filter((c) => c.status !== status))
    setCustomColumnIds((prev) => { const m = new Map(prev); m.delete(status); return m })
    try {
      await deleteKanbanColumn(colId)
    } catch {
      // Revert on error
      listKanbanColumns(projectId).then((cols) => {
        const idMap = new Map<string, string>()
        const defs: ColumnDef[] = cols.map((c) => {
          idMap.set(c.status, c.id)
          return { status: c.status, label: c.label, color: c.color, custom: true }
        })
        setCustomColumns(defs)
        setCustomColumnIds(idMap)
      })
    }
  }

  function handleAddArticle(status: string) {
    setCreateStatus(status)
    setCreateTitle('')
    setCreateKeyword('')
    setCreateCategoryId('')
  }

  async function handleCreateArticle(event: React.FormEvent) {
    event.preventDefault()
    if (!projectId || !createTitle.trim()) return
    setCreating(true)
    try {
      const created = await createArticle(projectId, {
        title: createTitle.trim(),
        keyword: createKeyword.trim() || undefined,
        category_id: createCategoryId || undefined,
        status: createStatus,
      })
      setArticles((prev) => [...prev, created])
      setCreateStatus('')
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Erreur lors de la création.")
    } finally {
      setCreating(false)
    }
  }

  const activeArticle = activeId ? articles.find((a) => a.id === activeId) : null

  function handleDragStart(event: DragStartEvent) {
    setActiveId(event.active.id as string)
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  function handleDragOver(_e: DragOverEvent) { /* handled by useDroppable */ }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveId(null)
    if (!over || !projectId) return

    const overId = String(over.id)
    // over.id is either a column status (droppable) or an article id (sortable)
    let newStatus: string | undefined
    const matchedColumn = allColumns.find((c) => c.status === overId)
    if (matchedColumn) {
      newStatus = matchedColumn.status
    } else {
      const targetArticle = articles.find((a) => a.id === overId)
      if (targetArticle) newStatus = targetArticle.status
    }

    if (!newStatus) return

    const article = articles.find((a) => a.id === active.id)
    if (!article || article.status === newStatus) return

    // Optimistically update UI
    const prevStatus = article.status
    setArticles((prev) => prev.map((a) => a.id === article.id ? { ...a, status: newStatus! as ArticleStatus } : a))

    // Persist to backend — revert on error
    patchArticle(projectId, article.id, { status: newStatus }).catch(() => {
      setArticles((prev) => prev.map((a) => a.id === article.id ? { ...a, status: prevStatus } : a))
    })
  }

  const knownStatuses = new Set([...COLUMNS, ...customColumns].map((column) => column.status))
  const unknownColumns: ColumnDef[] = Array.from(new Set(
    articles
      .map((article) => article.status)
      .filter((status) => !knownStatuses.has(status))
  )).map((status) => ({
    status,
    label: fallbackColumnLabel(status),
    color: '#8e8e93',
    custom: true,
  }))
  const allColumns = [...COLUMNS, ...customColumns, ...unknownColumns]

  const articlesByStatus = (status: string) =>
    articles
      .filter((a) => a.status === status)
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at))

  if (loadStatus === 'loading') return <LoadingState />
  if (loadStatus === 'error') return <ErrorState onRetry={() => setTick((t) => t + 1)} />

  return (
    <>
      <div className="flex min-h-full flex-col p-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 shrink-0">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Production éditoriale</h1>
            <p className="mt-0.5 text-[13px] text-secondary">
              Suivi de la production éditoriale — {articles.length} article{articles.length !== 1 ? 's' : ''} dans le workflow
            </p>
          </div>
          <div className="flex items-center gap-2">
            {loadingAction && <Loader2 size={14} className="animate-spin text-tertiary" />}
            <Button size="sm" variant="secondary" icon={<Plus size={13} />} onClick={() => setColumnModalOpen(true)}>
              Ajouter colonne
            </Button>
            <Button size="sm" variant="secondary" icon={<RefreshCw size={13} />} onClick={() => setTick((t) => t + 1)}>
              Rafraîchir
            </Button>
          </div>
        </div>

        {actionError && (
          <div className="mb-3 shrink-0 rounded-[10px] border border-danger/20 bg-danger/5 px-4 py-2.5 text-[13px] text-danger flex items-center justify-between">
            <span>{actionError}</span>
            <button onClick={() => setActionError('')} className="ml-3 text-danger/60 hover:text-danger">✕</button>
          </div>
        )}

        {/* Kanban board with DnD */}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 overflow-x-auto pb-4">
            {allColumns.map((col) => (
              <KanbanColumn
                key={col.status}
                column={col}
                articles={articlesByStatus(col.status)}
                categories={categories}
                onEdit={(a) => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
                onAction={handleAction}
                onAddArticle={handleAddArticle}
                onRemoveColumn={col.custom ? handleRemoveColumn : undefined}
              />
            ))}
          </div>

          <DragOverlay>
            {activeArticle && (
              <div className="w-[220px] rotate-1 opacity-90">
                <CardContent
                  article={activeArticle}
                  categories={categories}
                  onEdit={() => {}}
                  onAction={() => {}}
                />
              </div>
            )}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Custom column modal */}
      <Modal
        open={columnModalOpen}
        onClose={() => { setColumnModalOpen(false); setNewColumnName('') }}
        title="Ajouter une colonne"
        size="sm"
      >
        <form onSubmit={handleCreateColumn} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Nom de la colonne</label>
            <input
              value={newColumnName}
              onChange={(event) => setNewColumnName(event.target.value)}
              placeholder="Ex. À valider client"
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[13px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
              autoFocus
            />
            <p className="text-[11px] leading-snug text-tertiary">
              La colonne est partagée avec toute l'équipe du projet. Les cartes déplacées dans cette colonne sont enregistrées avec ce statut.
            </p>
          </div>
          <div className="flex gap-2 pt-1">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="flex-1 justify-center"
              onClick={() => { setColumnModalOpen(false); setNewColumnName('') }}
            >
              Annuler
            </Button>
            <Button type="submit" size="sm" className="flex-1 justify-center" disabled={!newColumnName.trim()}>
              Ajouter
            </Button>
          </div>
        </form>
      </Modal>

      {/* Create article modal */}
      <Modal
        open={!!createStatus}
        onClose={() => setCreateStatus('')}
        title="Ajouter un article"
        size="sm"
      >
        <form onSubmit={handleCreateArticle} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Titre *</label>
            <input
              value={createTitle}
              onChange={(e) => setCreateTitle(e.target.value)}
              placeholder="Titre de l'article"
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[13px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Mot-clé</label>
            <input
              value={createKeyword}
              onChange={(e) => setCreateKeyword(e.target.value)}
              placeholder="Mot-clé principal (optionnel)"
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[13px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Catégorie</label>
            <select
              value={createCategoryId}
              onChange={(e) => setCreateCategoryId(e.target.value)}
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[13px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
            >
              <option value="">Sans catégorie</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setCreateStatus('')}>
              Annuler
            </Button>
            <Button type="submit" size="sm" loading={creating} className="flex-1 justify-center" disabled={!createTitle.trim()}>
              Créer
            </Button>
          </div>
        </form>
      </Modal>

      {/* Schedule modal */}
      <Modal
        open={!!scheduleTarget}
        onClose={() => { setScheduleTarget(null); setScheduleDate('') }}
        title="Programmer la publication"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <p className="text-[13px] text-secondary truncate">{scheduleTarget?.title}</p>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Date et heure de publication</label>
            <input
              type="datetime-local"
              value={scheduleDate}
              onChange={(e) => setScheduleDate(e.target.value)}
              className="w-full rounded-[10px] border border-border bg-white px-3 py-2 text-[13px] text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent/20"
            />
          </div>
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setScheduleTarget(null)}>
              Annuler
            </Button>
            <Button size="sm" loading={scheduling} className="flex-1 justify-center" onClick={handleScheduleConfirm}>
              Programmer
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}
