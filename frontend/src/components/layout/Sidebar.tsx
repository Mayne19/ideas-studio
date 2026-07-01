import { useEffect, useRef, useState } from 'react'
import { NavLink, Link, useParams, useLocation, useNavigate } from 'react-router-dom'
import {
  FolderOpen,
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
  Check,
} from '@/components/ui/hugeIcons'
import {
  Calendar03Icon,
  ChartBarLineIcon,
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
        className="flex h-8 items-center gap-2 rounded-[6px] px-2.5 text-[14px] font-medium text-tertiary cursor-not-allowed opacity-50"
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
          'flex h-8 items-center gap-2 rounded-[6px] px-2.5 text-[14px] font-medium transition-colors duration-150',
          collapsed ? 'justify-center px-2' : '',
          isActive
            ? 'bg-accent/6 text-primary'
            : 'text-secondary hover:bg-surface-soft hover:text-primary',
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
        <p className="px-2.5 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-widest text-tertiary">
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

  const sidebarWidth = collapsed ? 'w-14' : 'w-52'
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
        className={`flex h-full ${sidebarWidth} shrink-0 flex-col border-r-2 border-border bg-transparent transition-all duration-200 overflow-hidden`}
      >
        {/* Brand + collapse toggle */}
        <div className="flex h-16 shrink-0 items-center justify-between border-b-2 border-border px-3">
          {!collapsed && (
            <Link to="/projects" className="flex min-w-0 items-center gap-2 text-[15px] font-semibold text-primary hover:opacity-80 transition-opacity">
              <img src="/icon.svg" alt="" className="h-6 w-6 shrink-0 rounded-[6px]" />
              <span className="truncate">Ideas Studio</span>
            </Link>
          )}
          <button
            onClick={onToggle}
            className={cn(
              'flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] text-tertiary hover:bg-surface-soft hover:text-primary transition-colors',
              collapsed ? 'mx-auto' : 'ml-auto',
            )}
            title={collapsed ? 'Ouvrir la sidebar' : 'Fermer la sidebar'}
          >
            {collapsed ? <PanelLeftOpen size={14} /> : <PanelLeftClose size={14} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className={cn('flex flex-1 flex-col gap-0.5 overflow-y-auto p-2', collapsed && 'items-center')}>
          {projectId ? (
            <>
              <SidebarSection collapsed={collapsed}>
                <SidebarLink
                  to={`/projects/${projectId}/dashboard`}
                  icon={<HugeIcon icon={DashboardSquare01Icon} size={15} />}
                  label="Dashboard"
                  collapsed={collapsed}
                />
              </SidebarSection>

              <SidebarSection title="Éditorial" collapsed={collapsed}>
                <SidebarLink to={`/projects/${projectId}/pipeline`} icon={<HugeIcon icon={WorkflowCircle03Icon} size={15} />} label="Pipeline" collapsed={collapsed} />
                <SidebarLink to={`/projects/${projectId}/articles`} icon={<HugeIcon icon={File01Icon} size={15} />} label="Articles" collapsed={collapsed} />
                <SidebarLink to={`/projects/${projectId}/categories`} icon={<HugeIcon icon={Folder01Icon} size={15} />} label="Catégories" collapsed={collapsed} />
                <SidebarLink to={`/projects/${projectId}/media`} icon={<HugeIcon icon={Image01Icon} size={15} />} label="Médias" collapsed={collapsed} />
                <SidebarLink to={`/projects/${projectId}/calendar`} icon={<HugeIcon icon={Calendar03Icon} size={15} />} label="Calendrier" collapsed={collapsed} />
              </SidebarSection>

              <SidebarSection title="Analytics" collapsed={collapsed}>
                <SidebarLink to={`/projects/${projectId}/analytics`} icon={<HugeIcon icon={ChartBarLineIcon} size={15} />} label="Analytics" collapsed={collapsed} />
                <SidebarLink to={`/projects/${projectId}/recommendations`} icon={<HugeIcon icon={MagicWand01Icon} size={15} />} label="Optimisations" collapsed={collapsed} />
              </SidebarSection>

              <SidebarSection title="Projet" collapsed={collapsed}>
                {collapsed ? (
                  <SidebarLink
                    to={`/projects/${projectId}/settings`}
                    icon={<HugeIcon icon={Setting06Icon} size={15} />}
                    label="Paramètres"
                    collapsed={collapsed}
                  />
                ) : (
                  <>
                  <div
                    className={cn(
                      'flex h-8 items-center rounded-[6px] transition-colors duration-150',
                      inSettings ? 'bg-accent/6 text-primary' : 'text-secondary hover:bg-surface-soft hover:text-primary',
                    )}
                  >
                    <NavLink
                      to={`/projects/${projectId}/settings`}
                      onClick={() => setSettingsOpen(true)}
                      className="flex h-full min-w-0 flex-1 items-center gap-2 px-2.5 text-[14px] font-medium"
                    >
                      <HugeIcon icon={Setting06Icon} size={15} className="shrink-0" />
                      <span className="truncate">Paramètres</span>
                    </NavLink>
                    <button
                      type="button"
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); setSettingsOpen((o) => !o) }}
                      className="mr-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-[6px] text-current hover:bg-surface-soft"
                    >
                      <ChevronDown size={12} className={cn('transition-transform duration-150', settingsOpen && 'rotate-180')} />
                    </button>
                  </div>
                  {settingsOpen && (
                    <div className="ml-4 flex flex-col gap-0.5 border-l border-border pl-2.5">
                      {settingsSections.map((item) => (
                        <NavLink
                          key={item.key}
                          to={item.path}
                          end={item.end}
                          className={({ isActive }) =>
                            cn(
                              'rounded-[6px] px-2 py-1.5 text-[11px] font-medium transition-colors',
                              isActive ? 'text-primary' : 'text-secondary hover:text-primary',
                            )
                          }
                        >
                          {item.label}
                        </NavLink>
                      ))}
                    </div>
                  )}
                  </>
                )}
              </SidebarSection>
            </>
          ) : (
            <SidebarSection collapsed={collapsed}>
              <SidebarLink to="/projects" icon={<HugeIcon icon={Folder01Icon} size={15} />} label="Mes projets" collapsed={collapsed} />
            </SidebarSection>
          )}
        </nav>

        {/* Footer — style Vercel */}
        <div className="shrink-0 border-t border-border p-2 flex flex-col gap-1" ref={dropRef}>
          {/* Project switcher */}
          {projectId && project && (
            <div className="relative">
              <button
                onClick={() => setProjectsOpen((v) => !v)}
                className={cn(
                  'flex w-full items-center gap-2 rounded-[6px] px-2 py-1.5 hover:bg-surface-soft transition-colors text-left',
                  projectsOpen && 'bg-surface-soft',
                )}
              >
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[6px] bg-primary text-white text-[10px] font-bold">
                  {project.name.charAt(0).toUpperCase()}
                </div>
                {!collapsed && (
                  <>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[11px] font-medium text-primary leading-tight">{project.name}</p>
                      <p className="truncate text-[10px] text-tertiary leading-tight">{project.domain ?? 'Sans domaine'}</p>
                    </div>
                    <ChevronDown size={11} className={cn('shrink-0 text-tertiary transition-transform', projectsOpen && 'rotate-180')} />
                  </>
                )}
              </button>

              {projectsOpen && (
                <div className="absolute bottom-full left-0 right-0 mb-1 z-50 overflow-hidden rounded-[8px] border-2 border-border bg-bg shadow-none">
                  {projects.length === 0 ? (
                    <p className="px-3 py-2.5 text-[11px] text-tertiary">Aucun autre projet</p>
                  ) : (
                    projects.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => { setProjectsOpen(false); navigate(`/projects/${p.id}/dashboard`) }}
                        className="flex w-full items-center gap-2 px-3 py-2 hover:bg-surface-soft transition-colors text-left"
                      >
                        <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[4px] bg-primary text-white text-[9px] font-bold">
                          {p.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="truncate text-[11px] font-medium text-primary">{p.name}</p>
                          <p className="truncate text-[10px] text-tertiary">{p.domain ?? 'Sans domaine'}</p>
                        </div>
                        {p.id === projectId && <Check size={11} className="text-accent shrink-0" />}
                      </button>
                    ))
                  )}
                  <div className="border-t border-border">
                    <Link
                      to="/projects"
                      onClick={() => setProjectsOpen(false)}
                      className="flex items-center gap-2 px-3 py-2 text-[11px] text-secondary hover:bg-surface-soft hover:text-primary transition-colors"
                    >
                      <FolderOpen size={12} />
                      Tous les projets
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Logout */}
          <div className="flex flex-col gap-0.5">
            <button
              type="button"
              onClick={() => setLogoutConfirmOpen(true)}
              title={collapsed ? 'Se déconnecter' : undefined}
              className={cn(
                'flex h-8 w-full items-center gap-2 rounded-[6px] px-2.5 text-[14px] font-medium text-secondary transition-colors hover:bg-surface-soft hover:text-primary',
                collapsed && 'justify-center',
              )}
            >
              <HugeIcon icon={Logout01Icon} size={15} className="shrink-0" />
              {!collapsed && <span>Déconnexion</span>}
            </button>
          </div>
        </div>
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
