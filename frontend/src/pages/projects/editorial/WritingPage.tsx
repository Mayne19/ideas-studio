import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardTitle } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import { listWritingQueue, type WorkflowArticle } from '@/api/editorialWorkflow'

const labels: Record<NonNullable<WorkflowArticle['status']>, string> = {
  idea: 'En attente', writing: 'En cours', review: 'Terminé', validated: 'Validé', scheduled: 'Programmé', published: 'Publié', update: 'À mettre à jour',
}

export default function WritingPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [jobs, setJobs] = useState<WorkflowArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!projectId) return
    let active = true
    const load = () => listWritingQueue(projectId).then((items) => { if (active) { setJobs(items); setLoading(false) } }).catch((err) => { if (active) { setError(err instanceof Error ? err.message : 'Impossible de charger la rédaction.'); setLoading(false) } })
    void load()
    const timer = window.setInterval(load, 10000)
    return () => { active = false; window.clearInterval(timer) }
  }, [projectId])

  return <div className="mx-auto flex max-w-5xl flex-col gap-6">
    <header><p className="text-[12px] font-medium uppercase tracking-[0.16em] text-tertiary">Parcours éditorial</p><h1 className="mt-2 text-[28px] font-semibold tracking-[-0.03em] text-primary">Rédaction</h1><p className="mt-2 text-[14px] text-secondary">Suivez les sujets transmis au rédacteur local. La rédaction se déroule en arrière-plan.</p></header>
    {error && <p className="rounded-[8px] border-2 border-red-200 px-4 py-3 text-[13px] text-red-700">{error}</p>}
    <Card><CardTitle>File de rédaction</CardTitle>{loading ? <LoadingState label="Chargement de la file…" /> : jobs.length === 0 ? <p className="py-8 text-[14px] text-secondary">Aucun sujet en rédaction.</p> : <div className="mt-3 divide-y divide-border">{jobs.map((job) => <div key={job.id} className="flex items-center justify-between gap-4 py-4"><div className="min-w-0"><p className="truncate text-[14px] font-medium text-primary">{job.title}</p><p className="mt-1 text-[12px] text-tertiary">Dernière activité : {new Date(job.updated_at).toLocaleString('fr-FR')}</p></div><span className="shrink-0 rounded-full bg-surface-soft px-3 py-1.5 text-[12px] font-medium text-secondary">{labels[job.status ?? 'writing']}</span></div>)}</div>}</Card>
  </div>
}
