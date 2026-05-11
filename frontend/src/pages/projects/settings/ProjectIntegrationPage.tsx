import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { Code2, Eye, EyeOff, Globe, Key, Power, RefreshCw, Wifi, WifiOff } from 'lucide-react'
import { getConnectInfo } from '@/api/projects'
import type { ConnectInfo } from '@/types'
import FormCard from '@/components/ui/FormCard'
import CopyButton from '@/components/ui/CopyButton'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import { formatDateTime } from '@/utils/format'

const API_KEY_MASK = '********'

function InfoRow({
  label,
  value,
  copyValue,
  canCopy = false,
  action,
  mono = true,
}: {
  label: string
  value: string
  copyValue?: string
  canCopy?: boolean
  action?: ReactNode
  mono?: boolean
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-[12px] bg-[#f9f9fb] px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-medium uppercase tracking-wider text-tertiary">{label}</p>
        <p className={`mt-0.5 truncate text-[13px] text-primary ${mono ? 'font-mono' : ''}`}>{value}</p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {action}
        {canCopy && <CopyButton value={copyValue ?? value} disabled={!(copyValue ?? value)} className="shrink-0" />}
      </div>
    </div>
  )
}

export default function ProjectIntegrationPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [info, setInfo] = useState<ConnectInfo | null>(null)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshState, setRefreshState] = useState<'idle' | 'success' | 'error'>('idle')
  const [isApiKeyVisible, setIsApiKeyVisible] = useState(false)
  const [showInstructions, setShowInstructions] = useState(false)

  function loadInfo({ quiet = false }: { quiet?: boolean } = {}) {
    if (!projectId) return
    if (quiet) setIsRefreshing(true)
    else setStatus('loading')
    getConnectInfo(projectId)
      .then((data) => {
        setInfo(data)
        setStatus('success')
        if (quiet) {
          setRefreshState('success')
          window.setTimeout(() => setRefreshState('idle'), 2200)
        }
      })
      .catch(() => {
        if (quiet) {
          setRefreshState('error')
          window.setTimeout(() => setRefreshState('idle'), 2600)
        } else {
          setStatus('error')
        }
      })
      .finally(() => setIsRefreshing(false))
  }

  useEffect(() => {
    if (!projectId) return
    getConnectInfo(projectId)
      .then((data) => { setInfo(data); setStatus('success') })
      .catch(() => setStatus('error'))
  }, [projectId])

  if (status === 'loading') return <LoadingState />
  if (status === 'error') return <ErrorState onRetry={loadInfo} />

  const isConnected = info?.status === 'connected'
  const apiKey = info?.secret_api_key ?? ''
  const apiKeyDisplay = isApiKeyVisible && apiKey ? apiKey : API_KEY_MASK
  const hasApiKey = Boolean(apiKey)
  const hasInstructionsVisible = !isConnected || showInstructions

  return (
    <div className="flex flex-col gap-5">
      {/* Connection status */}
      <FormCard title="Statut de connexion">
        <div className="flex flex-col gap-3">
          <div
            className={`flex flex-wrap items-center justify-between gap-3 rounded-[14px] px-4 py-3 ${
              isConnected ? 'bg-success/8' : 'bg-[#f9f9fb]'
            }`}
          >
            <div className="flex min-w-0 items-center gap-3">
              <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-[12px] ${isConnected ? 'bg-success/10 text-success' : 'bg-[#f0f0f2] text-tertiary'}`}>
                {isConnected ? <Wifi size={18} /> : <WifiOff size={18} />}
              </span>
              <div className="min-w-0">
                <p className={`text-[14px] font-semibold ${isConnected ? 'text-[#1a7a3a]' : 'text-primary'}`}>
                  {isConnected ? 'Site connecté' : 'En attente de connexion'}
                </p>
                <p className="text-[12px] text-secondary">
                  {isConnected
                    ? 'Le snippet est actif et les données sont collectées.'
                    : 'Installez le snippet ci-dessous pour connecter votre site.'}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-end gap-2">
              {refreshState !== 'idle' && (
                <span className={`text-[12px] ${refreshState === 'success' ? 'text-success' : 'text-danger'}`}>
                  {refreshState === 'success' ? 'Statut actualisé' : 'Actualisation impossible'}
                </span>
              )}
              <button
                onClick={() => loadInfo({ quiet: true })}
                disabled={isRefreshing}
                className="inline-flex items-center gap-1.5 rounded-[8px] bg-[#f0f0f2] px-3 py-1.5 text-[12px] font-medium text-secondary transition-colors hover:bg-[#e5e5e7] hover:text-primary disabled:cursor-wait disabled:opacity-60"
              >
                <RefreshCw size={12} className={isRefreshing ? 'animate-spin' : ''} />
                Actualiser le statut
              </button>
              {isConnected && (
                <button
                  disabled
                  className="inline-flex cursor-not-allowed items-center gap-1.5 rounded-[8px] bg-[#f0f0f2] px-3 py-1.5 text-[12px] font-medium text-tertiary opacity-60"
                  title="Déconnexion bientôt disponible côté backend"
                >
                  <Power size={12} />
                  Déconnecter
                </button>
              )}
            </div>
          </div>
          {isConnected && (
            <div className="grid gap-2 sm:grid-cols-3">
              <InfoRow label="Domaine" value={info?.domain ?? 'Domaine non renseigné'} mono={false} />
              <InfoRow label="Connecté depuis" value={info?.connected_at ? formatDateTime(info.connected_at) : 'Date non disponible'} mono={false} />
              <InfoRow label="Dernière activité" value={info?.last_seen_at ? formatDateTime(info.last_seen_at) : 'Aucune activité récente'} mono={false} />
            </div>
          )}
        </div>
      </FormCard>

      {/* Keys & identifiers */}
      <FormCard
        title="Identifiants"
        description="Utilisez ces clés pour connecter votre blog à l'API publique."
      >
        <div className="flex flex-col gap-2">
          <InfoRow
            label="Project ID"
            value={info?.project_id ?? '—'}
            copyValue={info?.project_id}
            canCopy={Boolean(info?.project_id)}
          />
          <InfoRow
            label="Clé de tracking publique"
            value={info?.public_tracking_key ?? '—'}
            copyValue={info?.public_tracking_key}
            canCopy={Boolean(info?.public_tracking_key)}
          />
          <InfoRow
            label="Clé API (masquée)"
            value={apiKeyDisplay}
            copyValue={apiKey}
            canCopy={hasApiKey}
            action={(
              <button
                onClick={() => setIsApiKeyVisible((visible) => !visible)}
                disabled={!hasApiKey}
                className="inline-flex items-center gap-1.5 rounded-[8px] bg-[#f0f0f2] px-3 py-1.5 text-[12px] font-medium text-secondary transition-colors hover:bg-[#e5e5e7] hover:text-primary disabled:cursor-not-allowed disabled:text-tertiary disabled:opacity-60"
              >
                {isApiKeyVisible ? <EyeOff size={12} /> : <Eye size={12} />}
                {isApiKeyVisible ? 'Masquer' : 'Révéler'}
              </button>
            )}
          />
        </div>
      </FormCard>

      {isConnected && (
        <button
          onClick={() => setShowInstructions((visible) => !visible)}
          className="w-fit rounded-[10px] bg-[#f0f0f2] px-3.5 py-2 text-[13px] font-medium text-secondary transition-colors hover:bg-[#e5e5e7] hover:text-primary"
        >
          {showInstructions ? 'Masquer les instructions d’installation' : 'Voir les instructions d’installation'}
        </button>
      )}

      {hasInstructionsVisible && (
        <>
          {/* Step-by-step instructions */}
          <FormCard
            title="Comment connecter votre blog"
            description="Suivez ces 4 étapes pour activer le tracking et les analyses SEO."
          >
            <ol className="flex flex-col gap-3">
              {[
                { n: 1, text: 'Copiez le snippet ci-dessous (bouton "Copier" à droite du code).' },
                { n: 2, text: 'Collez-le dans la balise <head> de votre site, avant </head>.' },
                { n: 3, text: 'Déployez votre site avec ce changement.' },
                { n: 4, text: 'Revenez ici — le statut passera à "Connecté" dès la première visite enregistrée.' },
              ].map(({ n, text }) => (
                <li key={n} className="flex items-start gap-3">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent/10 text-[11px] font-semibold text-accent mt-0.5">
                    {n}
                  </span>
                  <span className="text-[13px] text-secondary leading-snug">{text}</span>
                </li>
              ))}
            </ol>
          </FormCard>

          {/* Tracking snippet */}
          <FormCard
            title="Snippet de tracking"
            description="Collez ce code dans le <head> de votre site pour activer le tracking et la connexion API."
          >
            <div className="flex flex-col gap-3">
              <div className="relative">
                <div className="flex items-center justify-between rounded-t-[12px] bg-[#f0f0f2] px-3.5 py-2">
                  <div className="flex items-center gap-2 text-[12px] text-secondary">
                    <Code2 size={13} />
                    HTML
                  </div>
                  <CopyButton value={info?.snippet ?? ''} disabled={!info?.snippet} />
                </div>
                <pre className="overflow-x-auto rounded-b-[12px] bg-[#1d1d1f] p-4 text-[12px] leading-relaxed text-[#e5e5e7]">
                  <code>{info?.snippet}</code>
                </pre>
              </div>
            </div>
          </FormCard>
        </>
      )}

      {/* Public API endpoints */}
      {info?.public_api_endpoints && Object.keys(info.public_api_endpoints).length > 0 && (
        <FormCard
          title="Endpoints API publics"
          description="Ces routes sont accessibles sans authentification pour alimenter votre blog."
        >
          <div className="flex flex-col gap-2">
            {Object.entries(info.public_api_endpoints).map(([key, url]) => (
              <div
                key={key}
                className="flex items-start justify-between gap-3 rounded-[12px] bg-[#f9f9fb] px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wider text-tertiary">
                    <Globe size={11} />
                    {key}
                  </div>
                  <p className="mt-0.5 truncate font-mono text-[12px] text-secondary">{url}</p>
                </div>
                <CopyButton value={url} className="shrink-0" />
              </div>
            ))}
          </div>
        </FormCard>
      )}

      {/* Key notice */}
      <div className="flex items-start gap-2.5 rounded-[16px] bg-[#f9f9fb] px-4 py-3">
        <Key size={14} className="mt-0.5 shrink-0 text-tertiary" />
        <p className="text-[12px] text-secondary leading-relaxed">
          La clé API secrète est masquée par défaut et ne s'affiche en clair que lorsque vous cliquez sur Révéler. Contactez un administrateur si vous avez besoin de la réinitialiser.
        </p>
      </div>
    </div>
  )
}
