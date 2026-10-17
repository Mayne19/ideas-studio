import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import { listWorkflowUpdates, requestWorkflowWriting, type WorkflowArticle } from '@/api/editorialWorkflow'

export default function UpdatesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [articles, setArticles] = useState<WorkflowArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function refresh() {
    if (!projectId) return
    setLoading(true)
    try { setArticles(await listWorkflowUpdates(projectId)) } catch (err) { setError(err instanceof Error ? err.message : 'Impossible de charger les mises à jour.') } finally { setLoading(false) }
  }
  useEffect(() => { void refresh() }, [projectId])

  async function sendBack(articleId: string) {
    if (!projectId) return
    try { await requestWorkflowWriting(projectId, articleId); await refresh() } catch (err) { setError(err instanceof Error ? err.message : 'Impossible de relancer cet article.') }
  }

  return <div className="mx-auto flex max-w-5xl flex-col gap-6">
    <header><p className="text-[12px] font-medium uppercase tracking-[0.16em] text-tertiary">Parcours éditorial</p><h1 className="mt-2 text-[28px] font-semibold tracking-[-0.03em] text-primary">Mises à jour</h1><p className="mt-2 text-[14px] text-secondary">Retrouvez les articles dont les informations doivent être revérifiées.</p></header>
    {error && <p className="rounded-[8px] border-2 border-red-200 px-4 py-3 text-[13px] text-red-700">{error}</p>}
    <Card><CardTitle>Informations à revoir</CardTitle>{loading ? <LoadingState label="Chargement des mises à jour…" /> : articles.length === 0 ? <p className="py-8 text-[14px] text-secondary">Aucune mise à jour prévue.</p> : <div className="mt-3 divide-y divide-border">{articles.map((article) => <div key={article.id} className="flex items-center justify-between gap-4 py-4"><div className="min-w-0"><p className="truncate text-[14px] font-medium text-primary">{article.title}</p><p className="mt-1 text-[12px] text-tertiary">Dernière modification : {new Date(article.updated_at).toLocaleDateString('fr-FR')}</p></div><button onClick={() => void sendBack(article.id)} className="shrink-0 rounded-[7px] border-2 border-border px-3 py-2 text-[12px] font-medium text-primary hover:border-primary">Renvoyer en rédaction</button></div>)}</div>}</Card>
  </div>
}
