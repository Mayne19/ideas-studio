import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Calendar, ExternalLink, RefreshCw, List, ChevronLeft, ChevronRight } from 'lucide-react'
import { listArticles } from '@/api/articles'
import type { Article } from '@/types'
import { STATUS_LABELS } from '@/utils/articleActions'
import { formatDate } from '@/utils/format'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import StatusBadge from '@/components/ui/StatusBadge'
import Button from '@/components/ui/Button'
import EmptyState from '@/components/ui/EmptyState'

type ViewMode = 'list' | 'month'

function getMonthDays(year: number, month: number): (Date | null)[] {
  const first = new Date(year, month, 1)
  const last = new Date(year, month + 1, 0)
  const days: (Date | null)[] = []
  // Fill leading nulls for the first week
  const startDay = (first.getDay() + 6) % 7 // Monday = 0
  for (let i = 0; i < startDay; i++) days.push(null)
  for (let d = 1; d <= last.getDate(); d++) days.push(new Date(year, month, d))
  return days
}

const MONTH_NAMES = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
  'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
const DAY_NAMES = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

export default function CalendarPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [articles, setArticles] = useState<Article[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [currentDate, setCurrentDate] = useState(new Date())

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    Promise.all([
      listArticles(projectId, { status: 'scheduled', limit: 200 }),
      listArticles(projectId, { status: 'published', limit: 200 }),
    ])
      .then(([scheduled, published]) => {
        if (!cancelled) {
          const all = [...scheduled, ...published]
            .sort((a, b) => {
              const dateA = a.scheduled_at ?? a.published_at ?? a.updated_at
              const dateB = b.scheduled_at ?? b.published_at ?? b.updated_at
              return dateA.localeCompare(dateB)
            })
          setArticles(all)
          setLoadStatus('success')
        }
      })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, tick])

  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()

  function articlesForDay(day: Date): Article[] {
    const iso = day.toISOString().slice(0, 10)
    return articles.filter((a) => {
      const d = (a.scheduled_at ?? a.published_at ?? '').slice(0, 10)
      return d === iso
    })
  }

  // List view: group by month
  const grouped: Record<string, Article[]> = {}
  for (const a of articles) {
    const date = a.scheduled_at ?? a.published_at ?? a.updated_at
    const key = date.slice(0, 7)
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(a)
  }

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-[20px] font-semibold text-primary tracking-tight">Calendrier éditorial</h1>
          <p className="mt-0.5 text-[13px] text-secondary">
            Articles programmés et publiés dans le temps.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-[10px] border border-border overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium transition-colors ${
                viewMode === 'list' ? 'bg-accent text-white' : 'text-secondary hover:bg-[#f0f0f2]'
              }`}
            >
              <List size={13} />
              Liste
            </button>
            <button
              onClick={() => setViewMode('month')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium transition-colors ${
                viewMode === 'month' ? 'bg-accent text-white' : 'text-secondary hover:bg-[#f0f0f2]'
              }`}
            >
              <Calendar size={13} />
              Mois
            </button>
          </div>
          <Button size="sm" variant="secondary" icon={<RefreshCw size={13} />} onClick={() => setTick(t => t + 1)}>
            Rafraîchir
          </Button>
        </div>
      </div>

      {loadStatus === 'loading' && <LoadingState />}
      {loadStatus === 'error' && <ErrorState onRetry={() => setTick(t => t + 1)} />}

      {loadStatus === 'success' && articles.length === 0 && (
        <EmptyState
          icon={<Calendar size={22} />}
          title="Aucun article programmé ou publié"
          description="Programmez un article depuis l'éditeur ou la liste des articles pour le voir apparaître ici."
          action={{ label: 'Voir les articles', onClick: () => navigate(`/projects/${projectId}/articles`) }}
        />
      )}

      {loadStatus === 'success' && articles.length > 0 && viewMode === 'list' && (
        <div className="flex flex-col gap-6">
          {Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([monthKey, arts]) => {
            const [y, m] = monthKey.split('-').map(Number)
            return (
              <div key={monthKey}>
                <p className="mb-3 text-[12px] font-semibold text-secondary uppercase tracking-wide">
                  {MONTH_NAMES[m - 1]} {y}
                </p>
                <div className="flex flex-col gap-2">
                  {arts.map((a) => (
                    <div
                      key={a.id}
                      className="flex items-center gap-3 rounded-[14px] border border-border bg-surface px-4 py-3 hover:shadow-card transition-shadow group"
                    >
                      <div className="flex h-10 w-10 shrink-0 flex-col items-center justify-center rounded-[10px] bg-[#f0f0f2]">
                        <span className="text-[16px] font-bold text-primary leading-none">
                          {(a.scheduled_at ?? a.published_at ?? '').slice(8, 10)}
                        </span>
                        <span className="text-[9px] text-tertiary uppercase">
                          {MONTH_NAMES[(Number((a.scheduled_at ?? a.published_at ?? '').slice(5, 7)) - 1)]?.slice(0, 3)}
                        </span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-[13px] font-medium text-primary">{a.title}</p>
                        <div className="flex items-center gap-2 mt-0.5 text-[11px] text-tertiary">
                          {a.keyword && <span>{a.keyword}</span>}
                          {a.keyword && <span>·</span>}
                          <span>{a.status === 'scheduled' ? `Programmé le ${formatDate(a.scheduled_at!)}` : `Publié le ${formatDate(a.published_at!)}`}</span>
                        </div>
                      </div>
                      <StatusBadge status={a.status} />
                      <button
                        onClick={() => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
                        className="opacity-0 group-hover:opacity-100 flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-[#e5e5e7] hover:text-primary transition-all"
                        title="Ouvrir l'éditeur"
                      >
                        <ExternalLink size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {loadStatus === 'success' && articles.length > 0 && viewMode === 'month' && (
        <div>
          {/* Month navigator */}
          <div className="mb-4 flex items-center justify-between">
            <button
              onClick={() => setCurrentDate(new Date(year, month - 1, 1))}
              className="flex h-8 w-8 items-center justify-center rounded-[8px] text-secondary hover:bg-[#f0f0f2] transition-colors"
            >
              <ChevronLeft size={15} />
            </button>
            <p className="text-[14px] font-semibold text-primary">
              {MONTH_NAMES[month]} {year}
            </p>
            <button
              onClick={() => setCurrentDate(new Date(year, month + 1, 1))}
              className="flex h-8 w-8 items-center justify-center rounded-[8px] text-secondary hover:bg-[#f0f0f2] transition-colors"
            >
              <ChevronRight size={15} />
            </button>
          </div>

          {/* Day headers */}
          <div className="grid grid-cols-7 mb-1">
            {DAY_NAMES.map((d) => (
              <div key={d} className="py-2 text-center text-[11px] font-semibold text-tertiary uppercase tracking-wide">
                {d}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 gap-px bg-border rounded-[12px] overflow-hidden">
            {getMonthDays(year, month).map((day, i) => {
              if (!day) return <div key={`empty-${i}`} className="bg-[#f9f9fb] min-h-[80px] p-1" />
              const dayArts = articlesForDay(day)
              const isToday = day.toDateString() === new Date().toDateString()
              return (
                <div
                  key={day.toISOString()}
                  className={`bg-surface min-h-[80px] p-1.5 ${isToday ? 'bg-accent/3' : ''}`}
                >
                  <p className={`text-[12px] font-medium mb-1 w-6 h-6 flex items-center justify-center rounded-full ${
                    isToday ? 'bg-accent text-white' : 'text-secondary'
                  }`}>
                    {day.getDate()}
                  </p>
                  <div className="flex flex-col gap-0.5">
                    {dayArts.slice(0, 2).map((a) => (
                      <button
                        key={a.id}
                        onClick={() => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
                        className={`rounded-[4px] px-1.5 py-0.5 text-left text-[10px] font-medium truncate transition-colors ${
                          a.status === 'scheduled'
                            ? 'bg-accent/10 text-accent hover:bg-accent/20'
                            : 'bg-success/10 text-[#1a7a3a] hover:bg-success/20'
                        }`}
                        title={a.title}
                      >
                        {a.title}
                      </button>
                    ))}
                    {dayArts.length > 2 && (
                      <p className="text-[10px] text-tertiary pl-1">+{dayArts.length - 2} autres</p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Legend */}
          <div className="mt-3 flex items-center gap-4 text-[11px] text-tertiary">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-accent" />
              {STATUS_LABELS['scheduled']}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-success" />
              {STATUS_LABELS['published']}
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
