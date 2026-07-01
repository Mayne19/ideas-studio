import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Save, Sparkles } from '@/components/ui/hugeIcons'
import { getProject, updateProject } from '@/api/projects'
import type { Project } from '@/types'
import Textarea from '@/components/ui/Textarea'
import Select from '@/components/ui/Select'
import Button from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import LoadingState from '@/components/ui/LoadingState'
import EditorialSetupAssistant from '@/components/editorial/EditorialSetupAssistant'

const TONE_OPTIONS = [
  { value: '', label: 'Non défini' },
  { value: 'Professionnel clair', label: 'Professionnel clair' },
  { value: 'Expert accessible', label: 'Expert accessible' },
  { value: 'Pédagogique', label: 'Pédagogique' },
  { value: 'Direct et opérationnel', label: 'Direct et opérationnel' },
  { value: 'Éditorial premium', label: 'Éditorial premium' },
]

const READER_LEVEL_OPTIONS = [
  { value: '', label: 'Non défini' },
  { value: 'Découverte', label: 'Découverte' },
  { value: 'Pratique', label: 'Pratique' },
  { value: 'Intermédiaire', label: 'Intermédiaire' },
  { value: 'Expert opérationnel', label: 'Expert opérationnel' },
  { value: 'Décideur', label: 'Décideur' },
]

const WRITING_STYLE_OPTIONS = [
  { value: '', label: 'Non défini' },
  { value: 'Guide pratique', label: 'Guide pratique' },
  { value: 'Analyse experte', label: 'Analyse experte' },
  { value: 'Comparatif structuré', label: 'Comparatif structuré' },
  { value: 'Tutoriel étape par étape', label: 'Tutoriel étape par étape' },
  { value: 'Article éditorial', label: 'Article éditorial' },
]

const LENGTH_OPTIONS = [
  { value: '', label: 'Adaptatif' },
  { value: '600-900 mots', label: '600-900 mots' },
  { value: '900-1200 mots', label: '900-1200 mots' },
  { value: '1200-1600 mots', label: '1200-1600 mots' },
  { value: '1600-2200 mots', label: '1600-2200 mots' },
  { value: '2200+ mots si la SERP le justifie', label: '2200+ mots si la SERP le justifie' },
]

const TECHNICAL_LEVEL_OPTIONS = [
  { value: '', label: 'Non défini' },
  { value: 'Accessible sans prérequis', label: 'Accessible sans prérequis' },
  { value: 'Exemples concrets modérés', label: 'Exemples concrets modérés' },
  { value: 'Technique assumé', label: 'Technique assumé' },
  { value: 'Expert avec détails avancés', label: 'Expert avec détails avancés' },
]

type StrategyForm = {
  audience: string
  tone: string
  reader_level: string
  writing_style: string
  editorial_goal: string
  value_proposition: string
  allowed_topics: string
  forbidden_topics: string
  words_to_avoid: string
  average_target_length: string
  preferred_formats: string
  technical_level: string
  seo_rules: string
  geo_rules: string
  source_guidelines: string
  internal_linking_guidelines: string
  external_linking_guidelines: string
  style_examples: string
}

export default function ProjectStrategyPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [assistantOpen, setAssistantOpen] = useState(false)

  const [form, setForm] = useState<StrategyForm>({
    audience: '',
    tone: '',
    reader_level: '',
    writing_style: '',
    editorial_goal: '',
    value_proposition: '',
    allowed_topics: '',
    forbidden_topics: '',
    words_to_avoid: '',
    average_target_length: '',
    preferred_formats: '',
    technical_level: '',
    seo_rules: '',
    geo_rules: '',
    source_guidelines: '',
    internal_linking_guidelines: '',
    external_linking_guidelines: '',
    style_examples: '',
  })

  useEffect(() => {
    if (!projectId) return
    getProject(projectId)
      .then((p) => {
        setProject(p)
        setForm({
          audience: p.audience ?? '',
          tone: p.tone ?? '',
          reader_level: p.reader_level ?? '',
          writing_style: p.writing_style ?? '',
          editorial_goal: p.editorial_goal ?? '',
          value_proposition: p.value_proposition ?? '',
          allowed_topics: p.allowed_topics ?? '',
          forbidden_topics: p.forbidden_topics ?? '',
          words_to_avoid: p.words_to_avoid ?? '',
          average_target_length: p.average_target_length ?? '',
          preferred_formats: p.preferred_formats ?? '',
          technical_level: p.technical_level ?? '',
          seo_rules: p.seo_rules ?? '',
          geo_rules: p.geo_rules ?? '',
          source_guidelines: p.source_guidelines ?? '',
          internal_linking_guidelines: p.internal_linking_guidelines ?? '',
          external_linking_guidelines: p.external_linking_guidelines ?? '',
          style_examples: p.style_examples ?? '',
        })
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
      await updateProject(projectId, Object.fromEntries(
        Object.entries(form).map(([key, value]) => [key, value.trim() || undefined]),
      ))
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
      setForm((current) => ({
        ...current,
        audience: p.audience ?? '',
        tone: p.tone ?? '',
      }))
    }).catch(() => {})
  }

  if (loading) return <LoadingState />

  return (
    <form onSubmit={handleSave} className="flex flex-col gap-6">
      {error && (
        <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">{error}</div>
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
      <Card className="flex flex-col gap-4">
        <p className="text-[12px] font-semibold text-secondary uppercase tracking-wide">Positionnement éditorial</p>
        <Textarea
          label="Audience cible"
          value={form.audience}
          onChange={(e) => setForm((f) => ({ ...f, audience: e.target.value }))}
          placeholder="Ex : Développeurs web indépendants, 25-40 ans, intéressés par la performance et le SEO technique."
          rows={3}
          hint="Décrit le lecteur idéal de votre blog."
        />
        <Select
          label="Ton éditorial"
          options={TONE_OPTIONS}
          value={form.tone}
          onChange={(e) => setForm((f) => ({ ...f, tone: e.target.value }))}
          hint="Style et voix qui caractérisent vos articles."
        />
        <div className="grid gap-4 md:grid-cols-3">
          <Select
            label="Niveau du lecteur"
            options={READER_LEVEL_OPTIONS}
            value={form.reader_level}
            onChange={(e) => setForm((f) => ({ ...f, reader_level: e.target.value }))}
          />
          <Select
            label="Style d’écriture"
            options={WRITING_STYLE_OPTIONS}
            value={form.writing_style}
            onChange={(e) => setForm((f) => ({ ...f, writing_style: e.target.value }))}
          />
          <Select
            label="Longueur moyenne cible"
            options={LENGTH_OPTIONS}
            value={form.average_target_length}
            onChange={(e) => setForm((f) => ({ ...f, average_target_length: e.target.value }))}
          />
        </div>
          <Select
            label="Niveau de technicité"
            options={TECHNICAL_LEVEL_OPTIONS}
            value={form.technical_level}
            onChange={(e) => setForm((f) => ({ ...f, technical_level: e.target.value }))}
            hint="Ces paramètres sont transmis au contexte de génération et contraignent le brief rédactionnel."
          />
        </Card>

      <div className="flex items-center gap-3">
        <Button type="submit" size="sm" loading={saving} icon={<Save size={13} />}>
          Enregistrer
        </Button>
        {saved && <span className="text-[12px] text-[#1a7a3a]">Sauvegardé ✓</span>}
      </div>
    </form>
  )
}
