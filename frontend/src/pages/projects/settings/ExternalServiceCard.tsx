import { useState } from 'react'
import { Trash2, TestTube, CheckCircle, XCircle, Loader2, Eye, EyeOff, Save, ExternalLink } from '@/components/ui/hugeIcons'
import { friendlyApiErrorMessage } from '@/api/client'
import {
  deleteExternalService,
  saveExternalService,
  testExternalService,
  type ExternalServicePublic,
  type ExternalServiceUpsert,
} from '@/api/externalServices'

const FIELD_LABELS: Record<string, { label: string; placeholder: string }> = {
  cx: { label: 'Identifiant du moteur (cx)', placeholder: 'ex : 0123456789abcdef0' },
}

const SOURCE_LABELS: Record<string, string> = {
  project: 'clé du projet',
  global: 'clé globale de la plateforme',
  env: "variable d'environnement serveur",
}

type Props = {
  service: ExternalServicePublic
  projectId?: string
  onChanged: () => Promise<void> | void
}

function providerLabel(service: ExternalServicePublic, code: string | null): string {
  if (!code) return '—'
  return service.providers.find((p) => p.code === code)?.label ?? code
}

export default function ExternalServiceCard({ service, projectId, onChanged }: Props) {
  const [provider, setProvider] = useState<string>(service.provider ?? service.providers[0]?.code ?? '')
  const [apiKey, setApiKey] = useState('')
  const [config, setConfig] = useState<Record<string, string>>(service.config ?? {})
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [testResult, setTestResult] = useState<{ status: string; message: string } | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const selected = service.providers.find((p) => p.code === provider)
  const fields = selected?.fields ?? []
  const providerChanged = !!service.provider && provider !== service.provider
  const keyRequired = !service.api_key_configured || providerChanged
  const canSave = !!provider && (!keyRequired || apiKey.trim().length > 0) && fields.every((f) => (config[f] ?? '').trim())
  const canTest = apiKey.trim().length > 0 || !!service.effective_source

  function buildPayload(): ExternalServiceUpsert {
    const payload: ExternalServiceUpsert = { provider }
    if (apiKey.trim()) payload.api_key = apiKey.trim()
    if (fields.length > 0) {
      payload.config = Object.fromEntries(fields.map((f) => [f, (config[f] ?? '').trim()]))
    }
    return payload
  }

  async function handleSave() {
    setSaving(true)
    setFormError(null)
    try {
      await saveExternalService(service.service, buildPayload(), projectId)
      setApiKey('')
      setTestResult(null)
      await onChanged()
    } catch (err: unknown) {
      setFormError(friendlyApiErrorMessage(err, 'Erreur lors de la sauvegarde'))
    } finally {
      setSaving(false)
    }
  }

  async function handleTest() {
    setTesting(true)
    setTestResult(null)
    try {
      // Clé saisie : on la teste avant enregistrement ; sinon la clé enregistrée / réellement utilisée.
      const draft = apiKey.trim() ? buildPayload() : undefined
      const result = await testExternalService(service.service, projectId, draft)
      setTestResult({
        status: result.status,
        message: result.message || (result.status === 'connected' ? 'Connexion réussie' : 'Erreur inconnue'),
      })
      if (!draft) await onChanged()
    } catch (err: unknown) {
      setTestResult({ status: 'error', message: friendlyApiErrorMessage(err, 'Erreur de test') })
    } finally {
      setTesting(false)
    }
  }

  async function handleDelete() {
    if (!confirm(`Supprimer la clé ${providerLabel(service, service.provider)} de « ${service.label} » ?`)) return
    setDeleting(true)
    try {
      await deleteExternalService(service.service, projectId)
      setApiKey('')
      setTestResult(null)
      await onChanged()
    } catch (err: unknown) {
      alert(friendlyApiErrorMessage(err, 'Erreur lors de la suppression'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="rounded-[8px] border border-border bg-surface p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[14px] font-medium text-primary">{service.label}</p>
            {service.last_test_status === 'connected' && (
              <span className="rounded-full bg-success/8 px-2 py-0.5 text-[10px] font-medium text-success">Connecté</span>
            )}
            {service.last_test_status === 'error' && (
              <span className="rounded-full bg-danger/8 px-2 py-0.5 text-[10px] font-medium text-danger">Erreur</span>
            )}
            {!service.id && service.effective_source === 'env' && (
              <span className="rounded-full bg-warning/10 px-2 py-0.5 text-[10px] font-medium text-warning">Variable d'environnement</span>
            )}
            {!service.id && service.effective_source === 'global' && (
              <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">Config globale</span>
            )}
            {!service.effective_source && (
              <span className="rounded-full bg-surface-soft px-2 py-0.5 text-[10px] font-medium text-tertiary">Non configuré</span>
            )}
          </div>
          {service.description && <p className="mt-0.5 text-[12px] text-tertiary">{service.description}</p>}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleTest}
            disabled={testing || !canTest}
            className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-surface-soft hover:text-primary transition-colors disabled:opacity-40"
            title={apiKey.trim() ? 'Tester la clé saisie' : 'Tester la connexion'}
          >
            {testing ? <Loader2 size={13} className="animate-spin" /> : <TestTube size={13} />}
          </button>
          {service.id && (
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-danger/10 hover:text-danger transition-colors"
              title="Supprimer la clé du projet"
            >
              {deleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
            </button>
          )}
        </div>
      </div>

      {service.last_test_error && (
        <p className="text-[12px] text-danger mb-2">{service.last_test_error}</p>
      )}

      {testResult && (
        <div className={`rounded-[8px] p-2 text-[12px] mb-2 ${testResult.status === 'connected' ? 'bg-success/8 text-success' : 'bg-danger/8 text-danger'}`}>
          {testResult.status === 'connected' ? <CheckCircle size={11} className="inline mr-1" /> : <XCircle size={11} className="inline mr-1" />}
          {testResult.message}
        </div>
      )}

      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">Provider</label>
            <select
              value={provider}
              onChange={(e) => { setProvider(e.target.value); setTestResult(null); setFormError(null) }}
              className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent"
            >
              {service.providers.map((p) => (
                <option key={p.code} value={p.code}>{p.label}</option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-[12px] font-medium text-secondary">
              Clé API {keyRequired ? '' : '(laisser vide pour conserver)'}
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                autoComplete="off"
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={!keyRequired && service.key_last4 ? `•••• ${service.key_last4}` : 'Votre clé API'}
                className="w-full rounded-[10px] border border-border bg-surface px-3 py-2 pr-8 text-[14px] text-primary outline-none focus:border-accent"
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-tertiary hover:text-primary"
              >
                {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
          {fields.map((field) => (
            <div key={field} className="flex flex-col gap-1.5">
              <label className="text-[12px] font-medium text-secondary">{FIELD_LABELS[field]?.label ?? field}</label>
              <input
                type="text"
                value={config[field] ?? ''}
                onChange={(e) => setConfig((c) => ({ ...c, [field]: e.target.value }))}
                placeholder={FIELD_LABELS[field]?.placeholder}
                className="rounded-[10px] border border-border bg-surface px-3 py-2 text-[14px] text-primary outline-none focus:border-accent"
              />
            </div>
          ))}
        </div>

        {formError && <p className="text-[12px] text-danger">{formError}</p>}

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleSave}
            disabled={saving || !canSave}
            className="flex items-center gap-1.5 rounded-[10px] bg-accent px-4 py-2 text-[12px] font-medium text-white hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
            {service.id ? 'Mettre à jour' : 'Enregistrer'}
          </button>
          {selected?.docs_url && (
            <a
              href={selected.docs_url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1 rounded-[10px] px-3 py-2 text-[12px] font-medium text-secondary hover:bg-surface-soft transition-colors"
            >
              <ExternalLink size={12} />
              Obtenir une clé
            </a>
          )}
        </div>

        <div className="flex flex-wrap gap-4 text-[12px] text-tertiary">
          <span>
            Utilisé actuellement :{' '}
            {service.effective_source
              ? `${providerLabel(service, service.effective_provider)}${service.effective_key_last4 ? ` · •••• ${service.effective_key_last4}` : ''} (${SOURCE_LABELS[service.effective_source] ?? service.effective_source})`
              : 'aucun'}
          </span>
          {service.last_tested_at && <span>Dernier test : {new Date(service.last_tested_at).toLocaleString('fr-FR')}</span>}
        </div>
      </div>
    </div>
  )
}
