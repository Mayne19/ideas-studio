import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { AlertTriangle, CheckCircle, Edit3, RefreshCw, X, XCircle } from '@/components/ui/hugeIcons'
import { deleteIdea, generateMonthlyPlan } from '@/api/ideas'
import { patchArticle } from '@/api/articles'
import { getPipelineSettings } from '@/api/pipeline'
import type { PipelineSettings } from '@/api/pipeline'
import {
  listProductionArticles,
  listProductionUpdates,
  listProductionWritingQueue,
  rejectProductionArticle,
  requestProductionWriting,
  returnProductionToWriting,
  validateProductionArticle,
  type ProductionArticle,
  type ProductionCheck,
} from '@/api/production'
import { Card } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'

type Tab = 'ideas' | 'writing' | 'review' | 'updates'
const TABS: Array<{ key: Tab; label: string }> = [
  { key: 'ideas', label: 'Idées' }, { key: 'writing', label: 'Rédaction' },
  { key: 'review', label: 'Validation' }, { key: 'updates', label: 'Mises à jour' },
]
const STATUS_LABELS: Record<string, string> = { idea: 'En attente', writing: 'En cours', review: 'Terminé', error: 'Erreur' }

function ErrorMessage({ message }: { message: string }) {
  return <p className="rounded-[10px] border border-danger/20 bg-danger/5 px-3 py-2 text-[12px] text-danger">{message}</p>
}

function TabButton({ tab, active, count, onClick }: { tab: typeof TABS[number]; active: boolean; count: number; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`border-b-2 px-4 py-3 text-[13px] font-medium transition-colors ${active ? 'border-accent text-accent' : 'border-transparent text-secondary hover:text-primary'}`}>{tab.label}{count > 0 && <span className="ml-2 rounded-full bg-surface-soft px-1.5 py-0.5 text-[11px] text-tertiary">{count}</span>}</button>
}

function CheckIcon({ check }: { check?: ProductionCheck }) {
  if (!check) return <span className="text-tertiary">?</span>
  return check.passed ? <CheckCircle size={15} className="text-success" /> : <XCircle size={15} className="text-danger" />
}

function IdeasTab({ projectId, onRefresh }: { projectId: string; onRefresh: () => void }) {
  const [ideas, setIdeas] = useState<ProductionArticle[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const load = useCallback(() => { setLoading(true); listProductionArticles(projectId, 'idea').then(setIdeas).catch(() => setError('Impossible de charger les idées.')).finally(() => setLoading(false)) }, [projectId])
  useEffect(() => { load() }, [load])
  const grouped = useMemo(() => {
    const groups = new Map<string, ProductionArticle[]>()
    ideas.forEach((idea) => { const key = idea.category_name || 'Sans catégorie'; groups.set(key, [...(groups.get(key) || []), idea]) })
    return [...groups.entries()]
  }, [ideas])
  async function accept(items: ProductionArticle[]) {
    setBusy('accept')
    try { await Promise.all(items.map((idea) => requestProductionWriting(projectId, idea.id))); setMessage(`${items.length} idée(s) envoyée(s) en rédaction.`); setSelected(new Set()); load(); onRefresh() } catch { setError('Impossible d’envoyer les idées en rédaction.') } finally { setBusy(null) }
  }
  async function reject(idea: ProductionArticle) {
    setBusy(idea.id)
    try { await deleteIdea(projectId, idea.id); load(); onRefresh() } catch { setError('Impossible de supprimer cette idée.') } finally { setBusy(null) }
  }
  async function editTitle(idea: ProductionArticle) {
    const title = window.prompt('Nouveau titre', idea.title)?.trim()
    if (!title || title === idea.title) return
    setBusy(idea.id)
    try { await patchArticle(projectId, idea.id, { title }); load() } catch { setError('Impossible de modifier le titre.') } finally { setBusy(null) }
  }
  if (loading) return <LoadingState />
  return <div className="flex flex-col gap-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-[16px] font-semibold text-primary">Idées du mois</h2><p className="text-[12px] text-secondary">Chaque idée acceptée entre directement dans la file de rédaction.</p></div><div className="flex gap-2"><Button size="sm" variant="ghost" onClick={() => { load(); setMessage('') }} icon={<RefreshCw size={13} />}>Actualiser</Button><Button size="sm" onClick={() => void accept(ideas)} disabled={!ideas.length || busy !== null} loading={busy === 'accept'}>Tout accepter</Button><Button size="sm" variant="secondary" onClick={() => void accept(ideas.filter((idea) => selected.has(idea.id)))} disabled={!selected.size || busy !== null}>Accepter la sélection</Button></div></div>
    {message && <p className="text-[12px] text-success">{message}</p>}{error && <ErrorMessage message={error} />}
    {grouped.length === 0 ? <Card padding="lg"><p className="text-[13px] text-tertiary">Aucune idée en attente.</p></Card> : grouped.map(([category, items]) => <Card key={category} padding="sm"><h3 className="mb-2 text-[13px] font-semibold text-primary">{category}</h3><div className="divide-y divide-border">{items.map((idea) => <div key={idea.id} className="flex items-center gap-3 py-2.5"><input type="checkbox" checked={selected.has(idea.id)} onChange={(event) => setSelected((current) => { const next = new Set(current); event.target.checked ? next.add(idea.id) : next.delete(idea.id); return next })} /><div className="min-w-0 flex-1"><p className="truncate text-[13px] font-medium text-primary">{idea.title}</p><p className="text-[11px] text-tertiary">{idea.keyword || 'Mot-clé non renseigné'}</p></div>{idea.duplicate && <span className="flex items-center gap-1 text-[11px] text-warning"><AlertTriangle size={13} /> Doublon</span>}<button type="button" onClick={() => void editTitle(idea)} disabled={busy !== null} className="rounded p-1.5 text-tertiary hover:bg-surface-soft hover:text-primary" title="Modifier le titre"><Edit3 size={14} /></button><button type="button" onClick={() => void reject(idea)} disabled={busy !== null} className="rounded p-1.5 text-tertiary hover:bg-danger/5 hover:text-danger" title="Rejeter et supprimer"><X size={14} /></button><Button size="sm" variant="secondary" onClick={() => void accept([idea])} disabled={busy !== null} loading={busy === 'accept'}>Accepter</Button></div>)}</div></Card>)}
  </div>
}

function nextWorkingDate(total: number, perDay: number, days: number[]) {
  if (!total || !perDay) return '—'
  const allowed = new Set(days.length ? days : [0, 1, 2, 3, 4])
  const cursor = new Date(); let done = 0
  while (done < total) { cursor.setDate(cursor.getDate() + 1); if (allowed.has((cursor.getDay() + 6) % 7)) done += perDay }
  return cursor.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

function WritingTab({ projectId }: { projectId: string }) {
  const [queue, setQueue] = useState<ProductionArticle[]>([])
  const [settings, setSettings] = useState<PipelineSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = useCallback(() => Promise.all([listProductionWritingQueue(projectId), getPipelineSettings(projectId)]).then(([items, pipeline]) => { setQueue(items); setSettings(pipeline) }).catch(() => setError('Impossible de charger la file de rédaction.')).finally(() => setLoading(false)), [projectId])
  useEffect(() => { void load() }, [load])
  if (loading) return <LoadingState />
  const perDay = settings?.articles_per_day ?? 2; const days = settings?.writing_days ?? [0, 1, 2, 3, 4]; const totalCost = queue.reduce((sum, item) => sum + (item.cost_usd || 0), 0)
  return <div className="flex flex-col gap-4"><div><h2 className="text-[16px] font-semibold text-primary">File de rédaction</h2><p className="mt-1 text-[12px] text-secondary">{perDay} article(s) par jour · {days.length ? days.map((day) => ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.'][day]).join(', ') : 'aucun jour'} · file vide le {nextWorkingDate(queue.length, perDay, days)}</p></div>{error && <ErrorMessage message={error} />}<div className="flex gap-3 text-[11px] text-tertiary"><span>{queue.filter((item) => item.status === 'idea').length} en attente</span><span>{queue.filter((item) => item.status === 'writing').length} en cours</span><span>{queue.filter((item) => item.status === 'review').length} terminé(s)</span><span>{queue.filter((item) => item.status === 'error').length} erreur(s)</span>{totalCost > 0 && <span>Coût du mois : {totalCost.toFixed(2)} $</span>}</div><Card padding="sm"><div className="divide-y divide-border">{queue.length === 0 ? <p className="py-2 text-[13px] text-tertiary">Aucun article dans la file.</p> : queue.map((item) => <div key={item.id} className="flex items-center gap-3 py-3"><div className="min-w-0 flex-1"><p className="truncate text-[13px] font-medium text-primary">{item.title}</p><p className="text-[11px] text-tertiary">{item.category_name || 'Sans catégorie'}{item.planned_write_at ? ` · prévu le ${new Date(item.planned_write_at).toLocaleDateString('fr-FR')}` : ''}</p></div><span className={`text-[11px] ${item.status === 'error' ? 'text-danger' : 'text-secondary'}`}>{STATUS_LABELS[item.status || 'idea'] || item.status}</span>{item.cost_usd != null && <span className="text-[11px] text-tertiary">{item.cost_usd.toFixed(2)} $</span>}{item.status === 'error' && <Button size="sm" variant="secondary" onClick={() => void requestProductionWriting(projectId, item.id).then(load)}>Relancer</Button>}</div>)}</div></Card></div>
}

function ReviewTab({ projectId, threshold }: { projectId: string; threshold: number }) {
  const navigate = useNavigate(); const [items, setItems] = useState<ProductionArticle[]>([]); const [selected, setSelected] = useState<Set<string>>(new Set()); const [loading, setLoading] = useState(true); const [busy, setBusy] = useState<string | null>(null); const [error, setError] = useState('')
  const load = useCallback(() => { setLoading(true); listProductionArticles(projectId, 'review').then(setItems).catch(() => setError('Impossible de charger les articles à valider.')).finally(() => setLoading(false)) }, [projectId]); useEffect(() => { load() }, [load])
  async function validate(ids: string[]) { setBusy('validate'); try { await Promise.all(ids.map((id) => validateProductionArticle(projectId, id))); setSelected(new Set()); load() } catch { setError('Un ou plusieurs articles ne peuvent pas être validés.') } finally { setBusy(null) } }
  async function sendBack(item: ProductionArticle) { const comment = window.prompt('Commentaire pour la rédaction', '') ?? ''; setBusy(item.id); try { await returnProductionToWriting(projectId, item.id, comment); load() } catch { setError('Impossible de renvoyer l’article.') } finally { setBusy(null) } }
  async function reject(item: ProductionArticle) { setBusy(item.id); try { await rejectProductionArticle(projectId, item.id); load() } catch { setError('Impossible de rejeter l’article.') } finally { setBusy(null) } }
  if (loading) return <LoadingState />
  const eligible = items.filter((item) => (item.score ?? 0) >= threshold && item.checks.every((check) => check.passed))
  return <div className="flex flex-col gap-4"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-[16px] font-semibold text-primary">Articles à valider</h2><p className="mt-1 text-[12px] text-secondary">Seuls les articles au-dessus de {threshold}/100 et sans contrôle bloquant peuvent être programmés.</p></div><div className="flex gap-2"><Button size="sm" onClick={() => void validate(eligible.map((item) => item.id))} disabled={!eligible.length || busy !== null} loading={busy === 'validate'}>Valider tous les articles au-dessus du seuil</Button><Button size="sm" variant="secondary" onClick={() => void validate([...selected])} disabled={!selected.size || busy !== null}>Valider la sélection</Button></div></div>{error && <ErrorMessage message={error} />}<Card padding="sm"><div className="divide-y divide-border">{items.length === 0 ? <p className="py-2 text-[13px] text-tertiary">Aucun article à relire.</p> : items.map((item) => <div key={item.id} className="flex cursor-pointer items-center gap-3 py-3" onClick={() => navigate(`/projects/${projectId}/articles/${item.id}/edit?from=production`)}><input type="checkbox" checked={selected.has(item.id)} onClick={(event) => event.stopPropagation()} onChange={(event) => setSelected((current) => { const next = new Set(current); event.target.checked ? next.add(item.id) : next.delete(item.id); return next })} /><div className="min-w-0 flex-1"><p className="truncate text-[13px] font-medium text-primary">{item.title}</p><p className="text-[11px] text-tertiary">{item.category_name || 'Sans catégorie'}</p></div><span className="text-[14px] font-semibold text-primary">{item.score ?? '—'}</span><div className="flex items-center gap-1" title="Contrôles techniques">{item.checks.map((check) => <CheckIcon key={check.name} check={check} />)}</div>{item.alerts.map((alert) => <span key={alert} className="flex items-center gap-1 text-[11px] text-warning"><AlertTriangle size={13} />{alert}</span>)}<button type="button" onClick={(event) => { event.stopPropagation(); void sendBack(item) }} className="rounded p-1.5 text-tertiary hover:text-primary" title="Renvoyer en rédaction"><RefreshCw size={14} /></button><button type="button" onClick={(event) => { event.stopPropagation(); void reject(item) }} className="rounded p-1.5 text-tertiary hover:text-danger" title="Rejeter"><X size={14} /></button></div>)}</div></Card></div>
}

function UpdatesTab({ projectId }: { projectId: string }) {
  const [items, setItems] = useState<ProductionArticle[]>([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const load = useCallback(() => { setLoading(true); listProductionUpdates(projectId).then(setItems).catch(() => setError('Impossible de charger les mises à jour.')).finally(() => setLoading(false)) }, [projectId]); useEffect(() => { load() }, [load]); if (loading) return <LoadingState />
  return <div className="flex flex-col gap-4"><div><h2 className="text-[16px] font-semibold text-primary">Informations à mettre à jour</h2><p className="mt-1 text-[12px] text-secondary">Les informations variables restent attachées à la fiche de publication.</p></div>{error && <ErrorMessage message={error} />}<Card padding="sm"><div className="divide-y divide-border">{items.length === 0 ? <p className="py-2 text-[13px] text-tertiary">Aucune mise à jour prévue.</p> : items.flatMap((item) => { const rows = Array.isArray(item.fiche?.a_mettre_a_jour) ? item.fiche?.a_mettre_a_jour as Array<Record<string, unknown>> : []; return rows.length ? rows.map((row, index) => <div key={`${item.id}-${index}`} className="flex items-center gap-3 py-3"><div className="min-w-0 flex-1"><p className="text-[13px] font-medium text-primary">{String(row.information || 'Information à vérifier')}</p><p className="text-[11px] text-tertiary">{item.title} · {String(row.source || 'Source non renseignée')}</p></div><span className="text-[11px] text-secondary">{String(row.a_verifier || 'À planifier')}</span><Button size="sm" variant="secondary" onClick={() => void requestProductionWriting(projectId, item.id).then(load)}>Renvoyer en rédaction</Button></div>) : [<div key={item.id} className="flex items-center gap-3 py-3"><div className="min-w-0 flex-1"><p className="text-[13px] font-medium text-primary">{item.title}</p><p className="text-[11px] text-tertiary">Fiche sans détail d’échéance.</p></div><Button size="sm" variant="secondary" onClick={() => void requestProductionWriting(projectId, item.id).then(load)}>Renvoyer en rédaction</Button></div>] })}</div></Card></div>
}

export default function PipelinePage() {
  const { projectId } = useParams<{ projectId: string }>(); const [params, setParams] = useSearchParams(); const [pipeline, setPipeline] = useState<PipelineSettings | null>(null); const [counts, setCounts] = useState<Record<Tab, number>>({ ideas: 0, writing: 0, review: 0, updates: 0 }); const [message, setMessage] = useState(''); const [generating, setGenerating] = useState(false); const [error, setError] = useState('')
  const tabParam = params.get('tab'); const activeTab: Tab = tabParam === 'validate' ? 'review' : TABS.some((item) => item.key === tabParam) ? tabParam as Tab : 'ideas'
  const loadCounts = useCallback(async () => { if (!projectId) return; try { const [ideas, writing, review, updates, settings] = await Promise.all([listProductionArticles(projectId, 'idea'), listProductionWritingQueue(projectId), listProductionArticles(projectId, 'review'), listProductionUpdates(projectId), getPipelineSettings(projectId)]); setCounts({ ideas: ideas.length, writing: writing.length, review: review.length, updates: updates.length }); setPipeline(settings) } catch { setError('Impossible de charger la production.') } }, [projectId]); useEffect(() => { void loadCounts() }, [loadCounts])
  if (!projectId) return <ErrorState message="Projet introuvable." />
  const activeProjectId = projectId
  async function generateIdeas() { setGenerating(true); setMessage(''); try { const result = await generateMonthlyPlan(activeProjectId, true); setMessage(`${result.ideas_generated || 0} idée(s) générée(s).`); await loadCounts() } catch { setMessage('La génération des idées a échoué.') } finally { setGenerating(false) } }
  return <div className="mx-auto flex max-w-6xl flex-col gap-5 p-1"><div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-[11px] font-medium uppercase tracking-[0.16em] text-tertiary">Parcours éditorial</p><h1 className="mt-1 text-[25px] font-semibold tracking-[-0.03em] text-primary">Production</h1><p className="mt-1 text-[13px] text-secondary">Les idées, la rédaction, la validation et les mises à jour dans un seul espace.</p></div>{activeTab === 'ideas' && <Button size="sm" onClick={() => void generateIdeas()} loading={generating}>Générer les idées du mois</Button>}</div>{message && <p className="text-[12px] text-secondary">{message}</p>}{error && <ErrorMessage message={error} />}<div className="flex border-b border-border">{TABS.map((tab) => <TabButton key={tab.key} tab={tab} active={activeTab === tab.key} count={counts[tab.key]} onClick={() => setParams({ tab: tab.key })} />)}</div>{activeTab === 'ideas' && <IdeasTab projectId={projectId} onRefresh={() => void loadCounts()} />}{activeTab === 'writing' && <WritingTab projectId={projectId} />}{activeTab === 'review' && <ReviewTab projectId={projectId} threshold={pipeline?.min_publish_score ?? 90} />}{activeTab === 'updates' && <UpdatesTab projectId={projectId} />}</div>
}
