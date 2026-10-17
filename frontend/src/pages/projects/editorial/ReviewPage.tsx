import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import { getArticle } from '@/api/articles'
import { listWorkflowArticles, validateWorkflowArticle, type WorkflowArticle } from '@/api/editorialWorkflow'
import type { Article } from '@/types'

export default function ReviewPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [articles, setArticles] = useState<WorkflowArticle[]>([])
  const [selected, setSelected] = useState<Article | null>(null)
  const [checks, setChecks] = useState<Array<{ name: string; passed: boolean; detail: string }>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function refresh() {
    if (!projectId) return
    setLoading(true)
    try { setArticles(await listWorkflowArticles(projectId, 'review')); setError('') } catch (err) { setError(err instanceof Error ? err.message : 'Impossible de charger les articles.') } finally { setLoading(false) }
  }
  useEffect(() => { void refresh() }, [projectId])

  async function openArticle(article: WorkflowArticle) {
    if (!projectId) return
    try { setSelected(await getArticle(projectId, article.id)); setChecks([]) } catch (err) { setError(err instanceof Error ? err.message : 'Impossible de charger cet article.') }
  }

  async function validate() {
    if (!projectId || !selected) return
    try { const report = await validateWorkflowArticle(projectId, selected.id); setChecks(report.checks); await refresh() } catch (err) { setError(err instanceof Error ? err.message : 'Validation impossible.') }
  }

  return <div className="mx-auto flex max-w-6xl flex-col gap-6">
    <header><p className="text-[12px] font-medium uppercase tracking-[0.16em] text-tertiary">Parcours éditorial</p><h1 className="mt-2 text-[28px] font-semibold tracking-[-0.03em] text-primary">Relecture et validation</h1><p className="mt-2 text-[14px] text-secondary">Relisez l’article dans sa forme finale avant de le valider.</p></header>
    {error && <p className="rounded-[8px] border-2 border-red-200 px-4 py-3 text-[13px] text-red-700">{error}</p>}
    {loading ? <LoadingState /> : <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
      <Card><CardTitle>À relire</CardTitle><div className="mt-3 divide-y divide-border">{articles.length === 0 ? <p className="py-6 text-[13px] text-secondary">Aucun article à relire.</p> : articles.map((article) => <button key={article.id} onClick={() => void openArticle(article)} className="block w-full py-3 text-left hover:text-accent"><span className="block truncate text-[13px] font-medium text-primary">{article.title}</span><span className="mt-1 block text-[11px] text-tertiary">{new Date(article.updated_at).toLocaleDateString('fr-FR')}</span></button>)}</div></Card>
      <Card>{selected ? <><div className="flex items-start justify-between gap-4"><div><CardTitle>{selected.title}</CardTitle><p className="mt-1 text-[12px] text-tertiary">/{selected.slug}</p></div><button onClick={() => void validate()} className="rounded-[7px] bg-primary px-3 py-2 text-[12px] font-medium text-white">Valider</button></div><article className="prose prose-sm mt-6 max-w-none text-primary" dangerouslySetInnerHTML={{ __html: selected.content ?? '<p>Aucun contenu.</p>' }} />{checks.length > 0 && <div className="mt-6 border-t-2 border-border pt-4"><p className="text-[13px] font-semibold text-primary">Contrôles techniques</p>{checks.map((check) => <p key={check.name} className={`mt-2 text-[12px] ${check.passed ? 'text-emerald-700' : 'text-red-700'}`}>{check.passed ? '✓' : '×'} {check.detail}</p>)}</div>}</> : <p className="py-12 text-center text-[14px] text-secondary">Sélectionnez un article pour commencer la relecture.</p>}</Card>
    </div>}
  </div>
}
