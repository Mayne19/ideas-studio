import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from 'recharts'
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  BookOpen,
  Clock3,
  Eye,
  FileText,
  Lightbulb,
  Sparkles,
  Tags,
} from 'lucide-react'
import { getArticlesPerformance, getPerformanceSummary } from '@/api/performance'
import { listArticles } from '@/api/articles'
import { listCategories } from '@/api/categories'
import type { Article, ArticlePerformanceBrief, Category, PerformanceSummary } from '@/types'
import { Card } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import { formatAxisTick, formatMetric, percentOf } from '@/utils/trafficDisplay'

type Period = '1d' | '7d' | '30d' | '90d' | '180d' | '365d'

type ArticleMetric = {
  article: Article
  category: Category | null
  views: number
  variation: number | null
  engagement: number | null
  averageTime: number | null
  recommendation: string
}

const PERIODS: { value: Period; label: string }[] = [
  { value: '1d', label: '1 jour' },
  { value: '7d', label: '7 jours' },
  { value: '30d', label: '30 jours' },
  { value: '90d', label: '90 jours' },
  { value: '180d', label: '6 mois' },
  { value: '365d', label: '1 an' },
]

const STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  idea_proposed: 'Idée proposée',
  idea_priority: 'Prioritaire',
  writing_in_progress: 'En rédaction',
  draft_ready: 'Brouillon prêt',
  review_needed: 'À relire',
  ready_to_publish: 'Prêt',
  scheduled: 'Programmé',
  published: 'Publié',
  archived: 'Archivé',
}

const TOP_ARTICLE_BAR_COLOR = '#8f63d8'

function categoryColor(category: Category | null | undefined, fallbackIndex = 0) {
  const palette = ['#007aff', '#34c759', '#ff9500', '#ff3b30', '#5856d6', '#00a7a7']
  return category?.color || palette[fallbackIndex % palette.length]
}

function trendTick(period: Period, value: unknown) {
  const label = String(value)
  if (period === '1d' || period === '90d' || period === '180d' || period === '365d') return label
  return label.includes('-') ? label.slice(5) : label
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-secondary">{children}</p>
}

function StatCard({
  icon,
  value,
  label,
  variation,
  tone = 'accent',
}: {
  icon: React.ReactNode
  value: React.ReactNode
  label: string
  variation?: number | null
  tone?: 'accent' | 'success' | 'warning' | 'danger' | 'violet'
}) {
  const toneClass = {
    accent: 'bg-accent/10 text-accent',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/12 text-[#b46a00]',
    danger: 'bg-danger/10 text-danger',
    violet: 'bg-[#eef2ff] text-[#4f46e5]',
  }[tone]
  return (
    <Card padding="sm" className="flex h-full flex-col justify-between gap-2">
      <span className={`flex h-8 w-8 items-center justify-center rounded-[10px] ${toneClass}`}>{icon}</span>
      <div>
        <p className="truncate text-[22px] font-semibold tracking-tight text-primary">{value}</p>
        <div className="mt-0.5 flex items-center justify-between gap-2">
          <p className="text-[12px] text-tertiary">{label}</p>
          <VariationBadge value={variation} />
        </div>
      </div>
    </Card>
  )
}

function SplitMetric({ value, suffix }: { value: React.ReactNode; suffix: string }) {
  return (
    <span className="inline-flex items-baseline gap-0.5">
      <span>{value}</span>
      <span className="text-[13px] font-medium text-tertiary">{suffix}</span>
    </span>
  )
}

function VariationBadge({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return <span className="text-[12px] text-tertiary">—</span>
  const positive = value >= 0
  return (
    <span className={`text-[12px] font-semibold ${positive ? 'text-success' : 'text-danger'}`}>
      {positive ? '+' : ''}{value}%
    </span>
  )
}

function ScoreBadge({ label, value, showLabel = true }: { label: string; value: number | null; showLabel?: boolean }) {
  const color = value === null ? 'bg-[#f0f0f2] text-tertiary' : value >= 75 ? 'bg-success/10 text-[#16723a]' : value >= 55 ? 'bg-warning/12 text-[#a35b00]' : 'bg-danger/10 text-danger'
  return (
    <span className={`inline-flex min-w-8 items-center justify-center rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${color}`}>
      {showLabel ? `${label} ` : ''}{value ?? '—'}
    </span>
  )
}

const ACTION_SHORT: Record<string, string> = {
  'Mettre à jour': 'Mettre à jour',
  'Optimiser le titre': 'Optimiser',
  'Ajouter liens internes': 'Liens internes',
  'Améliorer meta description': 'Meta desc.',
  'Améliorer introduction': 'Introduction',
  Surveiller: 'Surveiller',
}

function ActionBadge({ action }: { action: string }) {
  const styles: Record<string, string> = {
    'Mettre à jour': 'bg-accent/10 text-accent',
    'Optimiser le titre': 'bg-warning/12 text-[#a35b00]',
    'Ajouter liens internes': 'bg-[#eef2ff] text-[#4f46e5]',
    'Améliorer meta description': 'bg-[#f0f9ff] text-[#0369a1]',
    'Améliorer introduction': 'bg-danger/10 text-danger',
    Surveiller: 'bg-success/10 text-[#16723a]',
  }
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${styles[action] ?? 'bg-[#f0f0f2] text-secondary'}`}
      title={action}
    >
      {ACTION_SHORT[action] ?? action}
    </span>
  )
}

function scoreAverage(metrics: ArticleMetric[]) {
  const values = metrics.flatMap((item) => [item.article.seo_score, item.article.readability_score, item.article.quality_score, item.article.eeat_score]).filter((value): value is number => typeof value === 'number')
  return values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : null
}

function statusLabel(status: string) {
  return STATUS_LABELS[status] ?? status.replaceAll('_', ' ')
}

function compactArticleTitle(article: Article) {
  const text = `${article.keyword ?? ''} ${article.title}`.toLowerCase()
  if (text.includes('roi')) return 'ROI'
  return article.keyword || article.title
}

function getRecommendation(metric: Pick<ArticleMetric, 'article' | 'views' | 'engagement'>) {
  const article = metric.article
  if ((article.seo_score ?? 100) < 60) return 'Optimiser le titre'
  if ((article.readability_score ?? 100) < 65) return 'Améliorer introduction'
  if ((article.quality_score ?? 100) < 65) return 'Ajouter liens internes'
  if (metric.views > 0 && (metric.engagement ?? 100) < 45) return 'Améliorer meta description'
  if (article.status === 'published' && Date.now() - new Date(article.updated_at).getTime() > 1000 * 60 * 60 * 24 * 90) return 'Mettre à jour'
  return 'Surveiller'
}

function buildArticleMetrics(
  articles: Article[],
  categories: Category[],
  perf: ArticlePerformanceBrief[],
): ArticleMetric[] {
  const perfById = new Map(perf.map((item) => [item.article_id, item]))
  return articles.map((article) => {
    const performance = perfById.get(article.id)
    const views = performance?.views ?? 0
    const variation = null
    const engagement = null
    const averageTime = null
    const category = categories.find((cat) => cat.id === article.category_id) ?? null
    const base = { article, category, views, variation, engagement, averageTime, recommendation: 'Surveiller' }
    return { ...base, recommendation: getRecommendation(base) }
  })
}

function DurationMetric({ seconds }: { seconds: number | null }) {
  if (seconds === null) return <>—</>
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  if (!minutes) {
    return (
      <span className="inline-flex items-baseline whitespace-nowrap">
        <span>{rest}</span>
        <span className="ml-0.5 text-[0.6em] font-medium text-tertiary">s</span>
      </span>
    )
  }
  return (
    <span className="inline-flex items-baseline whitespace-nowrap">
      <span>{minutes}</span>
      <span className="ml-0.5 text-[0.6em] font-medium text-tertiary">min</span>
      <span className="ml-1">{rest.toString().padStart(2, '0')}</span>
      <span className="ml-0.5 text-[0.6em] font-medium text-tertiary">s</span>
    </span>
  )
}

function DurationText({ seconds }: { seconds: number | null }) {
  if (seconds === null) return <>—</>
  const minutes = Math.floor(seconds / 60)
  const rest = seconds % 60
  return <>{minutes ? `${minutes} min ${rest.toString().padStart(2, '0')} s` : `${rest} s`}</>
}

function TrendList({ title, items, type }: { title: string; items: ArticleMetric[]; type: 'up' | 'down' }) {
  return (
    <Card>
      <SectionTitle>{title}</SectionTitle>
      <div className="flex flex-col gap-2">
        {items.length ? items.map((item) => (
          <div key={item.article.id} className="flex items-center gap-3 rounded-[12px] px-2 py-2 hover:bg-[#f9f9fb]">
            <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] ${type === 'up' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
              {type === 'up' ? <ArrowUpRight size={15} /> : <ArrowDownRight size={15} />}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-medium text-primary">{item.article.title}</p>
              <p className="text-[12px] text-tertiary">{formatMetric(item.views)} vues</p>
            </div>
            <VariationBadge value={item.variation} />
          </div>
        )) : (
          <p className="rounded-[12px] bg-[#f9f9fb] px-3 py-3 text-[13px] text-secondary">Aucune variation fiable sur cette période.</p>
        )}
      </div>
    </Card>
  )
}

function KeywordOpportunities() {
  return (
    <Card className="h-full">
      <SectionTitle>Mots-clés suivis</SectionTitle>
      <p className="rounded-[12px] bg-[#f9f9fb] px-3 py-3 text-[13px] text-secondary">
        Données mots-clés bientôt disponibles avec Search Console.
      </p>
    </Card>
  )
}

export default function PerformanceDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [period, setPeriod] = useState<Period>('1d')
  const [data, setData] = useState<PerformanceSummary | null>(null)
  const [articles, setArticles] = useState<Article[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [articlePerf, setArticlePerf] = useState<ArticlePerformanceBrief[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    Promise.all([
      getPerformanceSummary(projectId, period),
      getArticlesPerformance(projectId, period),
      listArticles(projectId, { limit: 100 }),
      listCategories(projectId),
    ])
      .then(([summary, perf, articleList, categoryList]) => {
        if (cancelled) return
        setData(summary)
        setArticlePerf(perf)
        setArticles(articleList)
        setCategories(categoryList)
        setLoadStatus('success')
      })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, period])

  const hasRealTraffic = Boolean(data && data.total_views > 0)
  const displayData = data
  const displayCategories = categories
  const displayArticles = articles
  const articleMetrics = useMemo(
    () => buildArticleMetrics(displayArticles, displayCategories, articlePerf).sort((a, b) => b.views - a.views),
    [displayArticles, displayCategories, articlePerf],
  )
  const hasData = !!displayData && hasRealTraffic

  if (loadStatus === 'loading') return <LoadingState />
  if (loadStatus === 'error') {
    return <ErrorState message="Impossible de charger les données de performance." onRetry={() => setLoadStatus('loading')} />
  }

  const publishedCount = articles.filter((article) => article.status === 'published').length
  const topArticle = articleMetrics[0]
  const optimizeItems = articleMetrics
    .filter((item) => item.recommendation !== 'Surveiller' || ((item.article.seo_score ?? 100) < 70 && item.views > 0))
    .slice(0, 6)
  const risingItems = articleMetrics.filter((item) => (item.variation ?? 0) > 0).slice(0, 5)
  const fallingItems = articleMetrics.filter((item) => (item.variation ?? 0) < 0).slice(0, 5)
  const averageReadSeconds = articleMetrics.length
    ? Math.round(articleMetrics.reduce((sum, item) => sum + (item.averageTime ?? 0), 0) / articleMetrics.length)
    : null
  const averageEngagement = articleMetrics.some((item) => item.engagement !== null)
    ? Math.round(articleMetrics.reduce((sum, item) => sum + (item.engagement ?? 0), 0) / articleMetrics.filter((item) => item.engagement !== null).length)
    : null
  const categoryRows = displayCategories
    .map((category) => {
      const related = articleMetrics.filter((item) => item.article.category_id === category.id)
      const views = related.reduce((sum, item) => sum + item.views, 0)
      return { category, views, count: related.length }
    })
    .filter((row) => row.count > 0)
    .sort((a, b) => b.views - a.views)
  const totalArticleViews = articleMetrics.reduce((sum, item) => sum + item.views, 0)
  const trendData = displayData?.trend_by_day ?? []
  const bestRiser = risingItems[0]
  const leaderCategory = categoryRows[0]
  const averageScore = scoreAverage(articleMetrics)

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-[20px] font-semibold tracking-tight text-primary">Performance</h1>
            <p className="mt-0.5 text-[13px] text-secondary">Identifiez les contenus qui montent, baissent ou méritent une optimisation.</p>
          </div>
        </div>
        <div className="flex overflow-hidden rounded-[10px] border border-border bg-surface">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1.5 text-[12px] font-medium transition-colors ${
                period === p.value ? 'bg-accent text-white' : 'text-secondary hover:bg-[#f0f0f2] hover:text-primary'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {!hasData || !displayData ? (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-[#f0f0f2] text-tertiary">
            <Eye size={22} />
          </div>
          <div>
            <p className="text-[15px] font-medium text-primary">Aucune donnée disponible pour le moment</p>
            <p className="mt-1 max-w-xs text-[13px] text-secondary">
              Connectez votre site pour commencer à collecter les statistiques.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard icon={<Eye size={18} />} value={formatMetric(displayData.total_views)} label="Vues totales" variation={null} tone="accent" />
            <StatCard icon={<Clock3 size={18} />} value={<DurationMetric seconds={averageReadSeconds} />} label="Temps moyen" variation={null} tone="violet" />
            <StatCard icon={<FileText size={18} />} value={publishedCount} label="Articles publiés" variation={null} tone="success" />
            <StatCard icon={<BarChart3 size={18} />} value={averageScore !== null ? <SplitMetric value={averageScore} suffix="/100" /> : '—'} label="Score éditorial moyen" variation={null} tone="warning" />
            <StatCard icon={<AlertTriangle size={18} />} value={optimizeItems.length} label="Articles à optimiser" variation={null} tone="danger" />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)] lg:items-stretch">
            <Card className="h-[320px]">
              <SectionTitle>Évolution des vues contenus</SectionTitle>
              <div className="h-[255px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} tickFormatter={(v) => trendTick(period, v)} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} width={44} allowDecimals={false} domain={[0, 'dataMax']} tickFormatter={formatAxisTick} />
                    <Tooltip cursor={false} contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid rgba(0,0,0,0.08)', boxShadow: 'none' }} labelStyle={{ color: '#1d1d1f', fontWeight: 600 }} formatter={(v) => [formatMetric(Number(v)), 'Vues']} />
                    <Line type="monotone" dataKey="views" stroke="#007aff" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: '#007aff' }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
            <div className="grid grid-cols-2 gap-3 lg:h-[320px]">
              <StatCard icon={<BookOpen size={18} />} value={topArticle ? formatMetric(topArticle.views) : '—'} label="Article le plus vu" variation={topArticle?.variation ?? null} tone="accent" />
              <StatCard
                icon={<ArrowUpRight size={18} />}
                value={bestRiser ? <span className="text-[22px] leading-tight">{compactArticleTitle(bestRiser.article)}</span> : '—'}
                label="Meilleure progression"
                variation={bestRiser?.variation ?? null}
                tone="success"
              />
              <StatCard icon={<Sparkles size={18} />} value={averageEngagement !== null ? <SplitMetric value={averageEngagement} suffix="%" /> : '—'} label="Engagement" variation={null} tone="violet" />
              <StatCard icon={<Tags size={18} />} value={leaderCategory ? formatMetric(leaderCategory.views) : '—'} label={leaderCategory ? `Catégorie : ${leaderCategory.category.name}` : 'Catégorie leader'} variation={null} tone="warning" />
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,1fr)]">
            <Card>
              <SectionTitle>Top articles par vues</SectionTitle>
              <div className="mb-4 h-[190px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={articleMetrics.slice(0, 6).map((item) => ({ title: item.article.title, views: item.views }))} layout="vertical" margin={{ top: 0, right: 12, bottom: 0, left: 0 }}>
                    <XAxis type="number" tick={{ fontSize: 10, fill: '#86868b' }} tickLine={false} axisLine={false} allowDecimals={false} domain={[0, 'dataMax']} tickFormatter={formatAxisTick} />
                    <YAxis type="category" dataKey="title" tick={{ fontSize: 10, fill: '#86868b' }} tickLine={false} axisLine={false} width={128} tickFormatter={(v: string) => v.length > 22 ? `${v.slice(0, 21)}…` : v} />
                    <Tooltip cursor={false} contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid rgba(0,0,0,0.08)' }} formatter={(v) => [formatMetric(Number(v)), 'Vues']} />
                    <Bar dataKey="views" fill={TOP_ARTICLE_BAR_COLOR} radius={[0, 4, 4, 0]} barSize={12} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <button onClick={() => navigate(`/projects/${projectId}/performance/articles`)} className="text-[12px] text-accent hover:underline">
                Voir tous les articles →
              </button>
            </Card>
            <Card>
              <SectionTitle>Articles à optimiser</SectionTitle>
              <div className="flex flex-col gap-2">
                {optimizeItems.length ? optimizeItems.map((item) => (
                  <div key={item.article.id} className="flex items-start gap-3 rounded-[12px] px-2 py-2 hover:bg-[#f9f9fb]">
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-warning/10 text-[#b46a00]"><Lightbulb size={15} /></span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[13px] font-medium text-primary">{item.article.title}</p>
                      <div className="mt-1"><ActionBadge action={item.recommendation} /></div>
                    </div>
                    <ScoreBadge label="SEO" value={item.article.seo_score} />
                  </div>
                )) : (
                  <p className="rounded-[12px] bg-[#f9f9fb] px-3 py-3 text-[13px] text-secondary">Aucun article prioritaire à optimiser.</p>
                )}
              </div>
            </Card>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <TrendList title="Articles en hausse" items={risingItems} type="up" />
            <TrendList title="Articles en baisse" items={fallingItems} type="down" />
          </div>

          <div className="grid items-stretch gap-6 lg:grid-cols-[minmax(280px,0.8fr)_minmax(0,1.2fr)]">
            <Card className="h-full">
              <SectionTitle>Performance par catégorie</SectionTitle>
              <div className="flex flex-col gap-1">
                {categoryRows.length ? categoryRows.slice(0, 6).map((row) => (
                  <div key={row.category.id} className="rounded-[10px] px-2 py-1.5 hover:bg-[#f9f9fb]">
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex min-w-0 items-center gap-2 truncate text-[13px] font-medium text-primary">
                        <span className="h-2.5 w-2.5 shrink-0 rounded-full bg-accent" style={{ backgroundColor: categoryColor(row.category) }} />
                        <span className="truncate">{row.category.name}</span>
                      </span>
                      <span className="text-[12px] font-semibold text-secondary">{formatMetric(row.views)}</span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[#f0f0f2]">
                      <div className="h-full rounded-full" style={{ width: `${percentOf(row.views, totalArticleViews)}%`, backgroundColor: categoryColor(row.category) }} />
                    </div>
                    <p className="mt-1 text-[11px] text-tertiary">{row.count} article{row.count > 1 ? 's' : ''}</p>
                  </div>
                )) : (
                  <p className="rounded-[12px] bg-[#f9f9fb] px-3 py-3 text-[13px] text-secondary">Aucune catégorie avec trafic pour le moment.</p>
                )}
              </div>
            </Card>
            <div className="h-full">
              <KeywordOpportunities />
            </div>
          </div>

          <Card>
            <SectionTitle>Tableau performance articles</SectionTitle>
            <div className="overflow-x-auto">
              <div className="min-w-[1040px]">
                <div className="grid grid-cols-[2fr_0.8fr_0.8fr_0.5fr_0.5fr_0.6fr_0.6fr_0.45fr_0.5fr_0.5fr_0.45fr_0.7fr_0.7fr] gap-2 border-b border-border px-2 pb-2 text-[11px] font-semibold uppercase tracking-wide text-tertiary">
                  <span className="truncate">Article</span><span className="whitespace-nowrap">Catégorie</span><span className="whitespace-nowrap">Statut</span><span className="whitespace-nowrap">Vues</span><span className="whitespace-nowrap">Variation</span><span className="whitespace-nowrap">Temps</span><span className="whitespace-nowrap">Engagement</span><span className="whitespace-nowrap">SEO</span><span className="whitespace-nowrap">Lisibilité</span><span className="whitespace-nowrap">Qualité</span><span className="whitespace-nowrap">EEAT</span><span className="whitespace-nowrap">MAJ</span><span className="whitespace-nowrap">Action</span>
                </div>
                {articleMetrics.slice(0, 12).map((item) => (
                  <div key={item.article.id} className="grid grid-cols-[2fr_0.8fr_0.8fr_0.5fr_0.5fr_0.6fr_0.6fr_0.45fr_0.5fr_0.5fr_0.45fr_0.7fr_0.7fr] gap-2 border-b border-border px-2 py-3 text-[12px] last:border-0">
                    <span className="min-w-0 truncate font-medium text-primary" title={item.article.title}>{item.article.title}</span>
                    <span className="truncate text-secondary whitespace-nowrap">{item.category?.name ?? '—'}</span>
                    <span className="truncate text-secondary whitespace-nowrap">{statusLabel(item.article.status)}</span>
                    <span className="font-semibold text-primary whitespace-nowrap">{formatMetric(item.views)}</span>
                    <span className="whitespace-nowrap"><VariationBadge value={item.variation} /></span>
                    <span className="text-secondary whitespace-nowrap"><DurationText seconds={item.averageTime} /></span>
                    <span className="text-secondary whitespace-nowrap">{item.engagement !== null ? `${item.engagement}%` : '—'}</span>
                    <span className="whitespace-nowrap"><ScoreBadge label="SEO" value={item.article.seo_score} showLabel={false} /></span>
                    <span className="whitespace-nowrap"><ScoreBadge label="Lis." value={item.article.readability_score} showLabel={false} /></span>
                    <span className="whitespace-nowrap"><ScoreBadge label="Qual." value={item.article.quality_score} showLabel={false} /></span>
                    <span className="whitespace-nowrap"><ScoreBadge label="EEAT" value={item.article.eeat_score} showLabel={false} /></span>
                    <span className="text-secondary whitespace-nowrap">{new Date(item.article.updated_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })}</span>
                    <span className="whitespace-nowrap"><ActionBadge action={item.recommendation} /></span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
