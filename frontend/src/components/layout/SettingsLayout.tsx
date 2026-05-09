import { NavLink, Outlet, useParams } from 'react-router-dom'
import { cn } from '@/utils/cn'

type SettingsTab = {
  label: string
  to: string
}

export default function SettingsLayout() {
  const { projectId } = useParams<{ projectId: string }>()

  const tabs: SettingsTab[] = [
    { label: 'Général', to: `/projects/${projectId}/settings` },
    { label: 'Stratégie', to: `/projects/${projectId}/settings/strategy` },
    { label: 'Providers', to: `/projects/${projectId}/settings/providers` },
    { label: 'Équipe', to: `/projects/${projectId}/settings/members` },
    { label: 'Intégration', to: `/projects/${projectId}/settings/integration` },
  ]

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-8">
        <h1 className="text-[20px] font-semibold text-primary tracking-tight">Paramètres</h1>
        <p className="mt-0.5 text-[13px] text-secondary">
          Configurez votre projet, votre équipe et votre intégration.
        </p>
      </div>

      {/* Tab navigation */}
      <div className="mb-6 flex gap-0.5 rounded-[12px] bg-[#f0f0f2] p-1">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end
            className={({ isActive }) =>
              cn(
                'flex-1 rounded-[8px] py-1.5 text-center text-[13px] font-medium transition-all duration-150',
                isActive
                  ? 'bg-surface text-primary shadow-sm'
                  : 'text-secondary hover:text-primary',
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      <Outlet />
    </div>
  )
}
