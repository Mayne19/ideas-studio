import { Info, CheckCircle, AlertCircle } from 'lucide-react'

type ProviderDef = {
  name: string
  description: string
  status: 'active' | 'inactive' | 'coming_soon'
}

const PROVIDERS: ProviderDef[] = [
  {
    name: 'OpenAI / Compatible',
    description: 'Génération d\'idées, rédaction d\'articles, analyse SEO.',
    status: 'active',
  },
  {
    name: 'Anthropic Claude',
    description: 'Modèle alternatif pour la génération de contenu.',
    status: 'coming_soon',
  },
  {
    name: 'Google Search Console',
    description: 'Import des données de positionnement SEO.',
    status: 'coming_soon',
  },
  {
    name: 'WordPress',
    description: 'Publication directe sur votre CMS WordPress.',
    status: 'coming_soon',
  },
]

export default function ProjectProvidersPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start gap-3 rounded-[14px] border border-accent/20 bg-accent/5 px-4 py-3">
        <Info size={15} className="mt-0.5 shrink-0 text-accent" />
        <div>
          <p className="text-[13px] font-medium text-primary">Configuration des providers</p>
          <p className="mt-0.5 text-[12px] text-secondary leading-snug">
            La configuration manuelle des clés API et providers sera disponible prochainement.
            Actuellement, les providers sont configurés via les variables d'environnement du serveur.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {PROVIDERS.map((provider) => (
          <div
            key={provider.name}
            className="flex items-center gap-4 rounded-[14px] border border-border bg-surface px-4 py-3"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-[13px] font-medium text-primary">{provider.name}</p>
                {provider.status === 'coming_soon' && (
                  <span className="rounded-full bg-[#f0f0f2] px-2 py-0.5 text-[10px] font-medium text-tertiary">
                    Bientôt
                  </span>
                )}
              </div>
              <p className="mt-0.5 text-[12px] text-tertiary">{provider.description}</p>
            </div>
            {provider.status === 'active' && (
              <div className="flex items-center gap-1.5 shrink-0">
                <CheckCircle size={14} className="text-[#1a7a3a]" />
                <span className="text-[12px] text-[#1a7a3a]">Actif</span>
              </div>
            )}
            {provider.status === 'inactive' && (
              <div className="flex items-center gap-1.5 shrink-0">
                <AlertCircle size={14} className="text-[#c07000]" />
                <span className="text-[12px] text-[#c07000]">Inactif</span>
              </div>
            )}
            {provider.status === 'coming_soon' && (
              <div className="flex items-center gap-1.5 shrink-0 opacity-40">
                <span className="text-[12px] text-tertiary">—</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
