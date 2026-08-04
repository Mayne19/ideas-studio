import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Globe, FolderOpen, FileText, Lightbulb, AlertCircle, ExternalLink, WifiOff, Trash2 } from '@/components/ui/hugeIcons'
import { listProjects, createProject, deleteProject } from '@/api/projects'
import { listArticles } from '@/api/articles'
import type { CreateProjectPayload } from '@/api/projects'
import type { Project } from '@/types'
import { ArticleStatus, ProjectStatus } from '@/lib/status'
import { formatDate } from '@/utils/format'
import { Card } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'
import Input from '@/components/ui/Input'
import Select from '@/components/ui/Select'
import EmptyState from '@/components/ui/EmptyState'
import ErrorState from '@/components/ui/ErrorState'
import { SkeletonCard } from '@/components/ui/Skeleton'

const LOCALE_OPTIONS = [
  { value: 'fr-FR', label: 'Français' },
  { value: 'en-US', label: 'Anglais' },
  { value: 'es-ES', label: 'Espagnol' },
  { value: 'de-DE', label: 'Allemand' },
  { value: 'pt-PT', label: 'Portugais' },
]

type ProjectStats = {
  published: number
  ideas: number
  review: number
}

function StatPill({ icon, value, label }: { icon: React.ReactNode; value: number; label: string }) {
  if (value === 0) return null
  return (
    <span className="inline-flex items-center gap-1 text-[12px] text-tertiary">
      {icon}
      <span className="font-medium text-secondary">{value}</span>
      <span>{label}</span>
    </span>
  )
}

function ProjectCard({
  project,
  stats,
  onClick,
  onConnect,
  onDelete,
}: {
  project: Project
  stats: ProjectStats | undefined
  onClick: () => void
  onConnect: () => void
  onDelete: () => void
}) {
  const isConnected = project.status === ProjectStatus.CONNECTED
  return (
    <Card className="flex flex-col gap-3 hover:shadow-none transition-shadow duration-200 group">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] bg-accent/10 text-accent text-[15px] font-bold cursor-pointer"
          onClick={onClick}
        >
          {project.name.charAt(0).toUpperCase()}
        </div>
        <div className="flex-1 min-w-0 cursor-pointer" onClick={onClick}>
          <h3 className="text-[15px] font-semibold text-primary truncate group-hover:text-accent transition-colors">
            {project.name}
          </h3>
          <p className="mt-0.5 text-[12px] text-tertiary truncate flex items-center gap-1">
            <Globe size={10} className="shrink-0" />
            {project.domain ?? 'Pas défini'}
          </p>
        </div>
        <button
          onClick={onClick}
          className="shrink-0 flex items-center gap-1 rounded-[8px] bg-accent px-2.5 py-1 text-[12px] font-medium text-white hover:bg-accent/90 transition-colors"
        >
          <ExternalLink size={10} />
          Ouvrir
        </button>
      </div>

      {/* Badges */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${
          isConnected ? 'bg-success/8 text-success' : 'bg-surface-soft text-tertiary'
        }`}>
          <span className={`h-1.5 w-1.5 rounded-full ${isConnected ? 'bg-success' : 'bg-[#c8c8cc]'}`} />
          {isConnected ? 'Connecté' : 'Non connecté'}
        </span>
        {project.locale && (
          <span className="rounded-full bg-surface-soft px-2 py-0.5 text-[10px] text-tertiary uppercase font-medium">
            {project.locale}
          </span>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="flex items-center gap-3 flex-wrap">
          <StatPill icon={<FileText size={10} />} value={stats.published} label="publié{s}" />
          <StatPill icon={<Lightbulb size={10} />} value={stats.ideas} label="idée{s}" />
          <StatPill icon={<AlertCircle size={10} />} value={stats.review} label="à relire" />
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-border">
        <p className="text-[12px] text-tertiary">
          {project.last_seen_at
            ? `Dernière visite ${formatDate(project.last_seen_at)}`
            : isConnected ? 'En attente de trafic' : 'Snippet non installé'}
        </p>
        <div className="flex items-center gap-2">
          {!isConnected && (
            <button
              onClick={(e) => { e.stopPropagation(); onConnect() }}
              className="flex items-center gap-1 text-[12px] text-accent hover:underline"
            >
              <WifiOff size={10} />
              Connecter
            </button>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); onDelete() }}
            className="flex items-center gap-1 text-[12px] text-tertiary hover:text-danger transition-colors"
            title="Supprimer le projet"
          >
            <Trash2 size={10} />
          </button>
        </div>
      </div>
    </Card>
  )
}

type FormState = {
  name: string
  domain: string
  locale: string
  audience: string
  tone: string
}

export default function ProjectsPage() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [projectStats, setProjectStats] = useState<Record<string, ProjectStats>>({})

  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState<FormState>({ name: '', domain: '', locale: 'fr-FR', audience: '', tone: '' })
  const [formError, setFormError] = useState('')
  const [creating, setCreating] = useState(false)

  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  function loadProjects() {
    setStatus('loading')
    listProjects()
      .then((data) => {
        setProjects(data)
        setStatus('success')
        // Fetch stats per project in parallel
        Promise.allSettled(
          data.map((p) =>
            Promise.allSettled([
              listArticles(p.id, { status: ArticleStatus.PUBLISHED, limit: 200 }),
              listArticles(p.id, { status: ArticleStatus.IDEA_PROPOSED, limit: 200 }),
              listArticles(p.id, { status: ArticleStatus.REVIEW_NEEDED, limit: 100 }),
            ]).then(([pub, ideas, review]) => ({
              id: p.id,
              stats: {
                published: pub.status === 'fulfilled' ? pub.value.length : 0,
                ideas: ideas.status === 'fulfilled' ? ideas.value.length : 0,
                review: review.status === 'fulfilled' ? review.value.length : 0,
              },
            }))
          )
        ).then((results) => {
          const map: Record<string, ProjectStats> = {}
          for (const r of results) {
            if (r.status === 'fulfilled') map[r.value.id] = r.value.stats
          }
          setProjectStats(map)
        })
      })
      .catch(() => setStatus('error'))
  }

  useEffect(() => { Promise.resolve().then(() => loadProjects()) }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setFormError('')
    if (!form.name.trim() || !form.domain.trim()) {
      setFormError('Le nom et le domaine sont requis.')
      return
    }
    setCreating(true)
    try {
      const payload: CreateProjectPayload = {
        name: form.name.trim(),
        domain: form.domain.trim(),
        locale: form.locale,
        audience: form.audience.trim() || undefined,
        tone: form.tone.trim() || undefined,
      }
      const project = await createProject(payload)
      setModalOpen(false)
      setForm({ name: '', domain: '', locale: 'fr-FR', audience: '', tone: '' })
      // Redirect to integration (onboarding)
      navigate(`/projects/${project.id}/settings/integration`)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Erreur lors de la création')
    } finally {
      setCreating(false)
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setDeleting(true)
    setDeleteError('')
    try {
      await deleteProject(deleteTarget.id)
      setProjects((prev) => prev.filter((p) => p.id !== deleteTarget.id))
      setDeleteTarget(null)
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Erreur lors de la suppression.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-[22px] font-semibold text-primary tracking-tight">Mes projets</h1>
          <p className="mt-0.5 text-[14px] text-secondary">
            Gérez vos blogs et sites depuis un seul espace.
          </p>
        </div>
        <Button icon={<Plus size={15} />} onClick={() => setModalOpen(true)}>
          Nouveau projet
        </Button>
      </div>

      {status === 'loading' && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}
      {status === 'error' && <ErrorState message="Impossible de charger vos projets." onRetry={loadProjects} />}
      {status === 'success' && projects.length === 0 && (
        <EmptyState
          icon={<FolderOpen size={22} />}
          title="Aucun projet pour l'instant"
          description="Créez votre premier projet pour commencer à gérer votre contenu SEO."
          action={{ label: 'Créer un projet', onClick: () => setModalOpen(true) }}
        />
      )}
      {status === 'success' && projects.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              stats={projectStats[project.id]}
              onClick={() => navigate(`/projects/${project.id}/dashboard`)}
              onConnect={() => navigate(`/projects/${project.id}/settings/integration`)}
              onDelete={() => { setDeleteTarget(project); setDeleteError('') }}
            />
          ))}
        </div>
      )}

      {/* Create project modal */}
      <Modal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setFormError(''); setForm({ name: '', domain: '', locale: 'fr-FR', audience: '', tone: '' }) }}
        title="Nouveau projet"
        size="sm"
      >
        <form onSubmit={handleCreate} className="flex flex-col gap-4">
          {formError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">{formError}</div>
          )}
          <Input
            label="Nom du projet"
            placeholder="Mon blog tech"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            required
            autoFocus
          />
          <Input
            label="Domaine"
            placeholder="monblog.com"
            value={form.domain}
            onChange={(e) => setForm((f) => ({ ...f, domain: e.target.value }))}
            required
            hint="Sans https:// ni chemin"
          />
          <Select
            label="Langue principale"
            options={LOCALE_OPTIONS}
            value={form.locale}
            onChange={(e) => setForm((f) => ({ ...f, locale: e.target.value }))}
          />
          <Input
            label="Audience cible"
            placeholder="Développeurs web freelances"
            value={form.audience}
            onChange={(e) => setForm((f) => ({ ...f, audience: e.target.value }))}
            hint="Optionnel — améliore la génération IA"
          />
          <Input
            label="Ton éditorial"
            placeholder="Professionnel et pédagogique"
            value={form.tone}
            onChange={(e) => setForm((f) => ({ ...f, tone: e.target.value }))}
            hint="Optionnel — style de rédaction souhaité"
          />
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="secondary" className="flex-1 justify-center" onClick={() => setModalOpen(false)}>
              Annuler
            </Button>
            <Button type="submit" loading={creating} className="flex-1 justify-center">
              Créer et configurer →
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete confirmation modal */}
      <Modal
        open={!!deleteTarget}
        onClose={() => { setDeleteTarget(null); setDeleteError('') }}
        title="Supprimer le projet"
        size="sm"
      >
        <div className="flex flex-col gap-4">
          <p className="text-[14px] text-secondary">
            Voulez-vous vraiment supprimer <strong className="text-primary">{deleteTarget?.name}</strong> ?
            Cette action est irréversible — tous les articles, idées et données associés seront perdus.
          </p>
          {deleteError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">{deleteError}</div>
          )}
          <div className="flex gap-2 pt-1">
            <Button type="button" variant="secondary" className="flex-1 justify-center" onClick={() => setDeleteTarget(null)}>
              Annuler
            </Button>
            <Button
              type="button"
              loading={deleting}
              className="flex-1 justify-center bg-danger hover:bg-danger/90 border-danger"
              onClick={handleDeleteConfirm}
            >
              Supprimer définitivement
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
