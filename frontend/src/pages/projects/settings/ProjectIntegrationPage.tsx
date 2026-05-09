import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Wifi, WifiOff, Globe, Key, Code2 } from 'lucide-react'
import { getConnectInfo } from '@/api/projects'
import type { ConnectInfo } from '@/types'
import FormCard from '@/components/ui/FormCard'
import CopyButton from '@/components/ui/CopyButton'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'

function InfoRow({ label, value, canCopy = false }: { label: string; value: string; canCopy?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-[12px] bg-[#f9f9fb] px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-medium uppercase tracking-wider text-tertiary">{label}</p>
        <p className="mt-0.5 truncate font-mono text-[13px] text-primary">{value}</p>
      </div>
      {canCopy && <CopyButton value={value} className="shrink-0" />}
    </div>
  )
}

export default function ProjectIntegrationPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [info, setInfo] = useState<ConnectInfo | null>(null)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  function loadInfo() {
    if (!projectId) return
    setStatus('loading')
    getConnectInfo(projectId)
      .then((data) => { setInfo(data); setStatus('success') })
      .catch(() => setStatus('error'))
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

  return (
    <div className="flex flex-col gap-5">
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

      {/* Connection status */}
      <FormCard title="Statut de connexion">
        <div
          className={`flex items-center gap-3 rounded-[14px] px-4 py-3 ${
            isConnected ? 'bg-success/8' : 'bg-[#f9f9fb]'
          }`}
        >
          {isConnected ? (
            <Wifi size={18} className="text-success" />
          ) : (
            <WifiOff size={18} className="text-tertiary" />
          )}
          <div>
            <p className={`text-[14px] font-semibold ${isConnected ? 'text-[#1a7a3a]' : 'text-primary'}`}>
              {isConnected ? 'Blog connecté' : 'En attente de connexion'}
            </p>
            <p className="text-[12px] text-secondary">
              {isConnected
                ? 'Le snippet est actif et les données sont collectées.'
                : 'Installez le snippet ci-dessous pour connecter votre blog.'}
            </p>
          </div>
        </div>
      </FormCard>

      {/* Tracking snippet */}
      <FormCard
        title="Snippet de tracking"
        description="Collez ce code dans le <head> de votre site pour activer le tracking et la connexion API."
      >
        <div className="flex flex-col gap-3">
          <div className="relative">
            <div className="flex items-center justify-between rounded-t-[12px] border border-border bg-[#f0f0f2] px-3.5 py-2">
              <div className="flex items-center gap-2 text-[12px] text-secondary">
                <Code2 size={13} />
                HTML
              </div>
              <CopyButton value={info?.snippet ?? ''} />
            </div>
            <pre className="overflow-x-auto rounded-b-[12px] border border-t-0 border-border bg-[#1d1d1f] p-4 text-[12px] leading-relaxed text-[#e5e5e7]">
              <code>{info?.snippet}</code>
            </pre>
          </div>
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
            canCopy
          />
          <InfoRow
            label="Clé de tracking publique"
            value={info?.public_tracking_key ?? '—'}
            canCopy
          />
          <InfoRow
            label="Clé API (masquée)"
            value={info?.secret_api_key_masked ?? '—'}
          />
        </div>
      </FormCard>

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
      <div className="flex items-start gap-2.5 rounded-[14px] border border-border bg-[#f9f9fb] px-4 py-3">
        <Key size={14} className="mt-0.5 shrink-0 text-tertiary" />
        <p className="text-[12px] text-secondary leading-relaxed">
          La clé API secrète n'est jamais affichée en clair. Contactez un administrateur si vous avez besoin de la réinitialiser.
        </p>
      </div>
    </div>
  )
}
