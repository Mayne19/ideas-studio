import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  FileText, Lightbulb, BarChart2, Sparkles, Globe,
  WifiOff, ArrowRight, AlertCircle, Clock, CheckCircle, PenLine,
  Edit3, Eye, Send, Star, BookOpen,
} from 'lucide-react'
import { useProject } from '@/context/ProjectContext'
import { useAuth } from '@/context/AuthContext'
import { listArticles } from '@/api/articles'
import { listCategories } from '@/api/categories'
import { getPerformanceSummary } from '@/api/performance'
import { listRecommendations } from '@/api/recommendations'
import type { Article, Category, OptimizationRecommendation } from '@/types'
import { Card } from '@/components/ui/Card'
import StatusBadge from '@/components/ui/StatusBadge'
import LoadingState from '@/components/ui/LoadingState'
import { formatDate } from '@/utils/format'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return "Aujourd'hui"
  if (days === 1) return 'Hier'
  if (days < 7) return `Il y a ${days} j`
  if (days < 30) return `Il y a ${Math.floor(days / 7)} sem.`
  return formatDate(iso)
}

function KpiCard({
  icon, value, suffix, label, trend, onClick,
}: {
  icon: React.ReactNode
  value: string | number
  suffix?: string
  label: string
  trend?: string
  onClick?: () => void
}) {
  return (
    <div
      className={`rounded-[16px] border border-border bg-surface p-4 flex flex-col gap-2 ${onClick ? 'cursor-pointer hover:border-accent/40 transition-colors' : ''}`}
      onClick={onClick}
    >
      <span className="text-accent">{icon}</span>
      <p className="text-[24px] font-semibold text-primary tracking-tight leading-none">
        {value}
        {suffix && <span className="text-[14px] font-normal text-tertiary ml-0.5">{suffix}</span>}
      </p>
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-tertiary">{label}</p>
        {trend && <span className="text-[11px] font-medium text-[#1a7a3a]">{trend}</span>}
      </div>
    </div>
  )
}

const TODO_ACCENT = {
  warning: 'bg-warning/8 text-[#c07000]',
  danger:  'bg-danger/8 text-danger',
  accent:  'bg-accent/8 text-accent',
  success: 'bg-success/8 text-[#1a7a3a]',
} as const

type TodoAccent = keyof typeof TODO_ACCENT

type TodoItem = {
  id: string
  icon: React.ReactNode
  label: string
  href: string
  accent: TodoAccent
}

type ActivityEvent = {
  id: string
  icon: React.ReactNode
  label: string
  articleTitle: string
  time: string
  href: string
}

type DashboardData = {
  recentArticles: Article[]
  categories: Category[]
  publishedCount: number
  writingCount: number
  ideasCount: number
  reviewNeededCount: number
  readyCount: number
  scheduledCount: number
  failedCount: number
  pendingRecs: OptimizationRecommendation[]
  totalViews: number | null
  avgSeoScore: number | null
  avgReadingTime: number | null
}

function deriveActivityEvents(articles: Article[], projectId: string): ActivityEvent[] {
  const events: ActivityEvent[] = []
  for (const a of articles.slice(0, 10)) {
    if (a.status === 'published') {
      events.push({
        id: `pub-${a.id}`,
        icon: <Send size={11} />,
        label: 'Article publié',
        articleTitle: a.title,
        time: timeAgo(a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    } else if (a.status === 'scheduled') {
      events.push({
        id: `sched-${a.id}`,
        icon: <Clock size={11} />,
        label: 'Publication programmée',
        articleTitle: a.title,
        time: timeAgo(a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    } else if (a.status === 'idea_proposed' || a.status === 'idea_priority') {
      events.push({
        id: `idea-${a.id}`,
        icon: <Lightbulb size={11} />,
        label: 'Idée créée',
        articleTitle: a.title,
        time: timeAgo(a.updated_at),
        href: `/projects/${projectId}/ideas`,
      })
    } else if (a.status === 'draft_ready' || a.status === 'review_needed') {
      events.push({
        id: `review-${a.id}`,
        icon: <Eye size={11} />,
        label: 'Brouillon prêt',
        articleTitle: a.title,
        time: timeAgo(a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    } else if (a.seo_score !== null) {
      events.push({
        id: `seo-${a.id}`,
        icon: <Star size={11} />,
        label: 'Analyse SEO terminée',
        articleTitle: a.title,
        time: timeAgo(a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    } else {
      events.push({
        id: `edit-${a.id}`,
        icon: <Edit3 size={11} />,
        label: 'Article modifié',
        articleTitle: a.title,
        time: timeAgo(a.updated_at),
        href: `/projects/${projectId}/articles/${a.id}/edit`,
      })
    }
  }
  return events.slice(0, 7)
}

export default function ProjectDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const { project, loading: projectLoading } = useProject()
  const { user } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    if (!projectId) return
    Promise.allSettled([
      listArticles(projectId, { limit: 15 }),
      listArticles(projectId, { status: 'published', limit: 200 }),
      listArticles(projectId, { status: 'writing_in_progress', limit: 100 }),
      listArticles(projectId, { status: 'idea_proposed', limit: 100 }),
      listArticles(projectId, { status: 'idea_priority', limit: 100 }),
      listArticles(projectId, { status: 'review_needed', limit: 100 }),
      listArticles(projectId, { status: 'ready_to_publish', limit: 100 }),
      listArticles(projectId, { status: 'scheduled', limit: 100 }),
      listArticles(projectId, { status: 'failed', limit: 100 }),
      listRecommendations(projectId),
      getPerformanceSummary(projectId, '30d'),
      listCategories(projectId),
    ]).then(([recent, published, writing, proposed, priority, review, ready, scheduled, failed, recs, perf, cats]) => {
      const recentArticles =
        recent.status === 'fulfilled'
          ? [...recent.value]
              .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
              .slice(0, 8)
          : []
      const categories = cats.status === 'fulfilled' ? cats.value : []
      const publishedArticles = published.status === 'fulfilled' ? published.value : []
      const scored = publishedArticles.filter((a) => a.seo_score !== null)
      const avgSeoScore = scored.length > 0
        ? scored.reduce((s, a) => s + (a.seo_score ?? 0), 0) / scored.length
        : null
      const worded = publishedArticles.filter((a) => a.word_count > 0)
      const avgReadingTime = worded.length > 0
        ? Math.round(worded.reduce((s, a) => s + a.word_count, 0) / worded.length / 200)
        : null
      setData({
        recentArticles,
        categories,
        publishedCount: publishedArticles.length,
        writingCount:   writing.status === 'fulfilled'   ? writing.value.length   : 0,
        ideasCount:
          (proposed.status === 'fulfilled' ? proposed.value.length : 0) +
          (priority.status === 'fulfilled' ? priority.value.length : 0),
        reviewNeededCount: review.status === 'fulfilled' ? review.value.length : 0,
        readyCount:     ready.status === 'fulfilled'     ? ready.value.length     : 0,
        scheduledCount: scheduled.status === 'fulfilled' ? scheduled.value.length : 0,
        failedCount:    failed.status === 'fulfilled'    ? failed.value.length    : 0,
        pendingRecs:
          recs.status === 'fulfilled'
            ? recs.value.filter((r) => r.status === 'pending')
            : [],
        totalViews: perf.status === 'fulfilled' ? perf.value.total_views : null,
        avgSeoScore,
        avgReadingTime,
      })
    })
  }, [projectId])

  if (projectLoading) return <LoadingState />

  const isConnected = project?.status === 'connected'
  const firstName = user?.name?.split(' ')[0] ?? user?.name ?? ''

  const todoItems: TodoItem[] = []
  if (!isConnected) {
    todoItems.push({
      id: 'connect',
      icon: <WifiOff size={14} />,
      label: 'Connecter votre blog pour activer le tracking et les analyses.',
      href: `/projects/${projectId}/settings/integration`,
      accent: 'warning',
    })
  }
  if (data) {
    const highRecs = data.pendingRecs.filter((r) => r.priority >= 3)
    if (highRecs.length > 0) {
      todoItems.push({
        id: 'recs',
        icon: <Sparkles size={14} />,
        label: `${highRecs.length} recommandation${highRecs.length > 1 ? 's' : ''} haute priorité à traiter.`,
        href: `/projects/${projectId}/recommendations`,
        accent: 'danger',
      })
    }
    if (data.reviewNeededCount > 0) {
      todoItems.push({
        id: 'review',
        icon: <AlertCircle size={14} />,
        label: `${data.reviewNeededCount} article${data.reviewNeededCount > 1 ? 's' : ''} en attente de révision.`,
        href: `/projects/${projectId}/articles`,
        accent: 'warning',
      })
    }
    if (data.ideasCount > 0) {
      todoItems.push({
        id: 'ideas',
        icon: <Lightbulb size={14} />,
        label: `${data.ideasCount} idée${data.ideasCount > 1 ? 's' : ''} en attente — commencez à rédiger.`,
        href: `/projects/${projectId}/ideas`,
        accent: 'accent',
      })
    }
    if (data.readyCount > 0) {
      todoItems.push({
        id: 'ready',
        icon: <Send size={14} />,
        label: `${data.readyCount} article${data.readyCount > 1 ? 's' : ''} prêt${data.readyCount > 1 ? 's' : ''} à publier.`,
        href: `/projects/${projectId}/articles`,
        accent: 'success',
      })
    }
    if (todoItems.length === 0) {
      todoItems.push({
        id: 'empty',
        icon: <CheckCircle size={14} />,
        label: 'Tout est en ordre. Générez de nouvelles idées pour continuer.',
        href: `/projects/${projectId}/ideas`,
        accent: 'success',
      })
    }
  }

  const activityEvents = data ? deriveActivityEvents(data.recentArticles, projectId ?? '') : []

  const seoValue = data?.avgSeoScore != null
    ? (data.avgSeoScore / 10).toFixed(1)
    : '—'

  const summaryText = (() => {
    if (!data) return 'Chargement de vos données…'
    if (data.publishedCount === 0 && data.writingCount === 0 && data.ideasCount === 0) {
      return 'Commencez par créer votre premier article ou générer des idées.'
    }
    if (!isConnected && data.publishedCount > 0) {
      return "Votre blog n'est pas encore connecté — installez le snippet pour activer les analytics."
    }
    return "Voici l'état de votre pipeline éditorial."
  })()

  return (
    <div className="mx-auto max-w-5xl">
      {/* Greeting */}
      <div className="mb-6 flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[14px] bg-accent/10 text-accent text-[18px] font-bold">
          {project?.name.charAt(0).toUpperCase() ?? '?'}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-[22px] font-semibold text-primary tracking-tight">
            {firstName ? `Bonjour, ${firstName} 👋` : 'Bonjour 👋'}
          </h1>
          <p className="mt-0.5 text-[13px] text-secondary">{summaryText}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-3">
            <span className="flex items-center gap-1 text-[12px] text-tertiary">
              <Globe size={11} />
              {project?.domain ?? '—'}
            </span>
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                isConnected ? 'bg-success/10 text-[#1a7a3a]' : 'bg-[#f0f0f2] text-tertiary'
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-[#1a7a3a]' : 'bg-[#c8c8cc]'}`} />
              {isConnected ? 'Connecté' : 'Non connecté'}
            </span>
          </div>
        </div>
      </div>

      {/* Onboarding */}
      {project && (!project.audience || !project.tone) && (
        <div className="mb-5 flex items-start gap-3 rounded-[14px] border border-warning/30 bg-warning/5 px-4 py-3">
          <AlertCircle size={16} className="mt-0.5 shrink-0 text-[#c07000]" />
          <div className="flex-1 min-w-0">
            <p className="text-[13px] font-medium text-primary">Complétez la configuration de votre projet</p>
            <p className="mt-0.5 text-[12px] text-secondary">
              Définissez l'audience cible et le ton éditorial pour améliorer la qualité de la génération IA.
            </p>
          </div>
          <button
            onClick={() => navigate(`/projects/${projectId}/settings`)}
            className="shrink-0 rounded-[8px] bg-[#c07000] px-3 py-1.5 text-[11px] font-medium text-white hover:bg-[#a05500] transition-colors"
          >
            Configurer
          </button>
        </div>
      )}

      {/* 5 KPI cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
        <KpiCard
          icon={<BarChart2 size={17} />}
          value={seoValue}
          suffix={data?.avgSeoScore != null ? '/10' : undefined}
          label="SEO moyen"
          onClick={() => navigate(`/projects/${projectId}/performance`)}
        />
        <KpiCard
          icon={<Globe size={17} />}
          value={data?.totalViews != null ? data.totalViews.toLocaleString('fr-FR') : '—'}
          label="Vues du mois"
          onClick={() => navigate(`/projects/${projectId}/traffic`)}
        />
        <KpiCard
          icon={<BookOpen size={17} />}
          value={data?.avgReadingTime != null ? data.avgReadingTime : '—'}
          suffix={data?.avgReadingTime != null ? ' min' : undefined}
          label="Temps moyen"
        />
        <KpiCard
          icon={<FileText size={17} />}
          value={data?.publishedCount ?? '—'}
          label="Publiés"
          onClick={() => navigate(`/projects/${projectId}/articles`)}
        />
        <KpiCard
          icon={<PenLine size={17} />}
          value={data?.writingCount ?? '—'}
          label="En cours"
          onClick={() => navigate(`/projects/${projectId}/articles`)}
        />
      </div>

      {/* Main 2-col layout: left=articles (65%), right=todo+activity (35%) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left — col-span-2 — Articles récents only */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <div className="flex items-center justify-between mb-4">
              <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide">Articles récents</p>
              <button
                onClick={() => navigate(`/projects/${projectId}/articles`)}
                className="text-[11px] text-accent hover:underline"
              >
                Voir tout →
              </button>
            </div>
            {!data || data.recentArticles.length === 0 ? (
              <div className="flex flex-col items-center gap-2 py-8 text-center">
                <FileText size={20} className="text-tertiary" />
                <p className="text-[13px] text-secondary">Aucun article pour l'instant.</p>
                <button
                  onClick={() => navigate(`/projects/${projectId}/articles`)}
                  className="text-[12px] text-accent hover:underline"
                >
                  Créer un article →
                </button>
              </div>
            ) : (
              <div className="flex flex-col divide-y divide-border">
                {data.recentArticles.map((a) => {
                  const cat = data.categories.find((c) => c.id === a.category_id)
                  return (
                    <div key={a.id} className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0">
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-[13px] font-medium text-primary">{a.title}</p>
                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                          {cat && (
                            <span className="text-[10px] font-medium text-accent/80">{cat.name}</span>
                          )}
                          <StatusBadge status={a.status} />
                          {a.seo_score !== null && (
                            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                              a.seo_score >= 70 ? 'bg-success/10 text-[#1a7a3a]' :
                              a.seo_score >= 40 ? 'bg-warning/10 text-[#c07000]' : 'bg-danger/10 text-danger'
                            }`}>
                              SEO {Math.round(a.seo_score)}
                            </span>
                          )}
                          <span className="text-[10px] text-tertiary flex items-center gap-0.5 ml-auto">
                            <Clock size={9} />
                            {timeAgo(a.updated_at)}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
                        className="shrink-0 flex items-center gap-1 rounded-[8px] border border-border px-2.5 py-1 text-[11px] font-medium text-secondary hover:bg-accent hover:text-white hover:border-accent transition-colors"
                      >
                        <Edit3 size={10} />
                        Éditer
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Right — col-span-1 — À faire + Activité stacked */}
        <div className="flex flex-col gap-4">
          {/* À faire maintenant */}
          <Card>
            <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide mb-3">À faire maintenant</p>
            <div className="flex flex-col gap-1.5">
              {(!data ? [] : todoItems).slice(0, 5).map((item) => (
                <button
                  key={item.id}
                  onClick={() => navigate(item.href)}
                  className="flex items-start gap-2.5 rounded-[10px] p-2 text-left hover:bg-[#f5f5f7] transition-colors"
                >
                  <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${TODO_ACCENT[item.accent]}`}>
                    {item.icon}
                  </span>
                  <span className="flex-1 text-[12px] text-primary leading-snug">{item.label}</span>
                  <ArrowRight size={11} className="mt-0.5 shrink-0 text-tertiary" />
                </button>
              ))}
              {!data && (
                <p className="text-[12px] text-tertiary text-center py-2">Chargement…</p>
              )}
            </div>
          </Card>

          {/* Activité récente */}
          <Card className="flex-1">
            <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide mb-3">Activité récente</p>
            {activityEvents.length === 0 ? (
              <p className="text-[12px] text-tertiary text-center py-4">Aucune activité récente.</p>
            ) : (
              <div className="flex flex-col gap-0.5">
                {activityEvents.map((ev) => (
                  <button
                    key={ev.id}
                    onClick={() => navigate(ev.href)}
                    className="flex items-start gap-2 rounded-[8px] px-2 py-1.5 text-left hover:bg-[#f5f5f7] transition-colors"
                  >
                    <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-accent/8 text-accent">
                      {ev.icon}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] font-medium text-secondary">{ev.label}</p>
                      <p className="text-[11px] text-primary truncate">{ev.articleTitle}</p>
                    </div>
                    <span className="text-[10px] text-tertiary shrink-0 mt-0.5">{ev.time}</span>
                  </button>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
