import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { BarChart2, ArrowLeft, ExternalLink, RefreshCw } from 'lucide-react'
import { getArticlesPerformance } from '@/api/performance'
import type { ArticlePerformanceBrief } from '@/types'
import { formatDate } from '@/utils/format'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import Button from '@/components/ui/Button'
import EmptyState from '@/components/ui/EmptyState'

type Period = '7d' | '30d' | '90d'

const PERIODS: { value: Period; label: string }[] = [
  { value: '7d',  label: '7 jours' },
  { value: '30d', label: '30 jours' },
  { value: '90d', label: '90 jours' },
]

function SeoBar({ score }: { score: number | null }) {
  if (score === null) return <span className="text-[12px] text-tertiary">—</span>
  const val = Math.round(score)
  const color = val >= 70 ? '#34c759' : val >= 40 ? '#ff9500' : '#ff3b30'
  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="h-1.5 flex-1 rounded-full bg-[#e5e5e7]">
        <div className="h-full rounded-full" style={{ width: `${val}%`, backgroundColor: color }} />
      </div>
      <span className="text-[12px] font-medium text-primary w-6 text-right">{val}</span>
    </div>
  )
}

export default function PerformanceArticlesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [articles, setArticles] = useState<ArticlePerformanceBrief[]>([])
  const [period, setPeriod] = useState<Period>('30d')
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    getArticlesPerformance(projectId, period)
      .then((data) => {
        if (!cancelled) {
          setArticles([...data].sort((a, b) => b.views - a.views))
          setLoadStatus('success')
        }
      })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, period, tick])

  const totalViews = articles.reduce((sum, a) => sum + a.views, 0)

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <button
            onClick={() => navigate(`/projects/${projectId}/performance`)}
            className="flex items-center gap-1.5 text-[13px] text-secondary hover:text-primary transition-colors mb-2"
          >
            <ArrowLeft size={13} />
            Performance
          </button>
          <h1 className="text-[20px] font-semibold text-primary tracking-tight">Articles</h1>
          <p className="mt-0.5 text-[13px] text-secondary">
            Performance par article — {totalViews.toLocaleString('fr-FR')} vues au total
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-[10px] border border-border overflow-hidden">
            {PERIODS.map((p) => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-3 py-1.5 text-[12px] font-medium transition-colors ${
                  period === p.value
                    ? 'bg-accent text-white'
                    : 'text-secondary hover:bg-[#f0f0f2] hover:text-primary'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <Button
            size="sm"
            variant="secondary"
            icon={<RefreshCw size={13} />}
            onClick={() => setTick((t) => t + 1)}
          >
            Rafraîchir
          </Button>
        </div>
      </div>

      {loadStatus === 'loading' && <LoadingState />}
      {loadStatus === 'error' && (
        <ErrorState
          message="Impossible de charger les performances."
          onRetry={() => setTick((t) => t + 1)}
        />
      )}
      {loadStatus === 'success' && articles.length === 0 && (
        <EmptyState
          icon={<BarChart2 size={22} />}
          title="Aucune donnée de performance"
          description="Installez le snippet de tracking et publiez des articles pour voir apparaître les données ici."
          action={{
            label: 'Voir l\'intégration',
            onClick: () => navigate(`/projects/${projectId}/settings/integration`),
          }}
        />
      )}
      {loadStatus === 'success' && articles.length > 0 && (
        <div className="rounded-[16px] border border-border bg-surface overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-4 px-4 py-2.5 border-b border-border bg-[#f9f9fb]">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-tertiary">Article</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-tertiary w-16 text-right">Vues</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-tertiary w-24 text-right hidden sm:block">Score SEO</span>
            <span className="text-[11px] font-semibold uppercase tracking-wide text-tertiary w-20 text-right hidden md:block">Publié</span>
          </div>

          {/* Rows */}
          <div className="divide-y divide-border">
            {articles.map((article) => (
              <div
                key={article.article_id}
                className="grid grid-cols-[1fr_auto_auto_auto] gap-4 px-4 py-3 items-center hover:bg-[#f9f9fb] transition-colors group"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium text-primary truncate">{article.title}</p>
                    <p className="text-[11px] text-tertiary truncate">{article.slug}</p>
                  </div>
                  <button
                    onClick={() => navigate(`/projects/${projectId}/performance/${article.article_id}`)}
                    className="shrink-0 opacity-0 group-hover:opacity-100 flex h-6 w-6 items-center justify-center rounded-[6px] text-tertiary hover:bg-[#e5e5e7] hover:text-primary transition-all"
                    title="Voir les détails"
                  >
                    <ExternalLink size={11} />
                  </button>
                </div>
                <span className="text-[13px] font-semibold text-primary w-16 text-right">
                  {article.views.toLocaleString('fr-FR')}
                </span>
                <div className="w-24 flex justify-end hidden sm:flex">
                  <SeoBar score={article.seo_score} />
                </div>
                <span className="text-[12px] text-tertiary w-20 text-right hidden md:block">
                  {article.published_at ? formatDate(article.published_at) : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
