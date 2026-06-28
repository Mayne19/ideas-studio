import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, Calendar, CheckCircle, ExternalLink, RefreshCw, Send, XCircle } from '@/components/ui/hugeIcons'
import { bulkPublishArticles, bulkValidateArticles, listArticles, patchArticle } from '@/api/articles'
import type { BulkValidateResponse } from '@/api/articles'
import { listCategories } from '@/api/categories'
import type { Article, Category } from '@/types'
import { formatDate } from '@/utils/format'
import Button from '@/components/ui/Button'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import Modal from '@/components/ui/Modal'
import Select from '@/components/ui/Select'
import StatusBadge from '@/components/ui/StatusBadge'
import ScoreBadge from '@/components/ui/ScoreBadge'
import { Skeleton } from '@/components/ui/Skeleton'
import { finiteScore, getGeoScore, getOriginalityScore } from '@/lib/scoreBadge'

const VALIDATION_STATUSES = ['ready_to_publish']

type ValidationFilter =
  | 'all'
  | 'ready'
  | 'global_gte_90'
  | 'global_lt_90'
  | 'seo_lt_85'
  | 'quality_lt_85'
  | 'readability_lt_80'
  | 'geo_lt_80'
  | 'originality_lt_85'
  | 'critical'
  | 'missing_date'
  | 'needs_fix'

const FILTERS: Array<{ value: ValidationFilter; label: string }> = [
  { value: 'all', label: 'Tous les articles à valider' },
  { value: 'ready', label: 'Prêts à valider' },
  { value: 'global_gte_90', label: 'Global ≥ 90' },
  { value: 'global_lt_90', label: 'Global < 90' },
  { value: 'seo_lt_85', label: 'SEO < 85' },
  { value: 'quality_lt_85', label: 'Qualité < 85' },
  { value: 'readability_lt_80', label: 'Lisibilité < 80' },
  { value: 'geo_lt_80', label: 'GEO < 80' },
  { value: 'originality_lt_85', label: 'Originalité < 85' },
  { value: 'critical', label: 'Warnings critiques' },
  { value: 'missing_date', label: 'Sans date prévue' },
  { value: 'needs_fix', label: 'À corriger' },
]

const GRID = 'lg:grid-cols-[32px_minmax(320px,1fr)_86px_70px_70px_70px_70px_70px_70px_90px_130px_170px]'

function isReady(article: Article) {
  return article.is_validable === true && Boolean(article.scheduled_at)
}

function matchesFilter(article: Article, filter: ValidationFilter) {
  const global = finiteScore(article.global_score)
  const seo = finiteScore(article.seo_score)
  const quality = finiteScore(article.quality_score)
  const geo = getGeoScore(article)
  const originality = getOriginalityScore(article)
  if (filter === 'ready') return isReady(article)
  if (filter === 'global_gte_90') return global !== null && global >= 90
  if (filter === 'global_lt_90') return global === null || global < 90 || article.global_score_valid === false
  if (filter === 'seo_lt_85') return seo === null || seo < 85
  if (filter === 'quality_lt_85') return quality === null || quality < 85
  if (filter === 'readability_lt_80') return finiteScore(article.readability_score) === null || (finiteScore(article.readability_score) ?? 0) < 80
  if (filter === 'geo_lt_80') return geo === null || geo < 80
  if (filter === 'originality_lt_85') return originality === null || originality < 85
  if (filter === 'critical') return article.critical_warnings.length > 0
  if (filter === 'missing_date') return !article.scheduled_at
  if (filter === 'needs_fix') return article.is_validable === false || article.critical_warnings.length > 0
  return true
}

export default function ValidationPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [articles, setArticles] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [filter, setFilter] = useState<ValidationFilter>('all')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [tick, setTick] = useState(0)
  const [error, setError] = useState('')
  const [bulkResult, setBulkResult] = useState<BulkValidateResponse | null>(null)
  const [confirmMode, setConfirmMode] = useState<'schedule' | 'publish' | 'correction' | null>(null)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    if (!projectId) return
    listCategories(projectId).then(setCategories).catch(() => {})
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setStatus('loading') })
    Promise.all(VALIDATION_STATUSES.map((s) => listArticles(projectId, { status: s, limit: 500 })))
      .then((groups) => {
        if (cancelled) return
        const rows = groups.flat().sort((a, b) => b.updated_at.localeCompare(a.updated_at))
        setArticles(rows)
        setSelectedIds(new Set())
        setStatus('success')
      })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }, [projectId, tick])

  const visibleArticles = useMemo(
    () => articles.filter((article) => matchesFilter(article, filter)),
    [articles, filter],
  )

  const selectedArticles = visibleArticles.filter((article) => selectedIds.has(article.id))
  const selectedCount = selectedArticles.length

  function categoryName(article: Article) {
    return categories.find((c) => c.id === article.category_id)?.name ?? 'Sans catégorie'
  }

  function toggle(id: string, checked: boolean) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (checked) next.add(id)
      else next.delete(id)
      return next
    })
  }

  function toggleAll(checked: boolean) {
    setSelectedIds(checked ? new Set(visibleArticles.map((article) => article.id)) : new Set())
  }

  async function runBulkAction() {
    if (!projectId || !confirmMode || selectedCount === 0) return
    setRunning(true)
    setError('')
    setBulkResult(null)
    try {
      if (confirmMode === 'schedule') {
        const result = await bulkValidateArticles(projectId, selectedArticles.map((article) => article.id))
        setBulkResult(result)
      } else if (confirmMode === 'publish') {
        const result = await bulkPublishArticles(projectId, selectedArticles.map((article) => article.id))
        setBulkResult(result)
      } else {
        await Promise.all(selectedArticles.map((article) => patchArticle(projectId, article.id, { status: 'correction_needed' })))
        setConfirmMode(null)
      }
      setTick((t) => t + 1)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible.')
      setConfirmMode(null)
    } finally {
      setRunning(false)
    }
  }

  if (status === 'loading') {
    return (
      <div className="project-page project-page--wide">
        <Skeleton className="mb-4 h-10 w-72 rounded-[8px]" />
        <div className="flex flex-col gap-2">
          {Array.from({ length: 8 }).map((_, index) => <Skeleton key={index} className="h-16 rounded-[8px]" />)}
        </div>
      </div>
    )
  }

  if (status === 'error') return <ErrorState message="Impossible de charger les articles à valider." onRetry={() => setTick((t) => t + 1)} />

  return (
    <>
      <div className="project-page project-page--wide">
        <div className="project-page-header">
          <div>
            <h1 className="text-[20px] font-semibold tracking-tight text-primary">Validation</h1>
            <p className="mt-0.5 text-[13px] text-secondary">
              Articles sortis de production, en attente de décision humaine.
            </p>
          </div>
          <Button size="sm" variant="secondary" icon={<RefreshCw size={13} />} onClick={() => setTick((t) => t + 1)}>
            Rafraîchir
          </Button>
        </div>

        {error && (
          <div className="mb-4 rounded-[8px] border border-danger/20 bg-danger/5 px-4 py-2.5 text-[13px] text-danger">
            {error}
          </div>
        )}

        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <Select
            options={FILTERS}
            value={filter}
            onChange={(event) => setFilter(event.target.value as ValidationFilter)}
            className="w-64"
            aria-label="Filtre validation"
          />
          <div className="flex flex-wrap items-center gap-2">
            {selectedCount > 0 && (
              <>
                <Button size="sm" variant="secondary" onClick={() => setConfirmMode('correction')}>
                  Renvoyer en correction ({selectedCount})
                </Button>
                <Button size="sm" variant="secondary" icon={<Calendar size={13} />} onClick={() => setConfirmMode('schedule')}>
                  Valider et programmer ({selectedCount})
                </Button>
                <Button size="sm" icon={<Send size={13} />} onClick={() => setConfirmMode('publish')}>
                  Publier maintenant ({selectedCount})
                </Button>
              </>
            )}
          </div>
        </div>

        {visibleArticles.length === 0 ? (
          <EmptyState
            icon={<CheckCircle size={22} />}
            title="Aucun article à valider"
            description="Les articles prêts apparaîtront ici dès qu'ils sortiront de Production."
            action={{ label: 'Voir la production', onClick: () => navigate(`/projects/${projectId}/production`) }}
          />
        ) : (
          <>
            <div className={`hidden gap-3 px-4 pb-1.5 text-[11px] font-medium uppercase tracking-wide text-tertiary lg:grid ${GRID}`}>
              <label>
                <input
                  type="checkbox"
                  checked={selectedCount > 0 && selectedCount === visibleArticles.length}
                  onChange={(event) => toggleAll(event.target.checked)}
                  aria-label="Sélectionner les articles filtrés"
                />
              </label>
              <div>Titre / catégorie</div>
              <div className="text-center">Global</div>
              <div className="text-center">SEO</div>
              <div className="text-center">Qualité</div>
              <div className="text-center">GEO</div>
              <div className="text-center">Originalité</div>
              <div className="text-center">Warnings</div>
              <div>Date cible</div>
              <div className="text-right">Actions</div>
            </div>
            <div className="flex flex-col gap-1.5">
              {visibleArticles.map((article) => {
                const criticalCount = article.critical_warnings.length
                return (
                  <div key={article.id} className={`grid gap-3 rounded-[8px] border border-border bg-surface px-4 py-3 transition-colors hover:bg-surface-soft lg:items-center ${GRID}`}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(article.id)}
                      onChange={(event) => toggle(article.id, event.target.checked)}
                      aria-label={`Sélectionner ${article.title}`}
                    />
                    <div className="min-w-0">
                      <button
                        type="button"
                        onClick={() => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}
                        className="block w-full truncate text-left text-[13px] font-semibold text-primary hover:text-accent"
                      >
                        {article.title}
                      </button>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-tertiary">
                        <span className="font-medium text-accent">{categoryName(article)}</span>
                        <span>·</span>
                        <StatusBadge status={article.status} />
                        {article.validation_reasons.length > 0 && (
                          <>
                            <span>·</span>
                            <span className="text-danger" title={article.validation_reasons.join('\n')}>
                              {article.validation_reasons.length} raison{article.validation_reasons.length > 1 ? 's' : ''}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <ScoreBadge value={finiteScore(article.global_score)} label="Global" valid={article.global_score_valid} className="w-full justify-center" />
                    <ScoreBadge value={finiteScore(article.seo_score)} label="SEO" className="w-full justify-center" />
                    <ScoreBadge value={finiteScore(article.quality_score)} label="Qualité" className="w-full justify-center" />
                    <ScoreBadge value={finiteScore(article.readability_score)} label="Lisibilité" className="w-full justify-center" />
                    <ScoreBadge value={getOriginalityScore(article)} label="Orig." className="w-full justify-center" />
                    <ScoreBadge value={getGeoScore(article)} label="GEO" className="w-full justify-center" />
                    <ScoreBadge value={finiteScore(article.eeat_score)} label="EEAT" className="w-full justify-center" />
                    <span className={`inline-flex items-center justify-center gap-1 rounded-full px-2 py-1 text-[11px] font-medium ${criticalCount > 0 ? 'bg-danger/10 text-danger' : 'bg-success/10 text-success'}`}>
                      {criticalCount > 0 ? <AlertTriangle size={11} /> : <CheckCircle size={11} />}
                      {criticalCount}
                    </span>
                    <span className={article.scheduled_at ? 'text-[12px] text-secondary' : 'inline-flex items-center gap-1 text-[12px] text-danger'}>
                      {!article.scheduled_at && <XCircle size={12} />}
                      {article.scheduled_at ? formatDate(article.scheduled_at) : 'Absente'}
                    </span>
                    <div className="flex items-center justify-end gap-1.5">
                      <Button size="sm" variant="secondary" icon={<ExternalLink size={12} />} onClick={() => navigate(`/projects/${projectId}/articles/${article.id}/edit`)}>
                        Ouvrir
                      </Button>
                      <Button size="sm" onClick={() => { setSelectedIds(new Set([article.id])); setConfirmMode('publish') }}>
                        Publier
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>

      <Modal
        open={confirmMode !== null}
        onClose={() => { if (!running) { setConfirmMode(null); setBulkResult(null) } }}
        title={confirmMode === 'publish' ? 'Publier maintenant' : confirmMode === 'correction' ? 'Renvoyer en correction' : 'Valider et programmer'}
        size="md"
      >
        <div className="flex flex-col gap-4">
          {!bulkResult ? (
            <>
              <p className="text-[13px] leading-relaxed text-secondary">
                {confirmMode === 'publish'
                  ? `Publication immédiate explicite de ${selectedCount} article(s). Les alertes de validation restent visibles mais ne bloquent pas votre décision.`
                  : confirmMode === 'correction'
                    ? `${selectedCount} article(s) repasseront en correction.`
                    : `${selectedCount} article(s) seront validés et programmés selon leur date prévue.`}
              </p>
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" className="flex-1 justify-center" onClick={() => setConfirmMode(null)}>
                  Annuler
                </Button>
                <Button size="sm" loading={running} className="flex-1 justify-center" onClick={runBulkAction}>
                  Confirmer
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="rounded-[8px] bg-surface-soft p-3 text-[13px] text-secondary">
                {bulkResult.scheduled_count} traité(s), {bulkResult.blocked_count} échec(s).
              </div>
              {bulkResult.blocked_articles.length > 0 && (
                <div className="max-h-64 overflow-auto rounded-[8px] border border-border">
                  {bulkResult.blocked_articles.map((item) => (
                    <div key={item.article_id} className="border-b border-border px-3 py-2 last:border-b-0">
                      <p className="text-[12px] font-medium text-primary">{item.title}</p>
                      <ul className="mt-1 list-disc pl-4 text-[11px] text-danger">
                        {item.reasons.map((reason, index) => <li key={index}>{reason}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
              <Button size="sm" className="justify-center" onClick={() => { setConfirmMode(null); setBulkResult(null) }}>
                Fermer
              </Button>
            </>
          )}
        </div>
      </Modal>
    </>
  )
}
