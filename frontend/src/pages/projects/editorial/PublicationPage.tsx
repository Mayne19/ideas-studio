import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import { listPublicationCalendar, type WorkflowArticle } from '@/api/editorialWorkflow'

export default function PublicationPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [articles, setArticles] = useState<WorkflowArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!projectId) return
    listPublicationCalendar(projectId).then(setArticles).catch((err) => setError(err instanceof Error ? err.message : 'Impossible de charger le calendrier.')).finally(() => setLoading(false))
  }, [projectId])

  return <div className="mx-auto flex max-w-5xl flex-col gap-6">
    <header><p className="text-[12px] font-medium uppercase tracking-[0.16em] text-tertiary">Parcours éditorial</p><h1 className="mt-2 text-[28px] font-semibold tracking-[-0.03em] text-primary">Publication</h1><p className="mt-2 text-[14px] text-secondary">Les articles validés apparaissent ici avec leur date de publication prévue.</p></header>
    {error && <p className="rounded-[8px] border-2 border-red-200 px-4 py-3 text-[13px] text-red-700">{error}</p>}
    <Card><CardTitle>Calendrier</CardTitle>{loading ? <LoadingState label="Chargement du calendrier…" /> : articles.length === 0 ? <p className="py-8 text-[14px] text-secondary">Aucun article programmé.</p> : <div className="mt-3 divide-y divide-border">{articles.map((article) => <div key={article.id} className="flex items-center justify-between gap-4 py-4"><div className="min-w-0"><p className="truncate text-[14px] font-medium text-primary">{article.title}</p><p className="mt-1 text-[12px] text-tertiary">/{article.slug}</p></div><time className="shrink-0 rounded-[7px] bg-surface-soft px-3 py-2 text-[12px] font-medium text-secondary">{article.scheduled_for ? new Date(article.scheduled_for).toLocaleString('fr-FR') : 'Date à définir'}</time></div>)}</div>}</Card>
  </div>
}
