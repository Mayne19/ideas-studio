import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import { ArrowLeft, Pencil, Eye } from '@/components/ui/hugeIcons'
import { getArticlePerformance } from '@/api/performance'
import type { ArticlePerformance } from '@/types'
import { Card } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import { formatDate } from '@/utils/format'

type Period = '1d' | '7d' | '30d' | '90d' | '180d' | '365d'
const PERIODS: { value: Period; label: string }[] = [
  { value: '1d', label: '1 jour' },
  { value: '7d', label: '7 jours' },
  { value: '30d', label: '30 jours' },
  { value: '90d', label: '90 jours' },
  { value: '180d', label: '6 mois' },
  { value: '365d', label: '1 an' },
]

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide mb-3">{children}</p>
}

function SimpleRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
      <span className="text-[14px] text-primary truncate max-w-[220px]" title={label}>{label || '—'}</span>
      <span className="text-[14px] font-medium text-secondary shrink-0 ml-2">{value.toLocaleString('fr-FR')}</span>
    </div>
  )
}

export default function ArticlePerformancePage() {
  const { projectId, articleId } = useParams<{ projectId: string; articleId: string }>()
  const navigate = useNavigate()
  const [period, setPeriod] = useState<Period>('1d')
  const [data, setData] = useState<ArticlePerformance | null>(null)
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')

  useEffect(() => {
    if (!articleId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoadStatus('loading') })
    getArticlePerformance(articleId, period)
      .then((d) => { if (!cancelled) { setData(d); setLoadStatus('success') } })
      .catch(() => { if (!cancelled) setLoadStatus('error') })
    return () => { cancelled = true }
  }, [articleId, period])

  if (loadStatus === 'loading') return <LoadingState />
  if (loadStatus === 'error') {
    return <ErrorState message="Impossible de charger la performance de l'article." onRetry={() => setLoadStatus('loading')} />
  }

  return (
    <div className="mx-auto max-w-3xl">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <button
          onClick={() => navigate(`/projects/${projectId}/performance`)}
          className="flex items-center gap-1.5 text-[14px] text-secondary hover:text-primary transition-colors"
        >
          <ArrowLeft size={14} />
          Performance
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(`/projects/${projectId}/articles/${articleId}/preview`)}
            className="flex items-center gap-1.5 text-[12px] text-secondary hover:text-primary transition-colors"
          >
            <Eye size={13} />
            Prévisualiser
          </button>
          <button
            onClick={() => navigate(`/projects/${projectId}/articles/${articleId}/edit`)}
            className="flex h-10 items-center gap-1.5 rounded-[8px] bg-accent px-3 text-[12px] font-medium text-white transition-colors hover:bg-accent/90"
          >
            <Pencil size={12} />
            Éditer
          </button>
        </div>
      </div>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[18px] font-semibold text-primary tracking-tight">Détail performance</h1>
          {data?.last_seen_at && (
            <p className="mt-0.5 text-[12px] text-tertiary">
              Dernière visite : {formatDate(data.last_seen_at)}
            </p>
          )}
        </div>
        <div className="flex h-10 overflow-hidden rounded-[10px] border border-border bg-transparent">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 text-[12px] font-medium transition-colors ${
                period === p.value ? 'bg-accent text-white' : 'text-secondary hover:bg-surface-soft'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {data && (
        <div className="flex flex-col gap-5">
          {/* Total views */}
          <Card padding="sm" className="inline-flex flex-col gap-1">
            <p className="text-[12px] text-tertiary">Pages vues sur la période</p>
            <p className="text-[28px] font-semibold text-primary tracking-tight">
              {data.views.toLocaleString('fr-FR')}
            </p>
          </Card>

          {/* Daily views chart */}
          {data.daily_views.length > 0 && (
            <Card>
              <SectionTitle>Vues par jour</SectionTitle>
              <ResponsiveContainer width="100%" height={180} minWidth={1} minHeight={1}>
                <LineChart data={data.daily_views} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#86868b' }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => v.slice(5)}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fontSize: 11, fill: '#86868b' }} tickLine={false} axisLine={false} width={28} />
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 10, border: '1px solid rgba(0,0,0,0.08)', boxShadow: 'none' }}
                    formatter={(v) => [Number(v).toLocaleString('fr-FR'), 'Vues']}
                  />
                  <Line type="monotone" dataKey="views" stroke="#007aff" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
            {data.referrers.length > 0 && (
              <Card>
                <SectionTitle>Sources de trafic</SectionTitle>
                {data.referrers.slice(0, 8).map((r) => (
                  <SimpleRow key={r.referrer} label={r.referrer || 'Direct'} value={r.views} />
                ))}
              </Card>
            )}
            {data.countries.length > 0 && (
              <Card>
                <SectionTitle>Pays</SectionTitle>
                {data.countries.slice(0, 8).map((c) => (
                  <SimpleRow key={c.country} label={c.country || 'Inconnu'} value={c.views} />
                ))}
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
