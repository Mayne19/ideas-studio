import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ChevronRight, LogOut, User, FileText, FolderOpen, Loader2, Image, Settings } from '@/components/ui/hugeIcons'
import { BellDotIcon, BellIcon, Search01Icon } from '@hugeicons/core-free-icons'
import { useAuth } from '@/context/AuthContext'
import { useProject } from '@/context/ProjectContext'
import { globalSearch, type SearchResult } from '@/api/search'
import { listNotifications } from '@/api/notifications'
import type { Notification } from '@/types'
import { cn } from '@/utils/cn'
import ConfirmModal from '@/components/ui/ConfirmModal'
import HugeIcon from '@/components/ui/HugeIcon'

export default function Topbar() {
  const { user, logout } = useAuth()
  const { project } = useProject()
  const { projectId } = useParams<{ projectId?: string }>()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [notifOpen, setNotifOpen] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [searchFocused, setSearchFocused] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [logoutConfirmOpen, setLogoutConfirmOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const notifRef = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLDivElement>(null)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

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
    // Fetch notifications when dropdown opens
    if (projectId) {
      listNotifications(projectId).then(setNotifications).catch(() => setNotifications([]))
    }
    return () => document.removeEventListener('mousedown', handler)
  }, [notifOpen, projectId])

  useEffect(() => {
    if (!searchFocused) {
      const timer = setTimeout(() => {
        setSearchQuery('')
        setSearchResults([])
      }, 0)
      return () => clearTimeout(timer)
    }
  }, [searchFocused])

  async function handleSearchInput(value: string) {
    setSearchQuery(value)
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    if (!value.trim()) {
      setSearchResults([])
      setSearching(false)
      return
    }
    searchTimerRef.current = setTimeout(async () => {
      setSearching(true)
      try {
        const results = await globalSearch(value.trim())
        setSearchResults(results)
      } catch {
        setSearchResults([])
      } finally {
        setSearching(false)
      }
    }, 300)
  }

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

  function resultIcon(type: SearchResult['type']) {
    if (type === 'article') return <FileText size={13} />
    if (type === 'media') return <Image size={13} />
    if (type === 'page') return <Settings size={13} />
    return <FolderOpen size={13} />
  }

  return (
    <>
    <header className="flex h-[64px] shrink-0 items-center justify-between border-b border-border bg-bg px-6">
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
              <HugeIcon icon={Search01Icon} size={13} className="absolute left-2.5 text-tertiary pointer-events-none" />
              <input
                type="text"
                placeholder="Rechercher…"
                value={searchQuery}
                onChange={(e) => handleSearchInput(e.target.value)}
                onFocus={() => setSearchFocused(true)}
                onBlur={() => setTimeout(() => setSearchFocused(false), 200)}
                className="rounded-[6px] border border-border bg-surface-soft pl-7 pr-3 py-1.5 text-[13px] placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent/30 focus:border-accent/50 w-44 transition-all focus:w-56"
              />
            </div>
            {searchFocused && searchQuery && (
              <div className="absolute right-0 top-10 z-50 w-80 rounded-[8px] border border-border bg-bg p-2 shadow-float">
                {searching ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 size={16} className="animate-spin text-tertiary" />
                  </div>
                ) : searchResults.length === 0 ? (
                  <p className="py-4 text-center text-[12px] text-tertiary">Aucun résultat</p>
                ) : (
                  <div className="flex flex-col gap-0.5">
                    {searchResults.map((result) => (
                      <Link
                        key={`${result.type}-${result.id}`}
                        to={result.url}
                        className="flex items-center gap-2.5 rounded-[6px] px-2.5 py-2 hover:bg-surface-soft transition-colors"
                        onClick={() => setSearchFocused(false)}
                      >
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-accent/10 text-accent">
                          {resultIcon(result.type)}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-[13px] font-medium text-primary truncate">{result.title}</p>
                          {result.subtitle && (
                            <p className="text-[11px] text-tertiary truncate">{result.subtitle}</p>
                          )}
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Notifications bell */}
        {projectId && (
          <div className="relative" ref={notifRef}>
            <button
              onClick={() => setNotifOpen((v) => !v)}
              className="relative flex h-8 w-8 items-center justify-center rounded-full text-tertiary hover:bg-surface-soft hover:text-primary transition-colors"
              title="Notifications"
              aria-label="Notifications"
            >
              {notifications.filter((n) => !n.read_at).length > 0 ? <HugeIcon icon={BellDotIcon} size={16} /> : <HugeIcon icon={BellIcon} size={16} />}
              {notifications.filter((n) => !n.read_at).length > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-3.5 min-w-[14px] items-center justify-center rounded-full bg-danger px-1 text-[8px] font-bold text-white leading-none">
                  {notifications.filter((n) => !n.read_at).length > 9 ? '9+' : notifications.filter((n) => !n.read_at).length}
                </span>
              )}
            </button>

            {notifOpen && (
              <div className="absolute right-0 top-10 z-50 w-80 rounded-[8px] border border-border bg-bg p-2 shadow-float">
                <div className="flex items-center justify-between mb-1 px-1">
                  <p className="text-[13px] font-semibold text-primary">Notifications</p>
                  <button
                    onClick={() => { setNotifOpen(false); navigate(`/projects/${projectId}/notifications`) }}
                    className="text-[11px] text-accent hover:underline"
                  >
                    Voir tout →
                  </button>
                </div>
                <div className="flex max-h-64 flex-col gap-0.5 overflow-y-auto">
                  {notifications.filter((n) => !n.read_at).slice(0, 5).length === 0 ? (
                    <div className="flex flex-col items-center gap-2 py-6 text-center">
                      <HugeIcon icon={BellIcon} size={16} className="text-tertiary opacity-40" />
                      <p className="text-[12px] text-secondary">Aucune notification non lue.</p>
                      {notifications.length > 0 && (
                        <button
                          onClick={() => { setNotifOpen(false); navigate(`/projects/${projectId}/notifications`) }}
                          className="text-[11px] text-accent hover:underline"
                        >
                          Voir l'historique →
                        </button>
                      )}
                    </div>
                  ) : (
                    notifications.filter((n) => !n.read_at).slice(0, 5).map((n) => (
                      <button
                        key={n.id}
                        onClick={() => { setNotifOpen(false); if (n.link) navigate(n.link) }}
                        className={`flex w-full items-start gap-2 rounded-[6px] px-2.5 py-2 text-left transition-colors ${n.link ? 'hover:bg-surface-soft' : ''}`}
                      >
                        <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-[8px] ${
                          n.level === 'error' ? 'bg-danger/10 text-danger' :
                          n.level === 'warning' ? 'bg-warning/10 text-warning' :
                          n.level === 'success' ? 'bg-success/10 text-success' :
                          'bg-accent/10 text-accent'
                        }`}>
                          <HugeIcon icon={BellIcon} size={11} />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-[12px] font-medium text-primary truncate">{n.title}</p>
                          <p className="text-[11px] text-tertiary truncate">{n.message}</p>
                        </div>
                      </button>
                    ))
                  )}
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
            <div className="absolute right-0 top-10 z-50 min-w-[200px] rounded-[8px] border border-border bg-bg p-1.5 shadow-float">
              <div className="px-3 py-2 border-b border-border mb-1">
                <p className="text-[13px] font-medium text-primary truncate">{user?.name}</p>
                <p className="text-[12px] text-tertiary truncate">{user?.email}</p>
              </div>
              <Link
                to="/account"
                onClick={() => setMenuOpen(false)}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-[6px] px-3 py-2',
                  'text-[13px] text-secondary hover:bg-surface-soft hover:text-primary transition-colors',
                )}
              >
                <User size={14} />
                Mon compte
              </Link>
              <button
                onClick={() => setLogoutConfirmOpen(true)}
                className={cn(
                  'flex w-full items-center gap-2.5 rounded-[6px] px-3 py-2',
                  'text-[13px] text-secondary hover:bg-surface-soft hover:text-primary transition-colors',
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
