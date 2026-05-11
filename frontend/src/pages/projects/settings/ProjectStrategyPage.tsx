import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Save, Info } from 'lucide-react'
import { getProject, updateProject } from '@/api/projects'
import type { Project } from '@/types'
import Input from '@/components/ui/Input'
import Textarea from '@/components/ui/Textarea'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'

export default function ProjectStrategyPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

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

  if (loading) return <LoadingState />

  return (
    <form onSubmit={handleSave} className="flex flex-col gap-6">
      {error && (
        <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">{error}</div>
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

      {/* Planned fields — coming soon */}
      <div className="rounded-[22px] bg-[#fafafa] p-5 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide">Stratégie avancée</p>
          <span className="rounded-full bg-[#f0f0f2] px-2 py-0.5 text-[10px] font-medium text-tertiary">Bientôt</span>
        </div>
        <div className="flex items-start gap-2">
          <Info size={13} className="mt-0.5 shrink-0 text-tertiary" />
          <p className="text-[12px] text-secondary leading-snug">
            Les champs suivants seront disponibles prochainement : concurrents analysés, sujets prioritaires,
            sujets à éviter, objectifs de trafic, fréquence cible de publication.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 opacity-40 pointer-events-none">
          <Input label="Concurrents (séparés par des virgules)" placeholder="blog1.com, blog2.com" disabled />
          <Input label="Sujets prioritaires" placeholder="SEO technique, performances Web, Core Web Vitals" disabled />
          <Input label="Sujets à éviter" placeholder="Politique, actualités hors domaine" disabled />
        </div>
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
