import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Calendar, ExternalLink, RefreshCw, List, ChevronLeft, ChevronRight } from 'lucide-react'
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
  if (count <= 0) return 'bg-[#f0f0f2]'
  if (count === 1) return 'bg-success/20'
  if (count === 2) return 'bg-success/35'
  if (count <= 4) return 'bg-success/55'
  return 'bg-success'
}

function getYearHeatmapRows(year: number): { monthLabel: string; days: (Date | null)[] }[] {
  const firstDay = new Date(year, 0, 1)
  const lastDay = new Date(year, 11, 31)
  const startOffset = (firstDay.getDay() + 6) % 7
  const cursor = new Date(year, 0, 1 - startOffset)
  const rows: { monthLabel: string; days: (Date | null)[] }[] = []

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

    rows.push({ monthLabel, days })
  }

  return rows
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
  const heatmapRows = getYearHeatmapRows(heatmapYear)

  return (
    <Card padding="sm" className="lg:sticky lg:top-4">
      <div className="mb-3">
        <p className="text-[12px] font-semibold uppercase tracking-wide text-secondary">Activité de publication</p>
        <p className="mt-0.5 text-[12px] text-tertiary">
          {heatmapTotal} article{heatmapTotal > 1 ? 's' : ''} publié{heatmapTotal > 1 ? 's' : ''} en {heatmapYear}.
        </p>
      </div>

      <div className="pb-1">
        <div className="mx-auto w-fit max-w-full">
          <div className="grid grid-cols-[34px_repeat(7,12px)] gap-x-1">
            <span />
            {DAY_NAMES.map((day) => (
              <span key={day} className="text-center text-[8px] font-medium text-tertiary">
                {day.slice(0, 1)}
              </span>
            ))}
          </div>

          <div className="mt-1 flex flex-col gap-0.5">
            {heatmapRows.map((row, rowIndex) => (
              <div key={rowIndex} className="grid grid-cols-[34px_repeat(7,12px)] gap-x-1">
                <span className="flex h-3 items-center text-[9px] font-medium text-tertiary">{row.monthLabel}</span>
                {row.days.map((day, dayIndex) => {
                  if (!day) {
                    return <span key={`${rowIndex}-empty-${dayIndex}`} className="h-3 w-3 rounded-[3px]" />
                  }

                  const key = localDateKey(day)
                  const activityCount = publishedByDay[key] ?? 0
                  const label = `${activityCount} article${activityCount > 1 ? 's' : ''} publié${activityCount > 1 ? 's' : ''} le ${formatDateKey(key)}`
                  return (
                    <span
                      key={key}
                      title={label}
                      aria-label={label}
                      className={`h-3 w-3 rounded-[3px] ${heatmapTone(activityCount)}`}
                    />
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-3 flex flex-col gap-2">
        <div className="flex items-center justify-center gap-1.5 text-[10px] text-tertiary">
          <span>Moins</span>
          {[0, 1, 2, 4, 5].map((value) => (
            <span key={value} className={`h-3 w-3 rounded-[3px] ${heatmapTone(value)}`} />
          ))}
          <span>Plus</span>
        </div>
        <select
          value={heatmapYear}
          onChange={(event) => onYearChange(Number(event.target.value))}
          className="mx-auto h-8 w-[84px] rounded-[9px] border border-border bg-surface px-2 text-[12px] text-secondary outline-none transition-colors hover:bg-[#f5f5f7] focus:border-accent focus:ring-1 focus:ring-accent/20"
          aria-label="Année de la heatmap"
        >
          {yearOptions.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
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
    Promise.all([
      listArticles(projectId, { status: 'scheduled', limit: 200 }),
      listArticles(projectId, { status: 'published', limit: 200 }),
    ])
      .then(([scheduled, published]) => {
        if (!cancelled) {
          const all = [...scheduled, ...published]
            .sort((a, b) => {
              const dateA = getCalendarDate(a) ?? ''
              const dateB = getCalendarDate(b) ?? ''
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
    <div className="mx-auto max-w-6xl">
      {loadStatus === 'loading' && <LoadingState />}
      {loadStatus === 'error' && <ErrorState onRetry={() => setTick(t => t + 1)} />}

      {loadStatus === 'success' && (
        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_220px]">
          <div className="min-w-0">
            <div className="mb-5">
              <h1 className="text-[20px] font-semibold text-primary tracking-tight">Calendrier éditorial</h1>
              <p className="mt-0.5 text-[13px] text-secondary">
                Articles programmés et publiés dans le temps.
              </p>
            </div>

            <div className="mb-4 flex items-center justify-between gap-3">
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
                          const dateLabel = a.status === 'scheduled' ? 'Programmé le' : a.status === 'published' ? 'Publié le' : 'Daté le'
                          return (
                            <div
                              key={a.id}
                              className="flex items-center gap-3 rounded-[16px] bg-surface px-4 py-3 transition-colors hover:bg-white group"
                            >
                              <div className="flex h-10 w-10 shrink-0 flex-col items-center justify-center rounded-[10px] bg-[#f0f0f2]">
                                <span className="text-[16px] font-bold text-primary leading-none">{displayDay}</span>
                                <span className="text-[9px] text-tertiary uppercase">{displayMonth}</span>
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="truncate text-[13px] font-medium text-primary">{a.title}</p>
                                <div className="flex items-center gap-2 mt-0.5 text-[11px] text-tertiary">
                                  {a.keyword && <span>{a.keyword}</span>}
                                  {a.keyword && <span>·</span>}
                                  <span>{dateLabel} {displayDate}</span>
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

          <aside className="min-w-0">
            <PublicationHeatmapPanel
              heatmapYear={heatmapYear}
              heatmapTotal={heatmapTotal}
              publishedByDay={publishedByDay}
              yearOptions={yearOptions}
              onYearChange={setHeatmapYear}
            />
          </aside>
        </div>
      )}
    </div>
  )
}
