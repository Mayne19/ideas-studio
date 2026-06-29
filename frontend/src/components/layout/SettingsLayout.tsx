import { NavLink, Outlet, useParams } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { getSettingsSections } from '@/lib/settingsSections'
import { useProject } from '@/context/ProjectContext'

export default function SettingsLayout() {
  const { projectId } = useParams<{ projectId: string }>()
  const { isAdminOrOwner } = useProject()
  const tabs = getSettingsSections(projectId, { showAdminOnly: isAdminOrOwner })

  return (
    <div className="project-page project-page--wide">
      <div className="grid items-start gap-8 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="sticky top-0 z-10 bg-app pb-4 pt-1">
          <div className="mb-5 px-1">
            <h1 className="text-[20px] font-semibold text-primary tracking-tight">Paramètres</h1>
            <p className="mt-0.5 max-w-[210px] whitespace-normal text-[13px] leading-snug text-secondary">
              Configurez votre projet, votre équipe et votre intégration.
            </p>
          </div>

          <nav className="flex flex-col gap-1 rounded-[18px] bg-surface p-2">
            {tabs.map((tab) => (
              <NavLink
                key={tab.key}
                to={tab.path}
                end={tab.end}
                className={({ isActive }) =>
                  cn(
                    'rounded-[12px] px-3 py-2.5 transition-colors',
                    isActive
                      ? 'bg-accent/10 text-accent'
                      : 'text-secondary hover:bg-[#f0f0f2] hover:text-primary',
                  )
                }
              >
                <span className="block text-[13px] font-semibold">{tab.label}</span>
                <span className="mt-0.5 block max-w-full whitespace-normal break-words text-[11px] leading-snug text-tertiary">
                  {tab.description}
                </span>
              </NavLink>
            ))}
          </nav>
        </aside>

        <div className="min-w-0">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
