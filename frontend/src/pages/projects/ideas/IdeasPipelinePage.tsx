import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Lightbulb, Plus, Star, Pencil, X, ExternalLink, RefreshCw,
  Search, Info, Sparkles, CheckCircle, Eye, Send,
} from '@/components/ui/hugeIcons'
import { listIdeas, generateIdea, rejectIdea, setIdeaPriority, startWriting, createManualDraft, autoGenerateIdeas, sendToProduction } from '@/api/ideas'
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

const IDEA_STATUSES_TO_FETCH = [
  'idea_proposed', 'idea_priority', 'idea_rejected',
  'outline_ready', 'writing_requested', 'writing_in_progress', 'draft_ready',
]

const IDEA_STATI: { key: string; label: string; color: string }[] = [
  { key: '', label: 'Tous', color: '' },
  { key: 'idea_proposed', label: 'Proposée', color: 'bg-blue-100 text-blue-700' },
  { key: 'idea_priority', label: 'Prioritaire', color: 'bg-orange-100 text-orange-700' },
  { key: 'idea_rejected', label: 'Rejetée', color: 'bg-red-100 text-red-700' },
  { key: 'writing_requested', label: 'Rédaction demandée', color: 'bg-purple-100 text-purple-700' },
  { key: 'writing_in_progress', label: 'En rédaction', color: 'bg-purple-100 text-purple-700' },
  { key: 'draft_ready', label: 'Brouillon prêt', color: 'bg-green-100 text-green-700' },
]

function translateIdeaError(err: unknown, context: 'action' | 'generate' | 'reject'): string {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 403: return "Vous n'avez pas la permission d'effectuer cette action."
      case 409:
        if (context === 'generate') return 'Une idée est déjà en cours de génération. Attendez quelques instants.'
        return "Cette action n'est pas possible dans l'état actuel de l'idée."
      case 422: return 'Données invalides. Vérifiez les informations saisies.'
      case 503: return err.message || 'Provider IA indisponible, génération réelle impossible.'
      default: return err.message || `Erreur ${err.status}`
    }
  }
  return 'Une erreur inattendue est survenue.'
}

function getLastCompletedAgent(article: Article): string | null {
  if (article.completed_agent_keys) {
    try {
      const keys = JSON.parse(article.completed_agent_keys)
      if (Array.isArray(keys) && keys.length > 0) {
        return keys[keys.length - 1]
      }
    } catch { /* invalid JSON */ }
  }
  return null
}

function getNextAgent(article: Article): string | null {
  if (article.next_agent_key) return article.next_agent_key
  return null
}

function normalizeOpportunityScore(score: number | null | undefined): number | null {
  if (typeof score !== 'number' || !Number.isFinite(score)) return null
  const pct = Math.round(score * 100)
  if (pct <= 0) return null
  return Math.min(100, pct)
}

function OpportunityBadge({ score, reason }: { score: number | null | undefined; reason?: string | null }) {
  const pct = normalizeOpportunityScore(score)
  if (pct === null) return <span className="text-[12px] text-tertiary">—</span>
  const color = pct >= 70 ? 'bg-success/10 text-success' : pct >= 40 ? 'bg-warning/10 text-warning' : 'bg-danger/10 text-danger'
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${color}`} title={reason ?? ''}>
      {pct}/100
    </span>
  )
}

function StatusBadgeSmall({ status }: { status: string }) {
  const match = IDEA_STATI.find((s) => s.key === status)
  if (!match) return <span className="text-[11px] text-tertiary">{status}</span>
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium ${match.color}`}>
      {match.label}
    </span>
  )
}

type SortField = 'opportunity_score' | 'priority' | 'created_at' | 'title'
type SortDir = 'asc' | 'desc'

export default function IdeasPipelinePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [allIdeas, setAllIdeas] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)
  const [actionError, setActionError] = useState('')

  const [filterCategory, setFilterCategory] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSearch, setFilterSearch] = useState('')
  const [filterMinScore, setFilterMinScore] = useState(0)
  const [sortField, setSortField] = useState<SortField>('opportunity_score')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const [selectedIdeas, setSelectedIdeas] = useState<Set<string>>(new Set())

  const [previewIdea, setPreviewIdea] = useState<Article | null>(null)

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
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    Promise.all(IDEA_STATUSES_TO_FETCH.map((s) => listIdeas(projectId, s)))
      .then((results) => {
        if (cancelled) return
        setAllIdeas(results.flat())
        setLoadStatus('success')
      })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, tick])

  const filtered = useMemo(() => {
    let items = [...allIdeas]
    if (filterCategory) items = items.filter((a) => a.category_id === filterCategory)
    if (filterStatus) items = items.filter((a) => a.status === filterStatus)
    if (filterSearch) {
      const q = filterSearch.toLowerCase()
      items = items.filter((a) =>
        a.title.toLowerCase().includes(q) || (a.keyword ?? '').toLowerCase().includes(q)
      )
    }
    if (filterMinScore > 0) {
      items = items.filter((a) => {
        return (normalizeOpportunityScore(a.opportunity_score) ?? 0) >= filterMinScore
      })
    }
    items.sort((a, b) => {
      const cmp = sortField === 'opportunity_score'
        ? (normalizeOpportunityScore(a.opportunity_score) ?? 0) - (normalizeOpportunityScore(b.opportunity_score) ?? 0)
        : sortField === 'priority'
        ? a.priority - b.priority
        : sortField === 'created_at'
        ? a.created_at.localeCompare(b.created_at)
        : a.title.localeCompare(b.title)
      return sortDir === 'desc' ? -cmp : cmp
    })
    return items
  }, [allIdeas, filterCategory, filterStatus, filterSearch, filterMinScore, sortField, sortDir])

  function toggleSort(field: SortField) {
    if (sortField === field) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  function toggleSelect(id: string) {
    setSelectedIdeas((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleSelectAll() {
    if (selectedIdeas.size === filtered.length) {
      setSelectedIdeas(new Set())
    } else {
      setSelectedIdeas(new Set(filtered.map((a) => a.id)))
    }
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
      } else if (action === 'send-to-production') {
        await sendToProduction(article.id)
      }
      setTick((t) => t + 1)
    } catch (err) {
      setActionError(translateIdeaError(err, 'action'))
    }
  }

  async function handleBatchAction(action: string) {
    if (!projectId || selectedIdeas.size === 0) return
    setActionError('')
    let errored = false
    for (const id of selectedIdeas) {
      const article = allIdeas.find((a) => a.id === id)
      if (!article) continue
      try {
        if (action === 'prioritize') await setIdeaPriority(id, 1)
        else if (action === 'reject') await rejectIdea(id, { rejection_reason: 'Action groupée' })
      } catch {
        errored = true
      }
    }
    if (errored) setActionError('Certaines actions ont échoué.')
    setSelectedIdeas(new Set())
    setTick((t) => t + 1)
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

  const catMap = useMemo(() => {
    const m = new Map<string, Category>()
    for (const c of categories) m.set(c.id, c)
    return m
  }, [categories])

  return (
    <>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="mb-4 flex items-center justify-between shrink-0">
          <div>
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Idées</h1>
            <p className="mt-0.5 text-[13px] text-secondary">
              Backlog éditorial — idées proposées par l'IA, briefs et préparation production.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" icon={<RefreshCw size={13} />} onClick={() => setTick((t) => t + 1)}>
              Rafraîchir
            </Button>
            <Button size="sm" variant="secondary" icon={<Sparkles size={14} />} onClick={() => { setAutoOpen(true); setAutoResult(null); setAutoError(''); setAutoCount(3) }}>
              Génération automatique
            </Button>
            <Button size="sm" icon={<Plus size={14} />} onClick={() => setGenerateOpen(true)}>
              Générer une idée
            </Button>
          </div>
        </div>

        {/* Info banner */}
        <div className="mb-4 flex items-start gap-2.5 rounded-[12px] border border-border bg-[#f9f9fb] px-4 py-3 shrink-0">
          <Info size={14} className="mt-0.5 shrink-0 text-tertiary" />
          <p className="text-[13px] text-secondary leading-snug">
            Les idées sont générées par les agents IA de planification. Validez une idée pour l'envoyer en{' '}
            <button onClick={() => navigate(`/projects/${projectId}/production`)} className="text-accent hover:underline">
              Production
            </button>.
          </p>
        </div>

        {/* Filters */}
        <div className="mb-3 flex flex-wrap items-center gap-2 shrink-0">
          <div className="flex items-center gap-1.5 rounded-[10px] border border-border bg-surface px-3 py-1.5">
            <Search size={12} className="text-tertiary" />
            <input
              type="text"
              value={filterSearch}
              onChange={(e) => setFilterSearch(e.target.value)}
              placeholder="Rechercher..."
              className="w-28 bg-transparent text-[12px] text-primary outline-none placeholder:text-tertiary"
            />
          </div>
          {categories.length > 0 && (
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value)}
              className="rounded-[10px] border border-border bg-surface px-3 py-1.5 text-[12px] text-secondary cursor-pointer"
            >
              <option value="">Toutes catégories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          )}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-[10px] border border-border bg-surface px-3 py-1.5 text-[12px] text-secondary cursor-pointer"
          >
            {IDEA_STATI.map((s) => (
              <option key={s.key} value={s.key}>{s.label}</option>
            ))}
          </select>
          <select
            value={filterMinScore}
            onChange={(e) => setFilterMinScore(Number(e.target.value))}
            className="rounded-[10px] border border-border bg-surface px-3 py-1.5 text-[12px] text-secondary cursor-pointer"
          >
            <option value={0}>Tous scores</option>
            <option value={70}>Score ≥ 70</option>
            <option value={50}>Score ≥ 50</option>
            <option value={30}>Score ≥ 30</option>
          </select>
          {(filterCategory || filterStatus || filterSearch || filterMinScore > 0) && (
            <button
              onClick={() => { setFilterCategory(''); setFilterStatus(''); setFilterSearch(''); setFilterMinScore(0) }}
              className="text-[11px] text-accent hover:underline"
            >
              Réinitialiser
            </button>
          )}
        </div>

        {/* Batch actions */}
        {selectedIdeas.size > 0 && (
          <div className="mb-3 flex items-center gap-2 rounded-[10px] bg-accent/5 px-3 py-2 shrink-0">
            <span className="text-[12px] font-medium text-secondary">{selectedIdeas.size} sélectionnée(s)</span>
            <div className="flex gap-1.5 ml-2">
              <Button size="sm" variant="secondary" className="text-[11px] h-7 px-2" onClick={() => handleBatchAction('prioritize')}>
                <Star size={11} /> Prioriser
              </Button>
              <Button size="sm" variant="secondary" className="text-[11px] h-7 px-2" onClick={() => handleBatchAction('reject')}>
                <X size={11} /> Rejeter
              </Button>
            </div>
            <button
              onClick={() => setSelectedIdeas(new Set())}
              className="ml-auto text-[11px] text-tertiary hover:text-primary transition-colors"
            >
              Annuler
            </button>
          </div>
        )}

        {/* Action error */}
        {actionError && (
          <div className="mb-3 flex items-center justify-between rounded-[10px] border border-danger/20 bg-danger/5 px-4 py-2.5 text-[13px] text-danger shrink-0">
            <span>{actionError}</span>
            <button onClick={() => setActionError('')} className="ml-3 shrink-0 text-danger/60 hover:text-danger transition-colors">✕</button>
          </div>
        )}

        {/* Content */}
        {loadStatus === 'loading' && (
          <div className="flex flex-col gap-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full rounded-[10px]" />
            ))}
          </div>
        )}

        {loadStatus === 'error' && (
          <ErrorState message="Impossible de charger les idées." onRetry={() => setTick((t) => t + 1)} />
        )}

        {loadStatus === 'success' && allIdeas.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-surface-soft text-tertiary">
              <Lightbulb size={22} />
            </div>
            <p className="text-[15px] font-medium text-primary">Aucune idée pour l'instant</p>
            <p className="max-w-xs text-[13px] text-secondary">
              Lancez une génération pour proposer des idées d'articles via l'IA.
            </p>
            <Button size="sm" icon={<Plus size={14} />} onClick={() => setGenerateOpen(true)}>
              Générer une idée
            </Button>
          </div>
        )}

        {loadStatus === 'success' && allIdeas.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="w-8 px-2 py-2">
                    <input
                      type="checkbox"
                      checked={selectedIdeas.size === filtered.length && filtered.length > 0}
                      onChange={toggleSelectAll}
                      className="rounded-[4px] border-border"
                    />
                  </th>
                  <th className="px-2 py-2 text-left"><button onClick={() => toggleSort('opportunity_score')} className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-tertiary hover:text-secondary transition-colors">Score{sortField === 'opportunity_score' && <span className="text-accent">{sortDir === 'desc' ? '↓' : '↑'}</span>}</button></th>
                  <th className="px-2 py-2 text-left"><button onClick={() => toggleSort('priority')} className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-tertiary hover:text-secondary transition-colors">Prio{sortField === 'priority' && <span className="text-accent">{sortDir === 'desc' ? '↓' : '↑'}</span>}</button></th>
                  <th className="px-2 py-2 text-left"><button onClick={() => toggleSort('title')} className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-tertiary hover:text-secondary transition-colors">Titre / Brief{sortField === 'title' && <span className="text-accent">{sortDir === 'desc' ? '↓' : '↑'}</span>}</button></th>
                  <th className="px-2 py-2 text-left hidden md:table-cell">Catégorie</th>
                  <th className="px-2 py-2 text-left hidden lg:table-cell">Mot-clé</th>
                  <th className="px-2 py-2 text-left hidden lg:table-cell">Statut</th>
                  <th className="px-2 py-2 text-left hidden xl:table-cell">Dernier agent</th>
                  <th className="px-2 py-2 text-left hidden xl:table-cell">Prochain agent</th>
                  <th className="px-2 py-2 text-left"><button onClick={() => toggleSort('created_at')} className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-tertiary hover:text-secondary transition-colors">Date{sortField === 'created_at' && <span className="text-accent">{sortDir === 'desc' ? '↓' : '↑'}</span>}</button></th>
                  <th className="w-28 px-2 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((article) => {
                  const cat = catMap.get(article.category_id ?? '')
                  const lastAgent = getLastCompletedAgent(article)
                  const nextAgent = getNextAgent(article)
                  const isRejected = article.status === 'idea_rejected'
                  const isIdea = ['idea_proposed', 'idea_priority'].includes(article.status)
                  return (
                    <tr
                      key={article.id}
                      className={`border-b border-border/50 hover:bg-[#f9f9fb] transition-colors ${isRejected ? 'opacity-60' : ''}`}
                    >
                      <td className="px-2 py-2.5">
                        <input
                          type="checkbox"
                          checked={selectedIdeas.has(article.id)}
                          onChange={() => toggleSelect(article.id)}
                          className="rounded-[4px] border-border"
                        />
                      </td>
                      <td className="px-2 py-2.5">
                        <OpportunityBadge score={article.opportunity_score} />
                      </td>
                      <td className="px-2 py-2.5">
                        {article.priority > 0 ? (
                          <Star size={13} className="text-orange-500 fill-orange-500" />
                        ) : (
                          <span className="text-tertiary text-[11px]">—</span>
                        )}
                      </td>
                      <td className="px-2 py-2.5 max-w-[280px]">
                        <button
                          onClick={() => setPreviewIdea(article)}
                          className="text-[13px] font-medium text-primary hover:text-accent transition-colors text-left line-clamp-1"
                        >
                          {article.title}
                        </button>
                        {article.angle && (
                          <p className="text-[11px] text-tertiary line-clamp-1 mt-0.5">{article.angle}</p>
                        )}
                      </td>
                      <td className="px-2 py-2.5 hidden md:table-cell">
                        {cat ? (
                          <span className="text-[12px] text-secondary">{cat.name}</span>
                        ) : (
                          <span className="text-[12px] text-tertiary">—</span>
                        )}
                      </td>
                      <td className="px-2 py-2.5 hidden lg:table-cell">
                        {article.keyword ? (
                          <span className="rounded-full bg-accent/8 px-2 py-0.5 text-[10px] text-accent">{article.keyword}</span>
                        ) : (
                          <span className="text-[12px] text-tertiary">—</span>
                        )}
                      </td>
                      <td className="px-2 py-2.5 hidden lg:table-cell">
                        <StatusBadgeSmall status={article.status} />
                      </td>
                      <td className="px-2 py-2.5 hidden xl:table-cell">
                        <span className="text-[11px] text-tertiary">{lastAgent ?? '—'}</span>
                      </td>
                      <td className="px-2 py-2.5 hidden xl:table-cell">
                        <span className="text-[11px] font-medium text-accent">{nextAgent ?? '—'}</span>
                      </td>
                      <td className="px-2 py-2.5 whitespace-nowrap">
                        <span className="text-[11px] text-tertiary">{formatDate(article.created_at)}</span>
                      </td>
                      <td className="px-2 py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {isIdea && !isRejected && (
                            <>
                              {article.status === 'idea_proposed' && (
                                <button
                                  onClick={() => handleAction('prioritize', article)}
                                  className="flex h-7 w-7 items-center justify-center rounded-[6px] text-tertiary hover:bg-orange-50 hover:text-orange-600 transition-colors"
                                  title="Prioriser"
                                >
                                  <Star size={12} />
                                </button>
                              )}
                              <button
                                onClick={() => handleAction('start-writing', article)}
                                className="flex h-7 w-7 items-center justify-center rounded-[6px] text-tertiary hover:bg-purple-50 hover:text-purple-600 transition-colors"
                                title="Lancer la rédaction"
                              >
                                <Pencil size={12} />
                              </button>
                              <button
                                onClick={() => handleAction('send-to-production', article)}
                                className="flex h-7 w-7 items-center justify-center rounded-[6px] text-tertiary hover:bg-accent/10 hover:text-accent transition-colors"
                                title="Envoyer en production"
                              >
                                <Send size={12} />
                              </button>
                              <button
                                onClick={() => handleAction('reject', article)}
                                className="flex h-7 w-7 items-center justify-center rounded-[6px] text-tertiary hover:bg-danger/10 hover:text-danger transition-colors"
                                title="Rejeter"
                              >
                                <X size={12} />
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => setPreviewIdea(article)}
                            className="flex h-7 w-7 items-center justify-center rounded-[6px] text-tertiary hover:bg-surface-muted hover:text-primary transition-colors"
                            title="Voir le brief"
                          >
                            <Eye size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>

            {filtered.length === 0 && (
              <div className="flex flex-col items-center gap-2 py-12 text-center">
                <p className="text-[13px] text-secondary">Aucune idée ne correspond aux filtres.</p>
                <button
                  onClick={() => { setFilterCategory(''); setFilterStatus(''); setFilterSearch(''); setFilterMinScore(0) }}
                  className="text-[12px] text-accent hover:underline"
                >
                  Réinitialiser les filtres
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Preview / Brief modal */}
      <Modal
        open={!!previewIdea}
        onClose={() => setPreviewIdea(null)}
        title={previewIdea?.title ?? 'Brief'}
        size="lg"
      >
        {previewIdea && (
          <div className="flex flex-col gap-4 max-h-[70vh] overflow-y-auto">
            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-2">
              <OpportunityBadge score={previewIdea.opportunity_score} />
              <StatusBadgeSmall status={previewIdea.status} />
              {previewIdea.priority > 0 && (
                <span className="inline-flex items-center gap-1 rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-medium text-orange-700">
                  <Star size={10} className="fill-orange-500" /> Prioritaire
                </span>
              )}
              <span className="text-[11px] text-tertiary">Créé le {formatDate(previewIdea.created_at)}</span>
            </div>

            {/* Brief fields */}
            <div className="grid grid-cols-2 gap-3">
              {previewIdea.keyword && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Mot-clé principal</p>
                  <p className="text-[13px] text-primary">{previewIdea.keyword}</p>
                </div>
              )}
              {previewIdea.recommended_format && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Format recommandé</p>
                  <p className="text-[13px] text-primary capitalize">{previewIdea.recommended_format}</p>
                </div>
              )}
              {previewIdea.search_intent && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Intention de recherche</p>
                  <p className="text-[13px] text-primary">{previewIdea.search_intent}</p>
                </div>
              )}
              {previewIdea.audience && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Audience cible</p>
                  <p className="text-[13px] text-primary">{previewIdea.audience}</p>
                </div>
              )}
              {previewIdea.estimated_difficulty && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Difficulté estimée</p>
                  <p className="text-[13px] text-primary capitalize">{previewIdea.estimated_difficulty}</p>
                </div>
              )}
              {previewIdea.target_word_count && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Longueur cible</p>
                  <p className="text-[13px] text-primary">{previewIdea.target_word_count} mots</p>
                </div>
              )}
              {previewIdea.needs_faq !== null && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">FAQ prévue</p>
                  <p className="text-[13px] text-primary">{previewIdea.needs_faq ? 'Oui' : 'Non'}</p>
                </div>
              )}
              {previewIdea.needs_images !== null && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Images nécessaires</p>
                  <p className="text-[13px] text-primary">{previewIdea.needs_images ? 'Oui' : 'Non'}</p>
                </div>
              )}
              {previewIdea.target_write_at && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Date rédaction cible</p>
                  <p className="text-[13px] text-primary">{formatDate(previewIdea.target_write_at)}</p>
                </div>
              )}
              {previewIdea.target_review_at && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Date relecture cible</p>
                  <p className="text-[13px] text-primary">{formatDate(previewIdea.target_review_at)}</p>
                </div>
              )}
              {previewIdea.scheduled_at && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Date publication cible</p>
                  <p className="text-[13px] text-primary">{formatDate(previewIdea.scheduled_at)}</p>
                </div>
              )}
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Dernier agent terminé</p>
                <p className="text-[13px] text-primary">{getLastCompletedAgent(previewIdea) ?? 'Aucun'}</p>
              </div>
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Prochain agent</p>
                <p className="text-[13px] font-medium text-accent">{getNextAgent(previewIdea) ?? 'Aucun'}</p>
              </div>
              {previewIdea.workflow_status && (
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Phase workflow</p>
                  <p className="text-[13px] text-primary capitalize">{previewIdea.workflow_status}</p>
                </div>
              )}
            </div>

            {/* Estimated cost */}
            {previewIdea.estimated_cost_json && typeof previewIdea.estimated_cost_json === 'object' && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Coût estimé</p>
                <p className="text-[13px] text-primary">
                  {(previewIdea.estimated_cost_json as Record<string, unknown>).estimated_cost_eur != null
                    ? `${((previewIdea.estimated_cost_json as Record<string, unknown>).estimated_cost_eur as number).toFixed(4)} €`
                    : 'Non disponible'}
                </p>
              </div>
            )}

            {/* Secondary keywords */}
            {(() => {
              let sk: string[] | null = null
              try {
                if (typeof previewIdea.secondary_keywords_json === 'string') sk = JSON.parse(previewIdea.secondary_keywords_json)
                else if (Array.isArray(previewIdea.secondary_keywords_json)) sk = previewIdea.secondary_keywords_json as string[]
              } catch { console.error('Failed to parse secondary_keywords_json') }
              return sk && sk.length > 0
            })() && (
              <div className="col-span-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Mots-clés secondaires</p>
                <div className="flex flex-wrap gap-1">
                  {(() => {
                    let sk: string[] = []
                    try {
                      if (typeof previewIdea.secondary_keywords_json === 'string') sk = JSON.parse(previewIdea.secondary_keywords_json)
                      else if (Array.isArray(previewIdea.secondary_keywords_json)) sk = previewIdea.secondary_keywords_json as string[]
              } catch { console.error('Failed to parse secondary_keywords_json') }
                    return sk
                  })().map((kw, i) => (
                    <span key={i} className="rounded-full bg-accent/8 px-2 py-0.5 text-[10px] text-accent">{kw}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Agent outputs JSON */}
            {previewIdea.agent_outputs_json && (
              <details className="group">
                <summary className="cursor-pointer text-[11px] text-secondary hover:text-primary transition-colors">
                  Sorties des agents
                </summary>
                <pre className="mt-1 max-h-40 overflow-auto rounded-[6px] bg-surface-soft p-2 text-[10px] leading-relaxed text-primary">
                  {JSON.stringify(previewIdea.agent_outputs_json, null, 2)}
                </pre>
              </details>
            )}

            {/* Planning brief JSON */}
            {previewIdea.planning_brief_json && (
              <details className="group">
                <summary className="cursor-pointer text-[11px] text-secondary hover:text-primary transition-colors">
                  Brief planning
                </summary>
                <pre className="mt-1 max-h-40 overflow-auto rounded-[6px] bg-surface-soft p-2 text-[10px] leading-relaxed text-primary">
                  {JSON.stringify(previewIdea.planning_brief_json, null, 2)}
                </pre>
              </details>
            )}

            {/* Opportunity justification */}
            {previewIdea.opportunity_justification && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Justification du score</p>
                <p className="text-[13px] text-secondary leading-relaxed">{previewIdea.opportunity_justification}</p>
              </div>
            )}

            {/* Main answer summary */}
            {previewIdea.main_answer_summary && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Réponse principale attendue</p>
                <p className="text-[13px] text-secondary leading-relaxed">{previewIdea.main_answer_summary}</p>
              </div>
            )}

            {/* Angle */}
            {previewIdea.angle && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-tertiary mb-0.5">Angle éditorial</p>
                <p className="text-[13px] text-secondary leading-relaxed">{previewIdea.angle}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 pt-2 border-t border-border">
              {['idea_proposed', 'idea_priority'].includes(previewIdea.status) && (
                <>
                  <Button size="sm" icon={<Send size={12} />} onClick={() => { handleAction('send-to-production', previewIdea); setPreviewIdea(null) }}>
                    Envoyer en production
                  </Button>
                  <Button size="sm" icon={<Pencil size={12} />} variant="secondary" onClick={() => { handleAction('start-writing', previewIdea); setPreviewIdea(null) }}>
                    Lancer la rédaction
                  </Button>
                </>
              )}
              <Button size="sm" variant="secondary" icon={<ExternalLink size={12} />} onClick={() => { navigate(`/projects/${projectId}/articles/${previewIdea.id}/edit`); setPreviewIdea(null) }}>
                Ouvrir l'article
              </Button>
            </div>
          </div>
        )}
      </Modal>

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
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => setGenerateOpen(false)}>
              Annuler
            </Button>
            <Button type="submit" size="sm" loading={generating} className="flex-1 justify-center">
              Générer
            </Button>
          </div>
        </form>
      </Modal>

      {/* Auto-generate modal */}
      <Modal
        open={autoOpen}
        onClose={() => { setAutoOpen(false); setAutoResult(null); setAutoError('') }}
        title="Génération automatique d'idées"
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
              <div className="flex items-center gap-2 text-success">
                <CheckCircle size={15} />
                <p className="text-[13px] font-semibold">{autoResult.generated} idée(s) proposée(s)</p>
              </div>
              <div className="flex flex-col gap-2 max-h-80 overflow-y-auto">
                {autoResult.ideas.map((idea) => (
                  <div key={idea.id} className="rounded-[10px] border border-border bg-[#f9f9fb] p-3">
                    <p className="text-[13px] font-medium text-primary">{idea.title}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5">
                      {idea.keyword && <span className="rounded-full bg-accent/8 px-2 py-0.5 text-[10px] text-accent">{idea.keyword}</span>}
                      {normalizeOpportunityScore(idea.opportunity_score) !== null && (
                        <span className="text-[10px] text-tertiary">Score: {normalizeOpportunityScore(idea.opportunity_score)}%</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex gap-2 pt-1">
                <Button variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => { setAutoOpen(false); setAutoResult(null) }}>
                  Fermer
                </Button>
                <Button size="sm" className="flex-1 justify-center" onClick={() => { setAutoOpen(false); setAutoResult(null); setTick((t) => t + 1) }}>
                  Voir dans la liste
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
                    L'IA va proposer plusieurs idées d'articles basées sur le contexte de votre projet.
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
                <Button variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => { setAutoOpen(false); setAutoResult(null) }}>
                  Annuler
                </Button>
                <Button size="sm" loading={autoGenerating} className="flex-1 justify-center" onClick={handleAutoGenerate}>
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
            <Button type="button" variant="secondary" size="sm" className="flex-1 justify-center" onClick={() => { setRejectTarget(null); setRejectError('') }}>
              Annuler
            </Button>
            <Button type="submit" variant="danger" size="sm" loading={rejecting} className="flex-1 justify-center">
              Rejeter
            </Button>
          </div>
        </form>
      </Modal>
    </>
  )
}
