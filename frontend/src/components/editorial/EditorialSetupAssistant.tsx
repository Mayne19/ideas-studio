import { useState } from 'react'
import { Sparkles, Check, Loader2, AlertCircle, Wand2, Info } from '@/components/ui/hugeIcons'
import { suggestEditorialSetup, updateProject } from '@/api/projects'
import type { EditorialSuggestion } from '@/api/projects'
import Modal from '@/components/ui/Modal'
import Button from '@/components/ui/Button'
import Textarea from '@/components/ui/Textarea'
import Input from '@/components/ui/Input'

type Props = {
  projectId: string
  open: boolean
  onClose: () => void
  onApplied: () => void
}

export default function EditorialSetupAssistant({ projectId, open, onClose, onApplied }: Props) {
  const [step, setStep] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [source, setSource] = useState<'llm' | 'default'>('default')
  const [error, setError] = useState('')
  const [applying, setApplying] = useState(false)
  const [applied, setApplied] = useState(false)

  const [form, setForm] = useState<EditorialSuggestion>({
    description: '',
    audience: '',
    tone: '',
    positioning: '',
    main_keywords: [],
    recommended_categories: [],
    seo_writing_guidelines: '',
  })

  async function handleGenerate() {
    setStep('loading')
    setError('')
    try {
      const res = await suggestEditorialSetup(projectId)
      setForm(res.suggestion)
      setSource(res.source)
      setStep('done')
    } catch (err) {
      setStep('error')
      setError(err instanceof Error ? err.message : 'Erreur lors de la génération.')
    }
  }

  async function handleApply() {
    setApplying(true)
    setError('')
    try {
      await updateProject(projectId, {
        audience: form.audience || undefined,
        tone: form.tone || undefined,
      })
      setApplied(true)
      setTimeout(() => {
        onApplied()
        onClose()
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde.')
    } finally {
      setApplying(false)
    }
  }

  function handleClose() {
    setStep('idle')
    setApplied(false)
    setError('')
    onClose()
  }

  const keywordsStr = form.main_keywords.join(', ')

  return (
    <Modal open={open} onClose={handleClose} title="Assistant de configuration éditoriale" size="lg">
      <div className="flex flex-col gap-4">
        {error && (
          <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger flex items-start gap-2">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {step === 'idle' && (
          <div className="flex flex-col gap-4">
            <div className="rounded-[16px] bg-[#f9f9fb] p-5 flex flex-col items-center gap-3 text-center">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/10 text-accent">
                <Wand2 size={22} />
              </span>
              <p className="text-[14px] font-medium text-primary">
                Analyse automatique de votre projet
              </p>
              <p className="text-[13px] text-secondary leading-relaxed max-w-sm">
                L'assistant va analyser votre site connecté, les catégories existantes et
                les données de votre projet pour vous proposer une configuration éditoriale
                complète. Rien ne sera sauvegardé sans votre validation.
              </p>
            </div>
            <Button onClick={handleGenerate} icon={<Sparkles size={14} />} className="w-full justify-center">
              Lancer l'analyse
            </Button>
          </div>
        )}

        {step === 'loading' && (
          <div className="flex flex-col items-center gap-3 py-8">
            <Loader2 size={28} className="animate-spin text-accent" />
            <p className="text-[14px] font-medium text-primary">Analyse en cours…</p>
            <p className="text-[12px] text-secondary">
              Consultation du site, des catégories et génération des suggestions.
            </p>
          </div>
        )}

        {step === 'done' && (
          <div className="flex flex-col gap-4 max-h-[60vh] overflow-y-auto pr-1">
            {source === 'llm' ? (
              <div className="flex items-center gap-2 rounded-[10px] bg-accent/8 px-3.5 py-2.5 text-[12px] text-accent font-medium">
                <Sparkles size={13} />
                Suggéré par l'intelligence artificielle
              </div>
            ) : (
              <div className="flex items-center gap-2 rounded-[10px] bg-[#f0f0f2] px-3.5 py-2.5 text-[12px] text-secondary font-medium">
                <Info size={13} />
                Suggestions basées sur l'analyse du site
              </div>
            )}

            {/* Sources */}
            <details className="rounded-[12px] border border-border bg-[#f9f9fb] px-3 py-2.5">
              <summary className="cursor-pointer text-[12px] font-medium text-secondary hover:text-primary">
                Sources utilisées
              </summary>
              <ul className="mt-2 flex flex-col gap-1.5 pl-1 text-[11px] text-tertiary">
                <li className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-success" />
                  Domaine du projet
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-success" />
                  Catégories synchronisées
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-warning" />
                  Articles publiés — disponibles
                </li>
                <li className="flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-warning" />
                  Données publiques accessibles — partiellement disponibles
                </li>
              </ul>
              {source === 'default' && (
                <p className="mt-2 text-[11px] text-warning">
                  Proposition basée sur des données limitées.
                </p>
              )}
            </details>

            <Textarea
              label="Description du site"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
              rows={3}
            />
            <Textarea
              label="Audience cible"
              value={form.audience}
              onChange={(e) => setForm((f) => ({ ...f, audience: e.target.value }))}
              rows={3}
            />
            <Input
              label="Ton éditorial"
              value={form.tone}
              onChange={(e) => setForm((f) => ({ ...f, tone: e.target.value }))}
            />
            <Textarea
              label="Positionnement"
              value={form.positioning}
              onChange={(e) => setForm((f) => ({ ...f, positioning: e.target.value }))}
              rows={2}
            />
            <Input
              label="Mots-clés principaux"
              value={keywordsStr}
              onChange={(e) => setForm((f) => ({ ...f, main_keywords: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) }))}
              hint="Séparés par des virgules"
            />
            <Input
              label="Catégories recommandées"
              value={form.recommended_categories.join(', ')}
              onChange={(e) => setForm((f) => ({ ...f, recommended_categories: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) }))}
              hint="Séparées par des virgules"
            />
            <Textarea
              label="Consignes de rédaction SEO"
              value={form.seo_writing_guidelines}
              onChange={(e) => setForm((f) => ({ ...f, seo_writing_guidelines: e.target.value }))}
              rows={4}
            />

            <div className="flex gap-2 pt-2">
              <Button variant="secondary" onClick={handleClose} className="flex-1 justify-center">
                Annuler
              </Button>
              <Button
                onClick={handleApply}
                loading={applying}
                icon={applied ? <Check size={14} /> : undefined}
                className="flex-1 justify-center"
              >
                {applied ? 'Appliqué !' : 'Appliquer la configuration'}
              </Button>
            </div>
          </div>
        )}

        {step === 'error' && (
          <div className="flex flex-col gap-3">
            <Button onClick={handleGenerate} variant="secondary" className="w-full justify-center">
              Réessayer
            </Button>
            <Button onClick={handleClose} variant="ghost" className="w-full justify-center">
              Fermer
            </Button>
          </div>
        )}
      </div>
    </Modal>
  )
}
