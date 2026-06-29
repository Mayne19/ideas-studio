import { useEffect, useRef, useState } from 'react'
import { NavLink, Link, useParams, useLocation, useNavigate } from 'react-router-dom'
import {
  FolderOpen,
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
  Check,
  Archive,
} from '@/components/ui/hugeIcons'
import {
  AiBrain01Icon,
  BellIcon,
  BulbIcon,
  Calendar03Icon,
  ChartBarLineIcon,
  CheckListIcon,
  ClipboardListIcon,
  DashboardSquare01Icon,
  File01Icon,
  Folder01Icon,
  Image01Icon,
  Logout01Icon,
  MagicWand01Icon,
  Setting06Icon,
  WorkflowCircle03Icon,
} from '@hugeicons/core-free-icons'
import { useProject } from '@/context/ProjectContext'
import { useAuth } from '@/context/AuthContext'
import { listProjects } from '@/api/projects'
import type { Project } from '@/types'
import { cn } from '@/utils/cn'
import ConfirmModal from '@/components/ui/ConfirmModal'
import { getSettingsSections } from '@/lib/settingsSections'
import HugeIcon from '@/components/ui/HugeIcon'

type NavItem = {
  label: string
  to: string
  icon: React.ReactNode
  disabled?: boolean
}

function SidebarLink({ to, icon, label, disabled = false, collapsed = false }: NavItem & { collapsed?: boolean }) {
  if (disabled) {
    return (
      <span
        title={label}
        className="flex items-center gap-2.5 rounded-[10px] px-3 py-2 text-[13px] font-medium text-tertiary cursor-not-allowed opacity-50"
      >
        <span className="shrink-0">{icon}</span>
        {!collapsed && label}
      </span>
    )
  }
  return (
    <NavLink
      to={to}
      end={to.endsWith('/dashboard')}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2.5 rounded-[10px] px-3 py-2 text-[13px] font-medium transition-colors duration-150',
          collapsed ? 'justify-center px-2' : '',
          isActive
            ? 'bg-accent/10 text-accent'
            : 'text-secondary hover:bg-[#f0f0f2] hover:text-primary',
        )
      }
    >
      <span className="shrink-0">{icon}</span>
      {!collapsed && label}
    </NavLink>
  )
}

function SidebarSection({ title, children, collapsed }: { title?: string; children: React.ReactNode; collapsed?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      {title && !collapsed && (
        <p className="px-3 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wider text-tertiary">
          {title}
        </p>
      )}
      {title && collapsed && <div className="mt-2 mb-1 border-t border-border mx-2" />}
      {children}
    </div>
  )
}

export default function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const { projectId } = useParams<{ projectId?: string }>()
  const { project, isAdminOrOwner } = useProject()
  const { logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const inSettings = location.pathname.includes('/settings')

  const [projectsOpen, setProjectsOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(() => inSettings)
  const [projects, setProjects] = useState<Project[]>([])
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const dropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!projectsOpen) return
    listProjects().then(setProjects).catch(() => {})
    const handler = (e: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) {
        setProjectsOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [projectsOpen])

  const sidebarWidth = collapsed ? 'w-14' : 'w-64'
  const settingsSections = getSettingsSections(projectId, { showAdminOnly: isAdminOrOwner })

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await logout()
      setLogoutConfirmOpen(false)
      navigate('/login')
    } finally {
      setLoggingOut(false)
    }
  }

  return (
    <>
      <aside
        className={`flex h-full ${sidebarWidth} shrink-0 flex-col border-r border-border bg-surface transition-all duration-200 overflow-hidden`}
      >
      {/* Brand + collapse toggle */}
      <div className="flex h-[64px] items-center border-b border-border px-3 justify-between shrink-0">
        {!collapsed && (
          <Link to="/projects" className="flex min-w-0 items-center gap-2 text-[15px] font-semibold text-primary hover:opacity-80 transition-opacity">
            <img src="/icon.svg" alt="" className="h-7 w-7 shrink-0 rounded-[8px]" />
            <span className="truncate">Ideas Studio</span>
          </Link>
        )}
        <button
          onClick={onToggle}
          className={cn(
            'flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] text-tertiary hover:bg-[#f0f0f2] hover:text-primary transition-colors',
            collapsed ? 'mx-auto' : 'ml-auto',
          )}
          title={collapsed ? 'Ouvrir la sidebar' : 'Fermer la sidebar'}
        >
          {collapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
        </button>
      </div>

      {/* Project switcher */}
      {projectId && project && !collapsed && (
        <div className="border-b border-border px-4 py-3 relative" ref={dropRef}>
          <button
            onClick={() => setProjectsOpen((v) => !v)}
            className="flex w-full items-center gap-2 rounded-[10px] px-2 py-1.5 hover:bg-[#f0f0f2] transition-colors text-left"
          >
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[6px] bg-accent/10 text-accent text-[10px] font-bold">
              {project.name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[12px] font-medium text-primary">{project.name}</p>
              <p className="truncate text-[11px] text-tertiary">{project.domain ?? 'Pas défini'}</p>
            </div>
            <ChevronDown size={12} className={`shrink-0 text-tertiary transition-transform ${projectsOpen ? 'rotate-180' : ''}`} />
          </button>

          {projectsOpen && (
            <div className="absolute left-3 right-3 top-full mt-1 z-50 rounded-[14px] border border-border bg-surface shadow-float overflow-hidden">
              {projects.length === 0 ? (
                <p className="px-4 py-3 text-[12px] text-tertiary">Aucun autre projet</p>
              ) : (
                projects.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setProjectsOpen(false)
                      navigate(`/projects/${p.id}/dashboard`)
                    }}
                    className="flex w-full items-center gap-2.5 px-3 py-2.5 hover:bg-[#f0f0f2] transition-colors text-left"
                  >
                    <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[6px] bg-accent/10 text-accent text-[10px] font-bold">
                      {p.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-[12px] font-medium text-primary">{p.name}</p>
                      <p className="truncate text-[11px] text-tertiary">{p.domain ?? 'Pas défini'}</p>
                    </div>
                    {p.id === projectId && <Check size={12} className="text-accent shrink-0" />}
                  </button>
                ))
              )}
              <div className="border-t border-border">
                <Link
                  to="/projects"
                  onClick={() => setProjectsOpen(false)}
                  className="flex items-center gap-2 px-3 py-2.5 text-[12px] text-accent hover:bg-[#f0f0f2] transition-colors"
                >
                  <FolderOpen size={13} />
                  Voir tous les projets
                </Link>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Navigation */}
      <nav className={cn('flex flex-1 flex-col gap-0.5 overflow-y-auto p-2', collapsed && 'items-center')}>
        {projectId ? (
          <>
            <SidebarSection collapsed={collapsed}>
              <SidebarLink
                to={`/projects/${projectId}/dashboard`}
                icon={<HugeIcon icon={DashboardSquare01Icon} size={16} />}
                label="Dashboard"
                collapsed={collapsed}
              />
            </SidebarSection>

            <SidebarSection title="Éditorial" collapsed={collapsed}>
              <SidebarLink to={`/projects/${projectId}/articles`} icon={<HugeIcon icon={File01Icon} size={16} />} label="Articles" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/categories`} icon={<HugeIcon icon={Folder01Icon} size={16} />} label="Catégories" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/ideas`} icon={<HugeIcon icon={BulbIcon} size={16} />} label="Idées" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/production`} icon={<HugeIcon icon={ClipboardListIcon} size={16} />} label="Production" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/validation`} icon={<HugeIcon icon={CheckListIcon} size={16} />} label="Validation" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/archives`} icon={<Archive size={16} />} label="Archives" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/media`} icon={<HugeIcon icon={Image01Icon} size={16} />} label="Médias" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/calendar`} icon={<HugeIcon icon={Calendar03Icon} size={16} />} label="Calendrier" collapsed={collapsed} />
            </SidebarSection>

            <SidebarSection title="Intelligence" collapsed={collapsed}>
              <SidebarLink to={`/projects/${projectId}/performance`} icon={<HugeIcon icon={ChartBarLineIcon} size={16} />} label="Performance" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/traffic`} icon={<HugeIcon icon={WorkflowCircle03Icon} size={16} />} label="Trafic" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/recommendations`} icon={<HugeIcon icon={MagicWand01Icon} size={16} />} label="Optimisations" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/generate`} icon={<HugeIcon icon={AiBrain01Icon} size={16} />} label="Génération IA" collapsed={collapsed} />
              <SidebarLink to={`/projects/${projectId}/notifications`} icon={<HugeIcon icon={BellIcon} size={16} />} label="Notifications" collapsed={collapsed} />
            </SidebarSection>

            <SidebarSection title="Projet" collapsed={collapsed}>
              {!collapsed ? (
                <>
                  <div
                    className={cn(
                      'flex items-center rounded-[10px] transition-colors duration-150',
                      inSettings ? 'bg-accent/10 text-accent' : 'text-secondary hover:bg-[#f0f0f2] hover:text-primary',
                    )}
                  >
                    <NavLink
                      to={`/projects/${projectId}/settings`}
                      onClick={() => setSettingsOpen(true)}
                      className="flex min-w-0 flex-1 items-center gap-2.5 px-3 py-2 text-[13px] font-medium"
                    >
                      <HugeIcon icon={Setting06Icon} size={16} className="shrink-0" />
                      <span className="truncate">Paramètres</span>
                    </NavLink>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.preventDefault()
                        event.stopPropagation()
                        setSettingsOpen((open) => !open)
                      }}
                      className="mr-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] text-current hover:bg-white/50"
                      aria-label={settingsOpen ? 'Replier les paramètres' : 'Déplier les paramètres'}
                    >
                      <ChevronDown
                        size={14}
                        className={cn('transition-transform duration-150', settingsOpen && 'rotate-180')}
                      />
                    </button>
                  </div>
                  {settingsOpen && (
                    <div className="ml-4 flex flex-col gap-0.5 border-l border-border pl-3">
                      {settingsSections.map((item) => (
                        <NavLink
                          key={item.key}
                          to={item.path}
                          end={item.end}
                          className={({ isActive }) =>
                            cn(
                              'rounded-[8px] px-2.5 py-1.5 text-[12px] font-medium transition-colors',
                              isActive ? 'text-accent' : 'text-secondary hover:text-primary',
                            )
                          }
                        >
                          {item.label}
                        </NavLink>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <SidebarLink to={`/projects/${projectId}/settings`} icon={<HugeIcon icon={Setting06Icon} size={16} />} label="Paramètres" collapsed={collapsed} />
              )}
            </SidebarSection>

            <div className={cn('mt-auto flex flex-col gap-0.5 border-t border-border pt-3', collapsed && 'w-full')}>
              <button
                type="button"
                onClick={() => setLogoutConfirmOpen(true)}
                title={collapsed ? 'Se déconnecter' : undefined}
                className={cn(
                  'flex items-center gap-2.5 rounded-[10px] px-3 py-2 text-[13px] font-medium text-secondary transition-colors hover:bg-[#f0f0f2] hover:text-primary',
                  collapsed && 'justify-center px-2',
                )}
              >
                <HugeIcon icon={Logout01Icon} size={16} className="shrink-0" />
                {!collapsed && 'Déconnexion'}
              </button>
            </div>
          </>
        ) : (
          <SidebarSection collapsed={collapsed}>
            <SidebarLink to="/projects" icon={<HugeIcon icon={Folder01Icon} size={16} />} label="Mes projets" collapsed={collapsed} />
          </SidebarSection>
        )}
      </nav>
      </aside>
      <ConfirmModal
        open={logoutConfirmOpen}
        onClose={() => setLogoutConfirmOpen(false)}
        onConfirm={handleLogout}
        title="Se déconnecter ?"
        description="Vous allez quitter votre session Ideas Studio sur cet appareil."
        confirmLabel="Se déconnecter"
        loading={loggingOut}
      />
    </>
  )
}
