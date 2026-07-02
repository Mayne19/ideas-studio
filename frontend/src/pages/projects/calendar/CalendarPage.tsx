import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Calendar, ExternalLink, RefreshCw, List, ChevronLeft, ChevronRight } from '@/components/ui/hugeIcons'
import { listArticles } from '@/api/articles'
import type { Article } from '@/types'
import { STATUS_LABELS } from '@/utils/articleActions'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import StatusBadge from '@/components/ui/StatusBadge'
import Button from '@/components/ui/Button'
import EmptyState from '@/components/ui/EmptyState'
import { Card } from '@/components/ui/Card'

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
const MONTH_SHORT = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
const DAY_NAMES = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']

function pad2(value: number): string {
  return String(value).padStart(2, '0')
}

function localDateKey(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
}

function localDateKeyFromIso(iso: string | null | undefined): string | null {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null
  return localDateKey(date)
}

function dateFromKey(key: string): Date {
  const [year, month, day] = key.split('-').map(Number)
  return new Date(year, month - 1, day)
}

function formatDateKey(key: string): string {
  return dateFromKey(key).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
}

function getCalendarDate(article: Article): string | null {
  return article.published_at ?? article.scheduled_at ?? article.updated_at ?? article.created_at ?? null
}

function getArticleDateKey(article: Article): string | null {
  return localDateKeyFromIso(getCalendarDate(article))
}

function getPublicationDateKey(article: Article): string | null {
  return localDateKeyFromIso(article.published_at)
}

function heatmapTone(count: number): string {
  if (count <= 0) return 'bg-[rgba(0,0,0,0.045)]'
  if (count === 1) return 'bg-success/20'
  if (count === 2) return 'bg-success/35'
  if (count <= 4) return 'bg-success/85'
  return 'bg-success'
}

function getYearHeatmapWeeks(year: number): { monthLabel: string; days: (Date | null)[] }[] {
  const firstDay = new Date(year, 0, 1)
  const lastDay = new Date(year, 11, 31)
  const startOffset = (firstDay.getDay() + 6) % 7
  const cursor = new Date(year, 0, 1 - startOffset)
  const weeks: { monthLabel: string; days: (Date | null)[] }[] = []

  while (cursor <= lastDay || ((cursor.getDay() + 6) % 7) !== 0) {
    const days: (Date | null)[] = []
    let monthLabel = ''

    for (let dayIndex = 0; dayIndex < 7; dayIndex++) {
      const day = new Date(cursor)
      const inYear = day.getFullYear() === year
      if (inYear && day.getDate() === 1) {
        monthLabel = MONTH_SHORT[day.getMonth()]
      }
      days.push(inYear ? day : null)
      cursor.setDate(cursor.getDate() + 1)
    }

    weeks.push({ monthLabel, days })
  }

  return weeks
}

function PublicationHeatmapPanel({
  heatmapYear,
  heatmapTotal,
  publishedByDay,
  yearOptions,
  onYearChange,
}: {
  heatmapYear: number
  heatmapTotal: number
  publishedByDay: Record<string, number>
  yearOptions: number[]
  onYearChange: (year: number) => void
}) {
  const heatmapWeeks = getYearHeatmapWeeks(heatmapYear)
  const weekColumnWidth = 'minmax(12px, 1fr)'

  return (
    <Card padding="md" className="overflow-hidden">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[12px] font-semibold uppercase tracking-wide text-secondary">Activité de publication</p>
          <p className="mt-0.5 text-[12px] text-tertiary">
            {heatmapTotal} article{heatmapTotal > 1 ? 's' : ''} publié{heatmapTotal > 1 ? 's' : ''} en {heatmapYear}.
          </p>
        </div>
        <select
          value={heatmapYear}
          onChange={(event) => onYearChange(Number(event.target.value))}
          className="h-10 w-[96px] rounded-[10px] border border-border bg-transparent px-3 text-[12px] text-secondary outline-none transition-colors hover:bg-surface-muted focus:ring-1 focus:ring-accent/20"
          aria-label="Année de la heatmap"
        >
          {yearOptions.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </div>

      <div className="pb-2">
        <div
          className="grid w-full gap-x-1 gap-y-1"
          style={{ gridTemplateColumns: `32px repeat(${heatmapWeeks.length}, ${weekColumnWidth})` }}
        >
          <span />
          {heatmapWeeks.map((week, index) => (
            <span key={`month-${index}`} className="h-4 text-[10px] font-medium text-tertiary">
              {week.monthLabel}
            </span>
          ))}

          {DAY_NAMES.map((dayName, dayIndex) => (
            <div key={dayName} className="contents">
              <span className="flex h-3 items-center text-[9px] font-medium text-tertiary">
                {dayName.slice(0, 3)}
              </span>
              {heatmapWeeks.map((week, weekIndex) => {
                const day = week.days[dayIndex]
                  if (!day) {
                    return <span key={`${weekIndex}-${dayIndex}-empty`} className="h-3 w-full rounded-[3px]" />
                  }

                  const key = localDateKey(day)
                  const activityCount = publishedByDay[key] ?? 0
                  const label = `${activityCount} article${activityCount > 1 ? 's' : ''} publié${activityCount > 1 ? 's' : ''} le ${formatDateKey(key)}`
                  return (
                    <span
                      key={key}
                      title={label}
                      aria-label={label}
                      className={`h-3 w-full rounded-[3px] ${heatmapTone(activityCount)}`}
                    />
                  )
              })}
            </div>
          ))}
        </div>
      </div>

      <div className="mt-1 flex items-center justify-end gap-1.5 text-[10px] text-tertiary">
        <span>Moins</span>
        {[0, 1, 2, 4, 5].map((value) => (
          <span key={value} className={`h-3 w-3 rounded-[3px] ${heatmapTone(value)}`} />
        ))}
        <span>Plus</span>
      </div>
    </Card>
  )
}

export default function CalendarPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [articles, setArticles] = useState<Article[]>([])
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [tick, setTick] = useState(0)
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [currentDate, setCurrentDate] = useState(new Date())
  const [heatmapYear, setHeatmapYear] = useState(new Date().getFullYear())

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    listArticles(projectId, { limit: 500 })
      .then((all) => {
        if (!cancelled) {
          const sorted = [...all].sort((a, b) => {
            const dateA = getCalendarDate(a) ?? ''
            const dateB = getCalendarDate(b) ?? ''
            return dateA.localeCompare(dateB)
          })
          setArticles(sorted)
          setLoadStatus('success')
        }
      })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [projectId, tick])

  const year = currentDate.getFullYear()
  const month = currentDate.getMonth()

  function articlesForDay(day: Date): Article[] {
    const key = localDateKey(day)
    return articles.filter((a) => {
      const articleKey = getArticleDateKey(a)
      return articleKey === key
    })
  }

  // List view: group by month
  const grouped: Record<string, Article[]> = {}
  for (const a of articles) {
    const dateKey = getArticleDateKey(a)
    if (!dateKey) continue
    const key = dateKey.slice(0, 7)
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(a)
  }

  const publishedByDay: Record<string, number> = {}
  for (const article of articles) {
    const key = getPublicationDateKey(article)
    if (!key) continue
    publishedByDay[key] = (publishedByDay[key] ?? 0) + 1
  }
  const heatmapTotal = Object.entries(publishedByDay)
    .filter(([key]) => Number(key.slice(0, 4)) === heatmapYear)
    .reduce((total, [, count]) => total + count, 0)
  const yearOptions = Array.from(new Set([
    new Date().getFullYear(),
    new Date().getFullYear() - 1,
    new Date().getFullYear() - 2,
    ...articles.flatMap((article) => {
      const keys = [getArticleDateKey(article), getPublicationDateKey(article)].filter(Boolean) as string[]
      return keys.map((key) => Number(key.slice(0, 4)))
    }),
  ])).sort((a, b) => b - a)

  return (
    <div className="mx-auto max-w-5xl">
      {loadStatus === 'loading' && <LoadingState />}
      {loadStatus === 'error' && <ErrorState onRetry={() => setTick(t => t + 1)} />}

      {loadStatus === 'success' && (
        <div className="flex flex-col gap-5">
          <div>
            <div className="mb-5">
              <h1 className="text-[20px] font-semibold text-primary tracking-tight">Calendrier éditorial</h1>
              <p className="mt-0.5 text-[14px] text-secondary">
                Articles programmés et publiés dans le temps.
              </p>
            </div>

            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex h-10 overflow-hidden rounded-[10px] border border-border">
                <button
                  onClick={() => setViewMode('list')}
                  className={`flex items-center gap-1.5 px-3 text-[12px] font-medium transition-colors ${
                    viewMode === 'list' ? 'bg-accent text-white' : 'text-secondary hover:bg-surface-soft'
                  }`}
                >
                  <List size={13} />
                  Liste
                </button>
                <button
                  onClick={() => setViewMode('month')}
                  className={`flex items-center gap-1.5 px-3 text-[12px] font-medium transition-colors ${
                    viewMode === 'month' ? 'bg-accent text-white' : 'text-secondary hover:bg-surface-soft'
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

          <PublicationHeatmapPanel
            heatmapYear={heatmapYear}
            heatmapTotal={heatmapTotal}
            publishedByDay={publishedByDay}
            yearOptions={yearOptions}
            onYearChange={setHeatmapYear}
          />

          <div className="min-w-0">
            {articles.length === 0 && (
              <EmptyState
                icon={<Calendar size={22} />}
                title="Aucun article programmé ou publié"
                description="Programmez un article depuis l'éditeur ou la liste des articles pour le voir apparaître ici."
                action={{ label: 'Voir les articles', onClick: () => navigate(`/projects/${projectId}/articles`) }}
              />
            )}

            {articles.length > 0 && viewMode === 'list' && (
              <div className="flex flex-col gap-6">
                {Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b)).map(([monthKey, arts]) => {
                  const [y, m] = monthKey.split('-').map(Number)
                  return (
                    <div key={monthKey}>
                      <p className="mb-3 text-[12px] font-semibold text-secondary uppercase tracking-wide">
                        {MONTH_NAMES[m - 1]} {y}
                      </p>
                      <div className="flex flex-col gap-2">
                        {arts.map((a) => {
                          const dateKey = getArticleDateKey(a)
                          const displayDate = dateKey ? formatDateKey(dateKey) : '—'
                          const displayDay = dateKey ? String(dateFromKey(dateKey).getDate()).padStart(2, '0') : '—'
                          const displayMonth = dateKey ? MONTH_NAMES[dateFromKey(dateKey).getMonth()]?.slice(0, 3) : ''
                          const dateLabel = a.status === 'scheduled' ? 'Programmé le' : a.status === 'published' ? 'Publié le' : a.status === 'idea_proposed' || a.status === 'idea_priority' ? 'Idée le' : a.status === 'writing_requested' || a.status === 'writing_in_progress' ? 'Rédaction le' : a.status === 'draft_ready' ? 'Brouillon le' : a.status === 'review_needed' ? 'Relecture le' : a.status === 'ready_to_publish' ? 'Prêt le' : 'Daté le'
                          return (
                            <div
                              key={a.id}
                              className="group flex items-center gap-3 rounded-[16px] border-2 border-border bg-transparent px-4 py-3 transition-colors hover:bg-surface-soft"
                            >
                              <div className="relative h-11 w-11 shrink-0">
                                <span className="absolute inset-x-1 bottom-0 h-8 rounded-[10px] bg-surface-muted" />
                                <div className="relative flex h-10 w-10 flex-col items-center justify-center rounded-[10px] border border-border bg-surface-muted">
                                  <span className="text-[16px] font-bold text-primary leading-none">{displayDay}</span>
                                  <span className="text-[9px] text-tertiary uppercase">{displayMonth}</span>
                                </div>
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="truncate text-[14px] font-medium text-primary">{a.title}</p>
                                <div className="flex items-center gap-2 mt-0.5 text-[12px] text-tertiary">
                                  {a.keyword && <span>{a.keyword}</span>}
                                  {a.keyword && <span>·</span>}
                                  <span>{dateLabel} {displayDate}</span>
                                </div>
                              </div>
                              <StatusBadge status={a.status} />
                              <button
                                onClick={() => navigate(`/projects/${projectId}/articles/${a.id}/edit`)}
                                className="opacity-0 group-hover:opacity-100 flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-surface-muted hover:text-primary transition-all"
                                title="Ouvrir l'éditeur"
                              >
                                <ExternalLink size={12} />
                              </button>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {articles.length > 0 && viewMode === 'month' && (
              <div>
          {/* Month navigator */}
          <div className="mb-4 flex items-center justify-between">
            <button
              onClick={() => setCurrentDate(new Date(year, month - 1, 1))}
              className="flex h-8 w-8 items-center justify-center rounded-[8px] text-secondary hover:bg-surface-soft transition-colors"
            >
              <ChevronLeft size={15} />
            </button>
            <p className="text-[15px] font-semibold text-primary">
              {MONTH_NAMES[month]} {year}
            </p>
            <button
              onClick={() => setCurrentDate(new Date(year, month + 1, 1))}
              className="flex h-8 w-8 items-center justify-center rounded-[8px] text-secondary hover:bg-surface-soft transition-colors"
            >
              <ChevronRight size={15} />
            </button>
          </div>

          {/* Day headers */}
          <div className="grid grid-cols-7 mb-1">
            {DAY_NAMES.map((d) => (
              <div key={d} className="py-2 text-center text-[12px] font-semibold text-tertiary uppercase tracking-wide">
                {d}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 gap-px bg-border rounded-[12px] overflow-hidden">
            {getMonthDays(year, month).map((day, i) => {
              if (!day) return <div key={`empty-${i}`} className="bg-surface-soft min-h-[80px] p-1" />
              const dayArts = articlesForDay(day)
              const isToday = day.toDateString() === new Date().toDateString()
              return (
                <div
                  key={localDateKey(day)}
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
                            ? 'bg-blue-500/10 text-blue-600 hover:bg-blue-500/15'
                            : a.status === 'published'
                            ? 'bg-success/8 text-success hover:bg-success/12'
                            : a.status === 'idea_proposed' || a.status === 'idea_priority'
                            ? 'bg-accent/8 text-accent hover:bg-accent/12'
                            : a.status === 'writing_requested' || a.status === 'writing_in_progress' || a.status === 'draft_ready'
                            ? 'bg-accent/8 text-accent hover:bg-accent/12'
                            : a.status === 'review_needed' || a.status === 'ready_to_publish'
                            ? 'bg-warning/8 text-warning hover:bg-warning/12'
                            : 'bg-surface-soft text-secondary hover:bg-surface-muted'
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
          <div className="mt-3 flex flex-wrap items-center gap-3 text-[12px] text-tertiary">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-accent" />
              Idée
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-tertiary" />
              En rédaction
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-blue-600" />
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
        </div>
      )}
    </div>
  )
}
