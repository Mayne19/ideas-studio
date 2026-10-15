import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Loader2, XCircle } from '@/components/ui/hugeIcons'
import { friendlyApiErrorMessage } from '@/api/client'
import { listExternalServices, type ExternalServicePublic } from '@/api/externalServices'
import { useProject } from '@/context/ProjectContext'
import ExternalServiceCard from './ExternalServiceCard'

function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-error/10">
        <span className="text-2xl text-error">🔒</span>
      </div>
      <h2 className="text-[18px] font-semibold text-primary">Accès réservé aux administrateurs</h2>
      <p className="mt-2 max-w-sm text-[15px] text-secondary">
        La configuration des services externes est réservée aux owners et admins du projet.
      </p>
    </div>
  )
}

export default function ProjectExternalServicesPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { myRole } = useProject()
  const [services, setServices] = useState<ExternalServicePublic[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      setServices(await listExternalServices(projectId))
    } catch (err: unknown) {
      setError(friendlyApiErrorMessage(err, 'Erreur de chargement'))
      setServices([])
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    const timer = setTimeout(() => load(), 0)
    return () => clearTimeout(timer)
  }, [load])

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
      <h2 className="text-[15px] font-semibold text-primary">Services externes</h2>

      <div className="rounded-[14px] border border-accent/20 bg-accent/5 px-4 py-3">
        <p className="text-[12px] text-secondary leading-snug">
          Clés des services utilisés par les agents en dehors des providers IA : recherche web (analyse SERP,
          idées, sources) et banques d'images. Les clés sont chiffrées et ne sont jamais réaffichées — seuls
          leurs 4 derniers caractères le sont. Une clé définie ici prime sur la configuration globale de la
          plateforme et sur les variables d'environnement du serveur.
        </p>
      </div>

      {error && (
        <div className="rounded-[12px] border border-danger/20 bg-danger/5 px-4 py-3">
          <div className="flex items-start gap-2 text-[14px] text-danger">
            <XCircle size={15} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-medium">Services externes indisponibles</p>
              <p className="mt-0.5 text-[12px] text-secondary">
                {error === 'Not Found' ? "L’API Services externes n’est pas disponible sur ce déploiement. Déployez le backend à jour." : error}
              </p>
            </div>
          </div>
          <button onClick={load} className="mt-3 rounded-[10px] bg-accent px-4 py-2 text-[12px] font-medium text-white transition-opacity hover:opacity-90">
            Réessayer
          </button>
        </div>
      )}

      {services.map((service) => (
        <ExternalServiceCard
          key={`${service.service}:${service.id ?? 'none'}:${service.provider ?? ''}`}
          service={service}
          projectId={projectId}
          onChanged={load}
        />
      ))}
    </div>
  )
}
