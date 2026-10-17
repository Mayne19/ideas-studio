import { useEffect, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import { createArticle } from '@/api/articles'
import { listWorkflowArticles, requestWorkflowWriting, type WorkflowArticle } from '@/api/editorialWorkflow'

export default function IdeasPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [ideas, setIdeas] = useState<WorkflowArticle[]>([])
  const [title, setTitle] = useState('')
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function refresh() {
    if (!projectId) return
    setLoading(true)
    try {
      setIdeas(await listWorkflowArticles(projectId, 'idea'))
      setError('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger les idées.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refresh() }, [projectId])

  async function addIdea(event: FormEvent) {
    event.preventDefault()
    if (!projectId || !title.trim()) return
    setSaving(true)
    try {
      await createArticle(projectId, { title: title.trim(), keyword: keyword.trim() || undefined })
      setTitle('')
      setKeyword('')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de créer le sujet.')
    } finally {
      setSaving(false)
    }
  }

  async function sendToWriting(articleId: string) {
    if (!projectId) return
    try {
      await requestWorkflowWriting(projectId, articleId)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible d’envoyer le sujet.')
    }
  }

  if (!projectId) return <LoadingState />

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <header>
        <p className="text-[12px] font-medium uppercase tracking-[0.16em] text-tertiary">Parcours éditorial</p>
        <h1 className="mt-2 text-[28px] font-semibold tracking-[-0.03em] text-primary">Idées</h1>
        <p className="mt-2 text-[14px] text-secondary">Gardez les sujets utiles au même endroit, puis envoyez-les en rédaction quand ils sont prêts.</p>
      </header>

      <Card>
        <CardTitle>Ajouter un sujet</CardTitle>
        <form onSubmit={addIdea} className="mt-4 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Titre ou sujet" className="h-10 rounded-[8px] border-2 border-border bg-transparent px-3 text-[14px] text-primary outline-none focus:border-accent" />
          <input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="Mot-clé (facultatif)" className="h-10 rounded-[8px] border-2 border-border bg-transparent px-3 text-[14px] text-primary outline-none focus:border-accent" />
          <button disabled={saving || !title.trim()} className="h-10 rounded-[8px] bg-primary px-4 text-[14px] font-medium text-white disabled:opacity-40">{saving ? 'Ajout…' : 'Ajouter'}</button>
        </form>
      </Card>

      {error && <p className="rounded-[8px] border-2 border-red-200 px-4 py-3 text-[13px] text-red-700">{error}</p>}
      <Card>
        <CardTitle>Sujets disponibles</CardTitle>
        {loading ? <LoadingState label="Chargement des idées…" /> : ideas.length === 0 ? <p className="py-8 text-[14px] text-secondary">Aucun sujet en attente.</p> : (
          <div className="mt-3 divide-y divide-border">
            {ideas.map((idea) => <div key={idea.id} className="flex items-center justify-between gap-4 py-4">
              <div className="min-w-0"><p className="truncate text-[14px] font-medium text-primary">{idea.title}</p><p className="mt-1 text-[12px] text-tertiary">Mis à jour le {new Date(idea.updated_at).toLocaleDateString('fr-FR')}</p></div>
              <button onClick={() => void sendToWriting(idea.id)} className="shrink-0 rounded-[7px] border-2 border-border px-3 py-2 text-[12px] font-medium text-primary hover:border-primary">Envoyer en rédaction</button>
            </div>)}
          </div>
        )}
      </Card>
    </div>
  )
}
