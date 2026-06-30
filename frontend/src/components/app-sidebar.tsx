import { useEffect, useRef, useState } from "react"
import { Link, NavLink, useParams, useLocation, useNavigate } from "react-router-dom"
import {
  LayoutDashboard,
  GitBranch,
  FileText,
  FolderTree,
  Image,
  Calendar,
  BarChart3,
  Sparkles,
  Settings,
  LogOut,
  ChevronDown,
  ChevronsUpDown,
  Check,
  FolderOpen,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react"
import { useProject } from "@/context/ProjectContext"
import { useAuth } from "@/context/AuthContext"
import { listProjects } from "@/api/projects"
import type { Project } from "@/types"
import { cn } from "@/utils/cn"
import ConfirmModal from "@/components/ui/ConfirmModal"
import { getSettingsSections } from "@/lib/settingsSections"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar"

type NavItem = {
  label: string
  to: string
  icon: React.ElementType
}

function NavLinkItem({ to, icon: Icon, label, end }: NavItem & { end?: boolean }) {
  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild className="text-[11px] font-medium">
        <NavLink
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              isActive && "!bg-sidebar-accent !text-sidebar-accent-foreground !font-medium",
            )
          }
        >
          <Icon className="!size-4" />
          <span>{label}</span>
        </NavLink>
      </SidebarMenuButton>
    </SidebarMenuItem>
  )
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { projectId } = useParams<{ projectId?: string }>()
  const { project, isAdminOrOwner } = useProject()
  const { logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const { open, toggleSidebar } = useSidebar()
  const inSettings = location.pathname.includes("/settings")

  const [settingsOpen, setSettingsOpen] = useState(inSettings)
  const [projectsOpen, setProjectsOpen] = useState(false)
  const [projectList, setProjectList] = useState<Project[]>([])
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const dropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!projectsOpen) return
    listProjects().then(setProjectList).catch(() => {})
    const handler = (e: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) {
        setProjectsOpen(false)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [projectsOpen])

  const settingsSections = getSettingsSections(projectId, {
    showAdminOnly: isAdminOrOwner,
  })

  async function handleLogout() {
    setLoggingOut(true)
    try {
      await logout()
      setLogoutConfirmOpen(false)
      navigate("/login")
    } finally {
      setLoggingOut(false)
    }
  }

  return (
    <>
      <Sidebar collapsible="icon" {...props}>
        <SidebarHeader>
          <div className="flex h-14 items-center justify-between border-b border-border px-3 shrink-0">
            {open && (
              <Link
                to="/projects"
                className="flex min-w-0 items-center gap-2 text-[14px] font-semibold text-primary hover:opacity-80 transition-opacity"
              >
                <img src="/icon.svg" alt="" className="h-6 w-6 shrink-0 rounded-[6px]" />
                <span className="truncate">Ideas Studio</span>
              </Link>
            )}
            <button
              onClick={toggleSidebar}
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-[6px] text-tertiary hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors",
                !open && "mx-auto",
                open && "ml-auto",
              )}
              title={open ? "Fermer la sidebar" : "Ouvrir la sidebar"}
            >
              {open ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
            </button>
          </div>
        </SidebarHeader>

        <SidebarContent>
          {projectId ? (
            <>
              <SidebarGroup>
                <SidebarMenu>
                  <NavLinkItem
                    to={`/projects/${projectId}/dashboard`}
                    icon={LayoutDashboard}
                    label="Dashboard"
                    end
                  />
                </SidebarMenu>
              </SidebarGroup>

              <SidebarGroup>
                <SidebarGroupLabel className="group-data-[collapsible=icon]:hidden text-[10px] font-semibold uppercase tracking-widest text-sidebar-foreground/50">
                  Éditorial
                </SidebarGroupLabel>
                <SidebarMenu>
                  <NavLinkItem to={`/projects/${projectId}/pipeline`} icon={GitBranch} label="Pipeline" />
                  <NavLinkItem to={`/projects/${projectId}/articles`} icon={FileText} label="Articles" />
                  <NavLinkItem to={`/projects/${projectId}/categories`} icon={FolderTree} label="Catégories" />
                  <NavLinkItem to={`/projects/${projectId}/media`} icon={Image} label="Médias" />
                  <NavLinkItem to={`/projects/${projectId}/calendar`} icon={Calendar} label="Calendrier" />
                </SidebarMenu>
              </SidebarGroup>

              <SidebarGroup>
                <SidebarGroupLabel className="group-data-[collapsible=icon]:hidden text-[10px] font-semibold uppercase tracking-widest text-sidebar-foreground/50">
                  Analytics
                </SidebarGroupLabel>
                <SidebarMenu>
                  <NavLinkItem to={`/projects/${projectId}/analytics`} icon={BarChart3} label="Analytics" />
                  <NavLinkItem to={`/projects/${projectId}/recommendations`} icon={Sparkles} label="Optimisations" />
                </SidebarMenu>
              </SidebarGroup>

              <SidebarGroup className={cn(!open && "hidden")}>
                <SidebarGroupLabel className="group-data-[collapsible=icon]:hidden text-[10px] font-semibold uppercase tracking-widest text-sidebar-foreground/50">
                  Projet
                </SidebarGroupLabel>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      asChild
                      className={cn(
                        "text-[11px] font-medium",
                        inSettings && "!bg-sidebar-accent !text-sidebar-accent-foreground !font-medium",
                      )}
                      onClick={() => setSettingsOpen(true)}
                    >
                      <NavLink
                        to={`/projects/${projectId}/settings`}
                        className={({ isActive }) => isActive ? "!bg-sidebar-accent !text-sidebar-accent-foreground !font-medium" : ""}
                      >
                        <Settings className="!size-4" />
                        <span>Paramètres</span>
                      </NavLink>
                    </SidebarMenuButton>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        setSettingsOpen((o) => !o)
                      }}
                      className="absolute right-1 top-1.5 flex aspect-square w-5 items-center justify-center rounded-md text-sidebar-foreground outline-none ring-sidebar-ring transition-transform hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    >
                      <ChevronDown
                        size={12}
                        className={cn(
                          "transition-transform duration-150",
                          settingsOpen && "rotate-180",
                        )}
                      />
                    </button>
                  </SidebarMenuItem>
                  {settingsOpen && (
                    <SidebarMenuSub>
                      {settingsSections.map((item) => (
                        <SidebarMenuSubItem key={item.key}>
                          <SidebarMenuSubButton asChild className="text-[11px] font-medium">
                            <NavLink
                              to={item.path}
                              end={item.end}
                              className={({ isActive }) =>
                                cn(isActive && "!font-medium")
                              }
                            >
                              {item.label}
                            </NavLink>
                          </SidebarMenuSubButton>
                        </SidebarMenuSubItem>
                      ))}
                    </SidebarMenuSub>
                  )}
                </SidebarMenu>
              </SidebarGroup>
            </>
          ) : (
            <SidebarGroup>
              <SidebarMenu>
                <NavLinkItem to="/projects" icon={FolderOpen} label="Mes projets" />
              </SidebarMenu>
            </SidebarGroup>
          )}
        </SidebarContent>

        <SidebarFooter className="border-t border-border">
          <div className="flex flex-col gap-0.5 p-2" ref={dropRef}>
            {/* Project switcher */}
            {projectId && project && (
              <div className="relative">
                <button
                  onClick={() => setProjectsOpen((v) => !v)}
                  className={cn(
                    "flex w-full items-center gap-2 rounded-[6px] px-2 py-1.5 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors text-left text-[11px]",
                    open ? "" : "justify-center",
                    projectsOpen && "bg-sidebar-accent",
                  )}
                >
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-[6px] bg-primary text-white text-[10px] font-bold">
                    {project.name.charAt(0).toUpperCase()}
                  </div>
                  {open && (
                    <>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-[12px] font-medium text-sidebar-foreground leading-tight">
                          {project.name}
                        </p>
                        <p className="truncate text-[10px] text-tertiary leading-tight">
                          {project.domain ?? "Sans domaine"}
                        </p>
                      </div>
                      <ChevronsUpDown size={11} className="shrink-0 text-tertiary" />
                    </>
                  )}
                </button>

                {projectsOpen && open && (
                  <div className="absolute bottom-full left-0 right-0 mb-1 z-50 rounded-[8px] border-2 border-border bg-bg shadow-md overflow-hidden">
                    {projectList.length === 0 ? (
                      <p className="px-3 py-2.5 text-[11px] text-tertiary">Aucun autre projet</p>
                    ) : (
                      projectList.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => {
                            setProjectsOpen(false)
                            navigate(`/projects/${p.id}/dashboard`)
                          }}
                          className="flex w-full items-center gap-2 px-3 py-2 hover:bg-surface-soft transition-colors text-left"
                        >
                          <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-[4px] bg-primary text-white text-[9px] font-bold">
                            {p.name.charAt(0).toUpperCase()}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="truncate text-[11px] font-medium text-primary">
                              {p.name}
                            </p>
                            <p className="truncate text-[10px] text-tertiary">
                              {p.domain ?? "Sans domaine"}
                            </p>
                          </div>
                          {p.id === projectId && (
                            <Check size={11} className="text-accent shrink-0" />
                          )}
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

            {/* Settings + Logout */}
            <div className="flex flex-col gap-0.5">
              {projectId && (
                <NavLink
                  to={`/projects/${projectId}/settings`}
                  className={({ isActive }) =>
                    cn(
                      "flex h-7 w-full items-center gap-2 rounded-[6px] px-2 text-[12px] font-medium transition-colors",
                      open ? "" : "justify-center",
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    )
                  }
                >
                  <Settings size={13} className="shrink-0" />
                  {open && <span>Paramètres</span>}
                </NavLink>
              )}
              <button
                type="button"
                onClick={() => setLogoutConfirmOpen(true)}
                className={cn(
                  "flex h-7 w-full items-center gap-2 rounded-[6px] px-2 text-[12px] font-medium text-sidebar-foreground/70 transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  open ? "" : "justify-center",
                )}
              >
                <LogOut size={13} className="shrink-0" />
                {open && <span>Déconnexion</span>}
              </button>
            </div>
          </div>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>

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
