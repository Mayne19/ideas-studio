import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Plus, Trash2, TestTube, CheckCircle, XCircle, Loader2, Eye, EyeOff, Save } from '@/components/ui/hugeIcons'
import { api } from '@/api/client'
import { Card } from '@/components/ui/Card'
import ToggleSwitch from '@/components/ui/ToggleSwitch'
import { useProject } from '@/context/ProjectContext'

type AIProviderConfig = {
  id: string
  provider: string
  label: string
  api_key_configured: boolean
  model: string
  base_url: string
  is_default: boolean
  enabled: boolean
  last_test_status: string | null
  last_test_error: string | null
  last_tested_at: string | null
  created_at: string
  updated_at: string
}

type ProviderDef = {
  key: string
  label: string
  default_model: string
  default_base_url: string
}

const SUPPORTED_PROVIDERS: ProviderDef[] = [
  { key: 'gemini', label: 'Google Gemini', default_model: 'gemini-2.5-flash', default_base_url: 'https://generativelanguage.googleapis.com/v1beta/openai/' },
  { key: 'openai', label: 'OpenAI', default_model: 'gpt-4o-mini', default_base_url: 'https://api.openai.com/v1' },
  { key: 'openrouter', label: 'OpenRouter', default_model: 'deepseek/deepseek-v4-flash', default_base_url: 'https://openrouter.ai/api/v1' },
  { key: 'anthropic', label: 'Claude / Anthropic', default_model: 'claude-3-5-sonnet-latest', default_base_url: 'https://api.anthropic.com/v1' },
  { key: 'mistral', label: 'Mistral', default_model: 'mistral-large-latest', default_base_url: 'https://api.mistral.ai/v1' },
  { key: 'ollama', label: 'Ollama (local)', default_model: 'qwen3:14b', default_base_url: 'http://127.0.0.1:11434/v1' },
  { key: 'custom', label: 'Custom OpenAI-compatible', default_model: '', default_base_url: '' },
]

function getProviderDef(key: string): ProviderDef | undefined {
  return SUPPORTED_PROVIDERS.find((p) => p.key === key)
}

type ProviderFormData = {
  provider: string
  label: string
  api_key: string
  model: string
  base_url: string
  is_default: boolean
  enabled: boolean
}

const emptyForm: ProviderFormData = {
  provider: 'gemini',
  label: '',
  api_key: '',
  model: '',
  base_url: '',
  is_default: false,
  enabled: true,
}

function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-error/10">
        <span className="text-2xl text-error">🔒</span>
      </div>
      <h2 className="text-[18px] font-semibold text-primary">Accès réservé aux administrateurs</h2>
      <p className="mt-2 max-w-sm text-[14px] text-secondary">
        La configuration des providers, agents et pipeline est réservée aux owners et admins du projet.
      </p>
    </div>
  )
}

export default function ProjectProvidersPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { myRole } = useProject()
  const [configs, setConfigs] = useState<AIProviderConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<ProviderFormData>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ id: string; status: string; message: string } | null>(null)
  const [showKeys, setShowKeys] = useState<Set<string>>(new Set())
  const [deleting, setDeleting] = useState<string | null>(null)
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const loadConfigs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<AIProviderConfig[]>(projectId ? `/settings/ai-providers?project_id=${projectId}` : '/settings/ai-providers')
      setConfigs(data)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur de chargement'
      setError(msg)
      setConfigs([])
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    const timer = setTimeout(() => loadConfigs(), 0)
    return () => clearTimeout(timer)
  }, [loadConfigs])

  function openCreate(providerKey: string) {
    const def = getProviderDef(providerKey)
    setForm({
      provider: providerKey,
      label: def?.label ?? providerKey,
      api_key: '',
      model: def?.default_model ?? '',
      base_url: def?.default_base_url ?? '',
      is_default: configs.length === 0,
      enabled: true,
    })
    setEditingId(null)
    setShowForm(true)
    setTestResult(null)
    setAdvancedOpen(providerKey === 'custom' || providerKey === 'ollama')
  }

  function openEdit(config: AIProviderConfig) {
    const def = getProviderDef(config.provider)
    setForm({
      provider: config.provider,
      label: config.label,
      api_key: '',
      model: config.model || def?.default_model || '',
      base_url: config.base_url || def?.default_base_url || '',
      is_default: config.is_default,
      enabled: config.enabled,
    })
    setEditingId(config.id)
    setShowForm(true)
    setTestResult(null)
    setAdvancedOpen(config.provider === 'custom' || config.provider === 'ollama')
  }

  async function handleSave() {
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        provider: form.provider,
        label: form.label || form.provider,
        project_id: projectId,
        model: form.model || undefined,
        base_url: form.base_url || undefined,
        is_default: form.is_default,
        enabled: form.enabled,
      }
      if (form.api_key) body.api_key = form.api_key

      if (editingId) {
        await api.patch(`/settings/ai-providers/${editingId}`, body)
      } else {
        await api.post('/settings/ai-providers', body)
      }
      setShowForm(false)
      setEditingId(null)
      setTestResult(null)
      await loadConfigs()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur lors de la sauvegarde'
      alert(msg)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    setDeleting(id)
    try {
      await api.delete(`/settings/ai-providers/${id}`)
      await loadConfigs()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur lors de la suppression'
      alert(msg)
    } finally {
      setDeleting(null)
    }
  }

  async function handleTest(id: string) {
    setTesting(id)
    setTestResult(null)
    try {
      const result = await api.post<{ status: string; message: string }>(`/settings/ai-providers/${id}/test`)
      setTestResult({ id, status: result.status, message: result.message || (result.status === 'connected' ? 'Connexion réussie' : 'Erreur inconnue') })
      await loadConfigs()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Erreur de test'
      setTestResult({ id, status: 'error', message: msg })
    } finally {
      setTesting(null)
    }
  }

  function toggleKey(id: string) {
    setShowKeys((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (myRole !== null && myRole !== 'owner' && myRole !== 'admin') {
    return <AccessDenied />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={20} className="animate-spin text-tertiary" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-[15px] font-semibold text-primary">Configuration des providers IA</h2>
      </div>

      {error && (
        <div className="rounded-[8px] border border-danger/20 bg-danger/5 px-4 py-3">
          <div className="flex items-start gap-2 text-[13px] text-danger">
            <XCircle size={15} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-medium">Configuration IA indisponible</p>
              <p className="mt-0.5 text-[12px] text-secondary">
                {error === 'Not Found' ? "L’API Providers n’est pas disponible sur ce déploiement. Déployez le backend à jour pour connecter Gemini." : error}
              </p>
            </div>
          </div>
          <button onClick={loadConfigs} className="mt-3 rounded-[6px] bg-primary px-4 py-2 text-[12px] font-medium text-bg transition-opacity hover:opacity-90">
            Réessayer
          </button>
        </div>
      )}

      {configs.length === 0 && !showForm && (
        <Card className="text-center">
          <p className="text-[13px] text-secondary mb-4">Aucun provider configuré. Ajoutez-en un depuis la liste ci-dessous.</p>
          <div className="flex flex-wrap justify-center gap-2">
            {SUPPORTED_PROVIDERS.map((p) => (
              <button
                key={p.key}
                onClick={() => openCreate(p.key)}
                disabled={!!error}
                className="flex items-center gap-1.5 rounded-[6px] border border-border px-3 py-2 text-[12px] font-medium text-secondary transition-colors hover:bg-surface-soft hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Plus size={13} />
                {p.label}
              </button>
            ))}
          </div>
        </Card>
      )}

      {configs.map((config) => {
        const def = getProviderDef(config.provider)
        return (
          <div key={config.id} className="rounded-[8px] bg-surface p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-[13px] font-medium text-primary">{config.label}</p>
                  {config.is_default && (
                    <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">Par défaut</span>
                  )}
                  {config.last_test_status === 'connected' && (
                    <span className="rounded-full bg-success/10 px-2 py-0.5 text-[10px] font-medium text-success">Connecté</span>
                  )}
                  {config.last_test_status === 'error' && (
                    <span className="rounded-full bg-danger/10 px-2 py-0.5 text-[10px] font-medium text-danger">Erreur</span>
                  )}
                </div>
                <p className="mt-0.5 text-[12px] text-tertiary">
                  {config.provider} · {config.model || def?.default_model || 'Modèle par défaut'}
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleTest(config.id)}
                  disabled={testing === config.id}
                  className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-surface-soft hover:text-primary transition-colors"
                  title="Tester la connexion"
                >
                  {testing === config.id ? <Loader2 size={13} className="animate-spin" /> : <TestTube size={13} />}
                </button>
                <button
                  onClick={() => openEdit(config)}
                  className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-surface-soft hover:text-primary transition-colors"
                  title="Modifier"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
                  </svg>
                </button>
                <button
                  onClick={() => handleDelete(config.id)}
                  disabled={deleting === config.id}
                  className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-danger/10 hover:text-danger transition-colors"
                  title="Supprimer"
                >
                  {deleting === config.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                </button>
              </div>
            </div>

            {config.last_test_error && (
              <p className="text-[11px] text-danger mb-2">{config.last_test_error}</p>
            )}

            {testResult && testResult.id === config.id && (
              <div className={`rounded-[6px] p-2 text-[11px] mb-2 ${testResult.status === 'connected' ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
                {testResult.status === 'connected' ? <CheckCircle size={11} className="inline mr-1" /> : <XCircle size={11} className="inline mr-1" />}
                {testResult.message}
              </div>
            )}

            <div className="flex flex-wrap gap-4 text-[11px] text-tertiary">
              <span>Clé API : {config.api_key_configured ? 'Configurée' : 'Non configurée'}</span>
              {config.last_tested_at && <span>Dernier test : {new Date(config.last_tested_at).toLocaleString('fr-FR')}</span>}
              <span>Statut : {config.enabled ? 'Actif' : 'Inactif'}</span>
            </div>
          </div>
        )
      })}

      {configs.length > 0 && !showForm && (
        <div className="flex flex-wrap gap-2">
          {SUPPORTED_PROVIDERS.map((p) => {
            const alreadyConfigured = configs.some((c) => c.provider === p.key)
            if (alreadyConfigured) return null
            return (
              <button
                key={p.key}
                onClick={() => openCreate(p.key)}
                disabled={!!error}
                className="flex items-center gap-1.5 rounded-[6px] border border-border px-3 py-2 text-[12px] font-medium text-secondary transition-colors hover:bg-surface-soft hover:text-primary disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Plus size={13} />
                {p.label}
              </button>
            )
          })}
        </div>
      )}

      {showForm && (
        <Card>
          <p className="text-[13px] font-medium text-primary mb-4">
            {editingId ? `Modifier : ${form.label}` : `Ajouter : ${getProviderDef(form.provider)?.label || form.provider}`}
          </p>
          <div className="flex flex-col gap-3">
            {!editingId && (
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-medium text-secondary">Type de provider</label>
                <select
                  value={form.provider}
                  onChange={(e) => {
                    const def = getProviderDef(e.target.value)
                    setForm({
                      ...form,
                      provider: e.target.value,
                      label: def?.label ?? e.target.value,
                      model: def?.default_model ?? '',
                      base_url: def?.default_base_url ?? '',
                    })
                    setAdvancedOpen(e.target.value === 'custom' || e.target.value === 'ollama')
                  }}
                  className="rounded-[6px] border border-border bg-surface px-3 py-2 text-[13px] text-primary outline-none focus:border-accent"
                >
                  {SUPPORTED_PROVIDERS.map((p) => (
                    <option key={p.key} value={p.key}>{p.label}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-medium text-secondary">Label</label>
              <input
                type="text"
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
                placeholder="Mon provider Gemini"
                className="rounded-[6px] border border-border bg-surface px-3 py-2 text-[13px] text-primary outline-none focus:border-accent"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-medium text-secondary">
                Clé API {editingId ? '(laisser vide pour conserver)' : ''}
              </label>
              <div className="relative">
                <input
                  type={showKeys.has('form') ? 'text' : 'password'}
                  value={form.api_key}
                  onChange={(e) => setForm({ ...form, api_key: e.target.value })}
                  placeholder={editingId ? 'Nouvelle clé (optionnelle)' : 'Votre clé API'}
                  className="w-full rounded-[6px] border border-border bg-surface px-3 py-2 pr-8 text-[13px] text-primary outline-none focus:border-accent"
                />
                <button
                  type="button"
                  onClick={() => toggleKey('form')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-tertiary hover:text-primary"
                >
                  {showKeys.has('form') ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-medium text-secondary">Modèle</label>
                <input
                  type="text"
                  value={form.model}
                  onChange={(e) => setForm({ ...form, model: e.target.value })}
                  placeholder="gemini-2.5-flash"
                  className="rounded-[6px] border border-border bg-surface px-3 py-2 text-[13px] text-primary outline-none focus:border-accent"
                />
              </div>
              {(advancedOpen || form.provider === 'custom' || form.provider === 'ollama') && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-[11px] font-medium text-secondary">URL de base</label>
                  <input
                    type="text"
                    value={form.base_url}
                    onChange={(e) => setForm({ ...form, base_url: e.target.value })}
                    placeholder="https://api.openai.com/v1"
                    className="rounded-[6px] border border-border bg-surface px-3 py-2 text-[13px] text-primary outline-none focus:border-accent"
                  />
                </div>
              )}
            </div>
            {form.provider !== 'custom' && form.provider !== 'ollama' && (
              <button
                type="button"
                onClick={() => setAdvancedOpen((open) => !open)}
                className="w-fit rounded-[6px] px-2 py-1 text-[11px] font-medium text-accent hover:bg-accent/10"
              >
                {advancedOpen ? 'Masquer les options avancées' : 'Afficher Base URL avancée'}
              </button>
            )}
            {form.provider === 'ollama' && (
              <div className="rounded-[8px] bg-warning/10 px-3 py-2 text-[12px] text-secondary">
                Ollama local fonctionne sur votre machine. Sur Render, utilisez un endpoint public sécurisé ou un provider cloud.
              </div>
            )}
            <div className="flex items-center gap-4">
              <ToggleSwitch checked={form.is_default} onChange={(v) => setForm({ ...form, is_default: v })} label="Provider par défaut" />
              <ToggleSwitch checked={form.enabled} onChange={(v) => setForm({ ...form, enabled: v })} label="Activé" />
            </div>
            <div className="flex items-center gap-2 pt-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-1.5 rounded-[6px] bg-primary px-4 py-2 text-[12px] font-medium text-bg hover:opacity-90 transition-opacity disabled:opacity-50"
              >
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                {editingId ? 'Mettre à jour' : 'Ajouter'}
              </button>
              <button
                onClick={() => { setShowForm(false); setEditingId(null); setTestResult(null) }}
                className="rounded-[6px] px-4 py-2 text-[12px] font-medium text-secondary hover:bg-surface-soft transition-colors"
              >
                Annuler
              </button>
            </div>
          </div>
        </Card>
      )}

      <div className="rounded-[8px] border border-accent/20 bg-accent/5 px-4 py-3">
        <p className="text-[12px] text-secondary leading-snug">
          Les providers configurés ici sont prioritaires par rapport aux variables d'environnement. 
          Vous pouvez ajouter un provider par type, tester sa connexion, et définir le provider par défaut.
          Les clés API sont stockées de manière sécurisée et ne sont jamais exposées au frontend.
        </p>
      </div>
    </div>
  )
}
