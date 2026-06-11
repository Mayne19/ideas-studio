import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Save, Sparkles } from 'lucide-react'
import { getProject, updateProject } from '@/api/projects'
import type { Project } from '@/types'
import Input from '@/components/ui/Input'
import Textarea from '@/components/ui/Textarea'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'
import EditorialSetupAssistant from '@/components/editorial/EditorialSetupAssistant'

export default function ProjectStrategyPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [assistantOpen, setAssistantOpen] = useState(false)

  const [form, setForm] = useState({
    audience: '',
    tone: '',
  })

  useEffect(() => {
    if (!projectId) return
    getProject(projectId)
      .then((p) => {
        setProject(p)
        setForm({ audience: p.audience ?? '', tone: p.tone ?? '' })
      })
      .catch(() => setError('Impossible de charger le projet.'))
      .finally(() => setLoading(false))
  }, [projectId])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!projectId || !project) return
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      await updateProject(projectId, { audience: form.audience || undefined, tone: form.tone || undefined })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde.')
    } finally {
      setSaving(false)
    }
  }

  function handleAssistantApplied() {
    if (!projectId) return
    getProject(projectId).then((p) => {
      setForm({ audience: p.audience ?? '', tone: p.tone ?? '' })
    }).catch(() => {})
  }

  if (loading) return <LoadingState />

  return (
    <form onSubmit={handleSave} className="flex flex-col gap-6">
      {error && (
        <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">{error}</div>
      )}

      {/* Assistant button */}
      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          icon={<Sparkles size={13} />}
          onClick={() => setAssistantOpen(true)}
        >
          Assistant de configuration
        </Button>
      </div>

      {assistantOpen && projectId && (
        <EditorialSetupAssistant
          projectId={projectId}
          open={assistantOpen}
          onClose={() => setAssistantOpen(false)}
          onApplied={handleAssistantApplied}
        />
      )}

      {/* Editorial positioning */}
      <div className="rounded-[22px] bg-surface p-5 flex flex-col gap-4">
        <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide">Positionnement éditorial</p>
        <Textarea
          label="Audience cible"
          value={form.audience}
          onChange={(e) => setForm((f) => ({ ...f, audience: e.target.value }))}
          placeholder="Ex : Développeurs web indépendants, 25-40 ans, intéressés par la performance et le SEO technique."
          rows={3}
          hint="Décrit le lecteur idéal de votre blog."
        />
        <Input
          label="Ton éditorial"
          value={form.tone}
          onChange={(e) => setForm((f) => ({ ...f, tone: e.target.value }))}
          placeholder="Ex : Expert mais accessible, pédagogique, sans jargon excessif."
          hint="Style et voix qui caractérisent vos articles."
        />
      </div>



      <div className="flex items-center gap-3">
        <Button type="submit" size="sm" loading={saving} icon={<Save size={13} />}>
          Enregistrer
        </Button>
        {saved && <span className="text-[12px] text-[#1a7a3a]">Sauvegardé ✓</span>}
      </div>
    </form>
  )
}
