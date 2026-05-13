import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ChevronRight, LogOut, User, Bell, Search } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useProject } from '@/context/ProjectContext'
import { cn } from '@/utils/cn'
import ConfirmModal from '@/components/ui/ConfirmModal'

export default function Topbar() {
  const { user, logout } = useAuth()
  const { project } = useProject()
  const { projectId } = useParams<{ projectId?: string }>()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [searchFocused, setSearchFocused] = useState(false)
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const notifRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  useEffect(() => {
    if (!notifOpen) return
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [notifOpen])

  async function handleLogout() {
    setLoggingOut(true)
    try {
      setMenuOpen(false)
      await logout()
      setLogoutConfirmOpen(false)
      navigate('/login')
    } finally {
      setLoggingOut(false)
    }
  }

  const initials = user?.name
    ? user.name
        .split(' ')
        .map((w) => w[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : '?'

  return (
    <>
    <header className="flex h-[64px] shrink-0 items-center justify-between border-b border-border bg-surface px-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-[13px]">
        <Link to="/projects" className="text-secondary hover:text-primary transition-colors">
          Projets
        </Link>
        {projectId && project && (
          <>
            <ChevronRight size={13} className="text-tertiary" />
            <Link
              to={`/projects/${projectId}/dashboard`}
              className="text-secondary hover:text-primary transition-colors"
            >
              {project.name}
            </Link>
          </>
        )}
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-2">
        {/* Search */}
        {projectId && (
          <div className="relative" ref={searchRef}>
            <div className="flex items-center gap-1.5">
              <Search size={13} className="absolute left-2.5 text-tertiary pointer-events-none" />
              <input
                type="text"
                placeholder="Rechercher…"
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setTimeout(() => setSearchFocused(false), 100)}
                className="rounded-[10px] border border-border bg-[#f0f0f2] pl-7 pr-3 py-1.5 text-[13px] placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent/30 focus:border-accent/50 w-44 transition-all focus:w-56"
              />
            </div>
            {searchFocused && (
              <div className="absolute right-0 top-10 z-50 w-64 rounded-[16px] border border-border bg-surface p-4 shadow-float">
                <p className="text-[12px] text-tertiary text-center">Recherche globale bientôt disponible</p>
              </div>
            )}
          </div>
        )}

        {/* Notifications bell */}
        {projectId && (
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setNotifOpen((v) => !v)}
              className="flex h-8 w-8 items-center justify-center rounded-full text-tertiary hover:bg-[#f0f0f2] hover:text-primary transition-colors"
              title="Notifications"
              aria-label="Notifications"
            >
              <Bell size={16} />
            </button>

            {notifOpen && (
              <div className="absolute right-0 top-10 z-50 w-72 rounded-[16px] border border-border bg-surface p-3 shadow-float">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[13px] font-semibold text-primary">Notifications</p>
                  <button
                    onClick={() => { setNotifOpen(false); navigate(`/projects/${projectId}/notifications`) }}
                    className="text-[11px] text-accent hover:underline"
                  >
                    Voir tout →
                  </button>
                </div>
                <div className="flex flex-col items-center gap-2 py-4 text-center">
                  <Bell size={18} className="text-tertiary opacity-40" />
                  <p className="text-[12px] text-secondary">
                    Les notifications en temps réel seront disponibles prochainement.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* User menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-accent/10 text-accent text-[12px] font-semibold hover:bg-accent/20 transition-colors"
            aria-label="Menu utilisateur"
          >
            {initials}
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-10 z-50 min-w-[200px] rounded-[16px] border border-border bg-surface p-1.5 shadow-float">
              <div className="px-3 py-2 border-b border-border mb-1">
                <p className="text-[13px] font-medium text-primary truncate">{user?.name}</p>
                <p className="text-[12px] text-tertiary truncate">{user?.email}</p>
              </div>
              <Link
                to="/account"
                onClick={() => setMenuOpen(false)}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-[10px] px-3 py-2',
                  'text-[13px] text-secondary hover:bg-[#f0f0f2] hover:text-primary transition-colors',
                )}
              >
                <User size={14} />
                Mon compte
              </Link>
              <button
                onClick={() => setLogoutConfirmOpen(true)}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-[10px] px-3 py-2',
                  'text-[13px] text-secondary hover:bg-[#f0f0f2] hover:text-primary transition-colors',
                )}
              >
                <LogOut size={14} />
                Se déconnecter
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
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
