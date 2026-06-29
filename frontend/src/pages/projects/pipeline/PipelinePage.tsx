import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import {
  Plus,
  RefreshCw,
  Search,
  Star,
  CheckCircle,
  XCircle,
  ExternalLink,
  Sparkles,
  Send,
  Calendar,
  AlertTriangle,
} from '@/components/ui/hugeIcons'
import { listArticles, bulkValidateByScore, bulkValidateArticles, bulkPublishArticles, patchArticle } from '@/api/articles'
import type { BulkValidateResponse } from '@/api/articles'
import {
  generateIdea,
  autoGenerateIdeas,
  sendToProduction,
  rejectIdea,
  setIdeaPriority,
} from '@/api/ideas'
import { listCategories } from '@/api/categories'
import type { Article, Category } from '@/types'
import { formatDate } from '@/utils/format'
import { finiteScore } from '@/lib/scoreBadge'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import ScoreBadge from '@/components/ui/ScoreBadge'
import StatusBadge from '@/components/ui/StatusBadge'
import { Skeleton } from '@/components/ui/Skeleton'

// ── Constants ──────────────────────────────────────────────────────────────

const IDEAS_STATUSES = ['idea_proposed', 'idea_priority', 'idea_rejected']
const WRITING_STATUSES = ['writing_requested', 'writing_in_progress', 'outline_ready']
const VALIDATE_STATUSES = ['draft_ready', 'ready_to_publish', 'review_needed', 'correction_needed']

const STATUS_OPTIONS = [
  { value: '', label: 'Tous les statuts' },
  { value: 'idea_proposed', label: 'Proposée' },
  { value: 'idea_priority', label: 'Prioritaire' },
  { value: 'idea_rejected', label: 'Rejetée' },
]

const SCORE_OPTIONS = [
  { value: '', label: 'Tous les scores' },
  { value: '70', label: '≥ 70' },
  { value: '50', label: '≥ 50' },
]

const VALIDATE_FILTER_OPTIONS = [
  { value: 'all', label: 'Tous' },
  { value: 'ready', label: 'Prêts' },
  { value: 'high_score', label: 'Score ≥ 90' },
  { value: 'warnings', label: 'Warnings critiques' },
  { value: 'no_date', label: 'Sans date planifiée' },
]

const SCORE_THRESHOLD_OPTIONS = [
  { value: '90', label: 'Score ≥ 90' },
  { value: '85', label: 'Score ≥ 85' },
  { value: '80', label: 'Score ≥ 80' },
  { value: '75', label: 'Score ≥ 75' },
]

// ── Tab button ──────────────────────────────────────────────────────────────

function TabButton({
  active,
  onClick,
  count,
  children,
}: {
  active: boolean
  onClick: () => void
  count: number
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative px-4 py-2.5 text-[13px] font-medium transition-colors ${
        active
          ? 'border-b-2 border-accent text-accent'
          : 'text-secondary hover:text-primary'
      }`}
    >
      {children}
      {count > 0 && (
        <span
          className={`ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[11px] font-semibold ${
            active ? 'bg-accent/10 text-accent' : 'bg-surface-soft text-tertiary'
          }`}
        >
          {count}
        </span>
      )}
    </button>
  )
}

// ── Writing step badge ───────────────────────────────────────────────────────

function StepBadge({ status }: { status: string }) {
  if (status === 'writing_in_progress') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-purple-100 px-2.5 py-1 text-[11px] font-medium text-purple-700">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-purple-500" />
        En cours…
      </span>
    )
  }
  if (status === 'outline_ready') {
    return (
      <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-1 text-[11px] font-medium text-blue-700">
        Plan prêt
      </span>
    )
  }
  return (
    <span className="inline-flex items-center rounded-full bg-surface-soft px-2.5 py-1 text-[11px] font-medium text-secondary">
      En attente
    </span>
  )
}

// ── Ideas Tab ────────────────────────────────────────────────────────────────

function IdeasTab({ projectId, categories }: { projectId: string; categories: Category[] }) {
  const navigate = useNavigate()
  const [articles, setArticles] = useState<Article[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)
  const [search, setSearch] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [scoreFilter, setScoreFilter] = useState('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [rejectTarget, setRejectTarget] = useState<Article | null>(null)
  const [rejectNote, setRejectNote] = useState('')
  const [generateOpen, setGenerateOpen] = useState(false)
  const [bulkGenerateOpen, setBulkGenerateOpen] = useState(false)
  const [generateTitle, setGenerateTitle] = useState('')
  const [generateContext, setGenerateContext] = useState('')
  const [bulkCount, setBulkCount] = useState(3)
  const [generating, setGenerating] = useState(false)
  const [generateResult, setGenerateResult] = useState('')

  const load = useCallback(() => {
    setLoadStatus('loading')
    Promise.all(IDEAS_STATUSES.map((s) => listArticles(projectId, { status: s, limit: 500 })))
      .then((groups) => {
        setArticles(groups.flat().sort((a, b) => b.updated_at.localeCompare(a.updated_at)))
        setLoadStatus('success')
      })
      .catch(() => setLoadStatus('error'))
  }, [projectId])

  useEffect(() => { load() }, [load, tick])

  const visible = useMemo(() => {
    let rows = articles
    if (search) rows = rows.filter((a) => a.title?.toLowerCase().includes(search.toLowerCase()) || a.keyword?.toLowerCase().includes(search.toLowerCase()))
    if (categoryFilter) rows = rows.filter((a) => a.category_id === categoryFilter)
    if (statusFilter) rows = rows.filter((a) => a.status === statusFilter)
    if (scoreFilter) {
      const min = Number(scoreFilter)
      rows = rows.filter((a) => (finiteScore(a.global_score) ?? 0) >= min)
    }
    return rows
  }, [articles, search, categoryFilter, statusFilter, scoreFilter])

  function toggle(id: string, checked: boolean) {
    setSelectedIds((prev) => { const s = new Set(prev); checked ? s.add(id) : s.delete(id); return s })
  }

  function toggleAll(checked: boolean) {
    setSelectedIds(checked ? new Set(visible.map((a) => a.id)) : new Set())
  }

  const selected = visible.filter((a) => selectedIds.has(a.id))

  async function handlePrioritize(article: Article) {
    setActionLoading(article.id + '-prioritize')
    setError('')
    try {
      await setIdeaPriority(article.id, article.status === 'idea_priority' ? 0 : 1)
      setTick((t) => t + 1)
    } catch { setError('Impossible de prioriser.') }
    finally { setActionLoading(null) }
  }

  async function handleSendToProduction(article: Article) {
    setActionLoading(article.id + '-send')
    setError('')
    try {
      await sendToProduction(article.id)
      setTick((t) => t + 1)
    } catch { setError('Impossible de valider cette idée.') }
    finally { setActionLoading(null) }
  }

  async function handleReject() {
    if (!rejectTarget) return
    setActionLoading(rejectTarget.id + '-reject')
    setError('')
    try {
      await rejectIdea(rejectTarget.id, { rejection_note: rejectNote || undefined })
      setRejectTarget(null)
      setRejectNote('')
      setTick((t) => t + 1)
    } catch { setError('Impossible de rejeter.') }
    finally { setActionLoading(null) }
  }

  async function handleBulkSend() {
    setActionLoading('bulk-send')
    setError('')
    try {
      await Promise.all(selected.map((a) => sendToProduction(a.id)))
      setSelectedIds(new Set())
      setTick((t) => t + 1)
    } catch { setError('Impossible de valider la sélection.') }
    finally { setActionLoading(null) }
  }

  async function handleBulkPrioritize() {
    setActionLoading('bulk-prio')
    setError('')
    try {
      await Promise.all(selected.map((a) => setIdeaPriority(a.id, 1)))
      setSelectedIds(new Set())
      setTick((t) => t + 1)
    } catch { setError('Impossible de prioriser la sélection.') }
    finally { setActionLoading(null) }
  }

  async function handleBulkReject() {
    setActionLoading('bulk-reject')
    setError('')
    try {
      await Promise.all(selected.map((a) => rejectIdea(a.id)))
      setSelectedIds(new Set())
      setTick((t) => t + 1)
    } catch { setError('Impossible de rejeter la sélection.') }
    finally { setActionLoading(null) }
  }

  async function handleGenerate() {
    setGenerating(true)
    setGenerateResult('')
    setError('')
    try {
      const res = await generateIdea(projectId, {
        preferred_title: generateTitle || undefined,
        context_hint: generateContext || undefined,
      })
      setGenerateResult(`"${res.title}" créée.`)
      setGenerateTitle('')
      setGenerateContext('')
      setTick((t) => t + 1)
    } catch { setGenerateResult('Erreur lors de la génération.') }
    finally { setGenerating(false) }
  }

  async function handleBulkGenerate() {
    setGenerating(true)
    setGenerateResult('')
    setError('')
    try {
      const res = await autoGenerateIdeas(projectId, bulkCount)
      setGenerateResult(`${res.generated} idée(s) créée(s).`)
      setTick((t) => t + 1)
    } catch { setGenerateResult('Erreur lors de la génération en masse.') }
    finally { setGenerating(false) }
  }

  const categoryOptions = [
    { value: '', label: 'Toutes les catégories' },
    ...categories.map((c) => ({ value: c.id, label: c.name })),
  ]

  if (loadStatus === 'loading') return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 rounded-[10px]" />)}
    </div>
  )

  if (loadStatus === 'error') return <ErrorState message="Impossible de charger les idées." onRetry={() => setTick((t) => t + 1)} />

  return (
    <>
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-tertiary" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher…"
              className="h-8 rounded-[10px] border border-border bg-surface pl-8 pr-3 text-[13px] text-primary placeholder:text-tertiary focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>
          <Select options={categoryOptions} value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="w-44" />
          <Select options={STATUS_OPTIONS} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-44" />
          <Select options={SCORE_OPTIONS} value={scoreFilter} onChange={(e) => setScoreFilter(e.target.value)} className="w-36" />
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" icon={<Sparkles size={13} />} onClick={() => setBulkGenerateOpen(true)}>
            Générer en masse
          </Button>
          <Button size="sm" icon={<Plus size={13} />} onClick={() => setGenerateOpen(true)}>
            Nouvelle idée
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-3 rounded-[10px] border border-danger/20 bg-danger/5 px-3 py-2 text-[13px] text-danger">{error}</div>
      )}

      {/* Batch bar */}
      {selected.length > 0 && (
        <div className="mb-3 flex items-center gap-2 rounded-[10px] border border-border bg-surface-soft px-3 py-2">
          <span className="text-[12px] font-medium text-secondary">{selected.length} sélectionné(s)</span>
          <div className="flex-1" />
          <Button size="sm" variant="secondary" loading={actionLoading === 'bulk-prio'} onClick={handleBulkPrioritize}>
            Prioriser ({selected.length})
          </Button>
          <Button size="sm" loading={actionLoading === 'bulk-send'} onClick={handleBulkSend}>
            Valider ({selected.length})
          </Button>
          <Button size="sm" variant="danger" loading={actionLoading === 'bulk-reject'} onClick={handleBulkReject}>
            Rejeter ({selected.length})
          </Button>
        </div>
      )}

      {visible.length === 0 ? (
        <EmptyState
          icon={<Sparkles size={20} />}
          title="Aucune idée"
          description="Générez des idées pour commencer."
          action={{ label: 'Nouvelle idée', onClick: () => setGenerateOpen(true) }}
        />
      ) : (
        <>
          {/* Header row */}
          <div className="mb-1 hidden grid-cols-[20px_56px_minmax(0,1fr)_140px_140px_100px_80px_130px] gap-3 px-3 text-[11px] font-medium uppercase tracking-wide text-tertiary lg:grid">
            <label><input type="checkbox" checked={selected.length > 0 && selected.length === visible.length} onChange={(e) => toggleAll(e.target.checked)} /></label>
            <div>Score</div>
            <div>Titre / Angle</div>
            <div>Catégorie</div>
            <div>Mot-clé</div>
            <div>Statut</div>
            <div>Date</div>
            <div className="text-right">Actions</div>
          </div>

          <div className="flex flex-col">
            {visible.map((article) => {
              const catName = categories.find((c) => c.id === article.category_id)?.name ?? '—'
              const score = finiteScore(article.global_score)
              return (
                <div
                  key={article.id}
                  className="group grid grid-cols-[20px_56px_minmax(0,1fr)_140px_140px_100px_80px_130px] items-center gap-3 border-b border-[#f0f0f0] px-3 py-2.5 transition-colors hover:bg-[#fafafa]"
                >
                  <input type="checkbox" checked={selectedIds.has(article.id)} onChange={(e) => toggle(article.id, e.target.checked)} />
                  <ScoreBadge label="Score" value={score} valid={article.global_score_valid} />
                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-medium text-primary">{article.title || '(sans titre)'}</p>
                    {article.meta_description && (
                      <p className="mt-0.5 truncate text-[11px] text-tertiary">{article.meta_description}</p>
                    )}
                  </div>
                  <span className="truncate text-[12px] text-secondary">{catName}</span>
                  <span className="truncate text-[12px] text-secondary">{article.keyword ?? '—'}</span>
                  <StatusBadge status={article.status} />
                  <span className="text-[12px] text-tertiary">{article.created_at ? formatDate(article.created_at) : '—'}</span>
                  <div className="flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    {article.status !== 'idea_rejected' && (
                      <button
                        type="button"
                        title={article.status === 'idea_priority' ? 'Retirer priorité' : 'Prioriser'}
                        onClick={() => handlePrioritize(article)}
                        disabled={actionLoading === article.id + '-prioritize'}
                        className={`flex h-7 w-7 items-center justify-center rounded-[8px] transition-colors hover:bg-surface-soft ${article.status === 'idea_priority' ? 'text-orange-500' : 'text-tertiary'}`}
                      >
                        <Star size={14} />
                      </button>
                    )}
                    {article.status !== 'idea_rejected' && (
                      <button
                        type="button"
                        title="Valider → production"
                        onClick={() => handleSendToProduction(article)}
                        disabled={actionLoading === article.id + '-send'}
                        className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary transition-colors hover:bg-accent/10 hover:text-accent"
                      >
                        <CheckCircle size={14} />
                      </button>
                    )}
                    <button
                      type="button"
                      title="Rejeter"
                      onClick={() => setRejectTarget(article)}
                      className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary transition-colors hover:bg-danger/10 hover:text-danger"
                    >
                      <XCircle size={14} />
                    </button>
                    <button
                      type="button"
                      title="Ouvrir dans l'éditeur"
                      onClick={() => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}
                      className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary transition-colors hover:bg-surface-soft hover:text-primary"
                    >
                      <ExternalLink size={14} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* Reject modal */}
      <Modal open={rejectTarget !== null} onClose={() => { setRejectTarget(null); setRejectNote('') }} title="Rejeter l'idée" size="sm">
        <div className="flex flex-col gap-3">
          <p className="text-[13px] text-secondary">Idée : <strong>{rejectTarget?.title}</strong></p>
          <Input
            label="Note (optionnelle)"
            value={rejectNote}
            onChange={(e) => setRejectNote(e.target.value)}
            placeholder="Raison du rejet…"
          />
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" className="flex-1 justify-center" onClick={() => setRejectTarget(null)}>Annuler</Button>
            <Button size="sm" variant="danger" className="flex-1 justify-center" loading={actionLoading?.includes('-reject')} onClick={handleReject}>Rejeter</Button>
          </div>
        </div>
      </Modal>

      {/* Generate idea modal */}
      <Modal open={generateOpen} onClose={() => { setGenerateOpen(false); setGenerateResult('') }} title="Nouvelle idée" size="sm">
        <div className="flex flex-col gap-3">
          <Input label="Titre suggéré (optionnel)" value={generateTitle} onChange={(e) => setGenerateTitle(e.target.value)} placeholder="ex. Comment choisir un hébergeur…" />
          <Input label="Contexte (optionnel)" value={generateContext} onChange={(e) => setGenerateContext(e.target.value)} placeholder="ex. Article pour débutants, angle SEO…" />
          {generateResult && <p className="rounded-[10px] bg-surface-soft px-3 py-2 text-[13px] text-secondary">{generateResult}</p>}
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" className="flex-1 justify-center" onClick={() => setGenerateOpen(false)}>Fermer</Button>
            <Button size="sm" className="flex-1 justify-center" loading={generating} onClick={handleGenerate}>Générer</Button>
          </div>
        </div>
      </Modal>

      {/* Bulk generate modal */}
      <Modal open={bulkGenerateOpen} onClose={() => { setBulkGenerateOpen(false); setGenerateResult('') }} title="Générer en masse" size="sm">
        <div className="flex flex-col gap-3">
          <div>
            <label className="mb-1 block text-[12px] font-medium text-secondary">Nombre d'idées</label>
            <select
              value={bulkCount}
              onChange={(e) => setBulkCount(Number(e.target.value))}
              className="w-full rounded-[10px] border border-border bg-surface px-3 py-2 text-[13px] text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
            >
              {[3, 5, 10, 20].map((n) => <option key={n} value={n}>{n} idées</option>)}
            </select>
          </div>
          {generateResult && <p className="rounded-[10px] bg-surface-soft px-3 py-2 text-[13px] text-secondary">{generateResult}</p>}
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" className="flex-1 justify-center" onClick={() => setBulkGenerateOpen(false)}>Fermer</Button>
            <Button size="sm" className="flex-1 justify-center" loading={generating} onClick={handleBulkGenerate}>Générer {bulkCount} idées</Button>
          </div>
        </div>
      </Modal>
    </>
  )
}

// ── Writing Tab ──────────────────────────────────────────────────────────────

function WritingTab({ projectId }: { projectId: string }) {
  const navigate = useNavigate()
  const [articles, setArticles] = useState<Article[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)

  useEffect(() => {
    setLoadStatus('loading')
    Promise.all(WRITING_STATUSES.map((s) => listArticles(projectId, { status: s, limit: 200 })))
      .then((groups) => {
        setArticles(groups.flat().sort((a, b) => b.updated_at.localeCompare(a.updated_at)))
        setLoadStatus('success')
      })
      .catch(() => setLoadStatus('error'))
  }, [projectId, tick])

  if (loadStatus === 'loading') return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-12 rounded-[10px]" />)}
    </div>
  )

  if (loadStatus === 'error') return <ErrorState message="Impossible de charger les articles en rédaction." onRetry={() => setTick((t) => t + 1)} />

  if (articles.length === 0) return (
    <EmptyState
      icon={<RefreshCw size={20} />}
      title="Aucun article en cours de rédaction"
      description="Validez des idées pour lancer la génération."
    />
  )

  return (
    <>
      <div className="mb-1 hidden grid-cols-[minmax(0,1fr)_180px_140px_120px_40px] gap-3 px-3 text-[11px] font-medium uppercase tracking-wide text-tertiary lg:grid">
        <div>Titre</div>
        <div>Catégorie</div>
        <div>Étape</div>
        <div>Mis à jour</div>
        <div />
      </div>
      <div className="flex flex-col">
        {articles.map((article) => (
          <div
            key={article.id}
            className="group grid grid-cols-[minmax(0,1fr)_180px_140px_120px_40px] items-center gap-3 border-b border-[#f0f0f0] px-3 py-3 transition-colors hover:bg-[#fafafa]"
          >
            <p className="truncate text-[13px] font-medium text-primary">{article.title || '(sans titre)'}</p>
            <span className="truncate text-[12px] text-secondary">{article.category_id || '—'}</span>
            <StepBadge status={article.status} />
            <span className="text-[12px] text-tertiary">{formatDate(article.updated_at)}</span>
            <button
              type="button"
              title="Ouvrir"
              onClick={() => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}
              className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary opacity-0 transition-opacity hover:bg-surface-soft hover:text-primary group-hover:opacity-100"
            >
              <ExternalLink size={14} />
            </button>
          </div>
        ))}
      </div>
    </>
  )
}

// ── Validate Tab ─────────────────────────────────────────────────────────────

type ValidateFilter = 'all' | 'ready' | 'high_score' | 'warnings' | 'no_date'

function ValidateTab({ projectId, categories }: { projectId: string; categories: Category[] }) {
  const navigate = useNavigate()
  const [articles, setArticles] = useState<Article[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)
  const [filter, setFilter] = useState<ValidateFilter>('all')
  const [scoreThreshold, setScoreThreshold] = useState(85)
  const [confirmMode, setConfirmMode] = useState<'publish' | 'schedule' | 'bulk-score' | null>(null)
  const [targetId, setTargetId] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [bulkResult, setBulkResult] = useState<BulkValidateResponse | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setLoadStatus('loading')
    Promise.all(VALIDATE_STATUSES.map((s) => listArticles(projectId, { status: s, limit: 500 })))
      .then((groups) => {
        setArticles(groups.flat().sort((a, b) => b.updated_at.localeCompare(a.updated_at)))
        setLoadStatus('success')
      })
      .catch(() => setLoadStatus('error'))
  }, [projectId])

  useEffect(() => { load() }, [load, tick])

  const visible = useMemo(() => {
    switch (filter) {
      case 'ready': return articles.filter((a) => a.is_validable && a.scheduled_at)
      case 'high_score': return articles.filter((a) => (finiteScore(a.global_score) ?? 0) >= 90)
      case 'warnings': return articles.filter((a) => a.critical_warnings.length > 0)
      case 'no_date': return articles.filter((a) => !a.scheduled_at)
      default: return articles
    }
  }, [articles, filter])

  const eligibleCount = useMemo(
    () => articles.filter((a) => (finiteScore(a.global_score) ?? 0) >= scoreThreshold).length,
    [articles, scoreThreshold],
  )

  async function handleBulkValidateByScore() {
    setRunning(true)
    setError('')
    setBulkResult(null)
    try {
      const res = await bulkValidateByScore(projectId, scoreThreshold, ['draft_ready', 'ready_to_publish'])
      setBulkResult(res)
      setTick((t) => t + 1)
    } catch { setError("Impossible d'exécuter la validation par score.") }
    finally { setRunning(false) }
  }

  async function handleConfirm() {
    if (!targetId || !confirmMode) return
    setRunning(true)
    setError('')
    setBulkResult(null)
    try {
      if (confirmMode === 'publish') {
        const res = await bulkPublishArticles(projectId, [targetId])
        setBulkResult(res)
      } else if (confirmMode === 'schedule') {
        const res = await bulkValidateArticles(projectId, [targetId])
        setBulkResult(res)
      }
      setTick((t) => t + 1)
    } catch { setError('Action impossible.'); setConfirmMode(null) }
    finally { setRunning(false) }
  }

  async function handleMarkCorrection(articleId: string) {
    try {
      await patchArticle(projectId, articleId, { status: 'correction_needed' })
      setTick((t) => t + 1)
    } catch { setError('Impossible de marquer en correction.') }
  }

  const catName = (article: Article) => categories.find((c) => c.id === article.category_id)?.name ?? '—'

  if (loadStatus === 'loading') return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14 rounded-[10px]" />)}
    </div>
  )

  if (loadStatus === 'error') return <ErrorState message="Impossible de charger les articles." onRetry={() => setTick((t) => t + 1)} />

  return (
    <>
      {/* Bulk validate by score header */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <select
            value={scoreThreshold}
            onChange={(e) => setScoreThreshold(Number(e.target.value))}
            className="rounded-[10px] border border-border bg-surface px-3 py-1.5 text-[13px] text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            {SCORE_THRESHOLD_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <Button
            size="sm"
            icon={<CheckCircle size={13} />}
            loading={running}
            onClick={handleBulkValidateByScore}
            disabled={eligibleCount === 0}
          >
            Valider tout ce qui dépasse ce score ({eligibleCount})
          </Button>
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as ValidateFilter)}
          className="rounded-[10px] border border-border bg-surface px-3 py-1.5 text-[13px] text-primary focus:outline-none focus:ring-2 focus:ring-accent/30"
        >
          {VALIDATE_FILTER_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {error && <div className="mb-3 rounded-[10px] border border-danger/20 bg-danger/5 px-3 py-2 text-[13px] text-danger">{error}</div>}

      {bulkResult && !confirmMode && (
        <div className="mb-3 rounded-[10px] bg-surface-soft px-3 py-2 text-[13px] text-secondary">
          {bulkResult.validated_count ?? bulkResult.scheduled_count} traité(s), {bulkResult.blocked_count} bloqué(s).
        </div>
      )}

      {visible.length === 0 ? (
        <EmptyState
          icon={<CheckCircle size={20} />}
          title="Aucun article à valider"
          description="Les articles sortis de production apparaîtront ici."
        />
      ) : (
        <>
          <div className="mb-1 hidden grid-cols-[minmax(0,1fr)_90px_120px_160px] gap-3 px-3 text-[11px] font-medium uppercase tracking-wide text-tertiary lg:grid">
            <div>Titre / Catégorie</div>
            <div className="text-center">Score global</div>
            <div>Date prévue</div>
            <div className="text-right">Actions</div>
          </div>
          <div className="flex flex-col">
            {visible.map((article) => {
              const score = finiteScore(article.global_score)
              const scoreColor = score === null ? 'text-tertiary' : score >= 85 ? 'text-success' : score >= 65 ? 'text-warning' : 'text-danger'
              return (
                <div
                  key={article.id}
                  className="group grid grid-cols-[minmax(0,1fr)_90px_120px_160px] items-center gap-3 border-b border-[#f0f0f0] px-3 py-3 transition-colors hover:bg-[#fafafa]"
                >
                  <div className="min-w-0">
                    <p className="truncate text-[13px] font-medium text-primary">{article.title || '(sans titre)'}</p>
                    <div className="mt-0.5 flex items-center gap-2 text-[11px] text-tertiary">
                      <span>{catName(article)}</span>
                      {article.critical_warnings.length > 0 && (
                        <span className="flex items-center gap-1 text-danger">
                          <AlertTriangle size={11} /> {article.critical_warnings.length} warning{article.critical_warnings.length > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex justify-center">
                    <span className={`text-[13px] font-semibold tabular-nums ${scoreColor}`}>
                      {article.global_score_valid === false ? '~' : ''}{score ?? '—'}
                    </span>
                  </div>
                  <span className={`text-[12px] ${article.scheduled_at ? 'text-secondary' : 'text-tertiary'}`}>
                    {article.scheduled_at ? formatDate(article.scheduled_at) : '—'}
                  </span>
                  <div className="flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                    <Button size="sm" variant="secondary" onClick={() => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}>
                      Ouvrir
                    </Button>
                    {article.scheduled_at && (
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={<Calendar size={12} />}
                        onClick={() => { setTargetId(article.id); setConfirmMode('schedule') }}
                      >
                        Programmer
                      </Button>
                    )}
                    <Button
                      size="sm"
                      icon={<Send size={12} />}
                      onClick={() => { setTargetId(article.id); setConfirmMode('publish') }}
                    >
                      Publier
                    </Button>
                    <button
                      type="button"
                      title="Marquer en correction"
                      onClick={() => handleMarkCorrection(article.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary transition-colors hover:bg-danger/10 hover:text-danger"
                    >
                      <XCircle size={13} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      <Modal
        open={confirmMode === 'publish' || confirmMode === 'schedule'}
        onClose={() => { if (!running) { setConfirmMode(null); setBulkResult(null) } }}
        title={confirmMode === 'publish' ? 'Publier maintenant' : 'Valider et programmer'}
        size="sm"
      >
        <div className="flex flex-col gap-4">
          {!bulkResult ? (
            <>
              <p className="text-[13px] text-secondary">
                {confirmMode === 'publish'
                  ? 'Publier cet article immédiatement ?'
                  : 'Valider et programmer cet article selon sa date prévue ?'}
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" className="flex-1 justify-center" onClick={() => setConfirmMode(null)}>Annuler</Button>
                <Button size="sm" loading={running} className="flex-1 justify-center" onClick={handleConfirm}>Confirmer</Button>
              </div>
            </>
          ) : (
            <>
              <div className="rounded-[10px] bg-surface-soft px-3 py-2 text-[13px] text-secondary">
                {bulkResult.validated_count ?? bulkResult.scheduled_count} traité(s), {bulkResult.blocked_count} bloqué(s).
              </div>
              <Button size="sm" className="justify-center" onClick={() => { setConfirmMode(null); setBulkResult(null) }}>Fermer</Button>
            </>
          )}
        </div>
      </Modal>
    </>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function PipelinePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = (searchParams.get('tab') ?? 'ideas') as 'ideas' | 'writing' | 'validate'

  const [categories, setCategories] = useState<Category[]>([])

  useEffect(() => {
    if (!projectId) return
    listCategories(projectId).then(setCategories).catch(() => {})
  }, [projectId])

  const setTab = (t: string) => setSearchParams({ tab: t }, { replace: true })

  if (!projectId) return null

  return (
    <div className="project-page project-page--wide">
      <div className="project-page-header">
        <div>
          <h1 className="text-[20px] font-semibold tracking-tight text-primary">Pipeline</h1>
          <p className="mt-0.5 text-[13px] text-secondary">Idées, rédaction en cours et articles à valider.</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-5 flex gap-0 border-b border-border">
        <TabButton active={tab === 'ideas'} onClick={() => setTab('ideas')} count={0}>Idées</TabButton>
        <TabButton active={tab === 'writing'} onClick={() => setTab('writing')} count={0}>En rédaction</TabButton>
        <TabButton active={tab === 'validate'} onClick={() => setTab('validate')} count={0}>À valider</TabButton>
      </div>

      {tab === 'ideas' && (
        <IdeasTab
          key="ideas"
          projectId={projectId}
          categories={categories}
        />
      )}
      {tab === 'writing' && <WritingTab key="writing" projectId={projectId} />}
      {tab === 'validate' && (
        <ValidateTab
          key="validate"
          projectId={projectId}
          categories={categories}
        />
      )}
    </div>
  )
}
