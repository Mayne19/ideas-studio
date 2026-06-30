import { useCallback, useEffect, useState } from 'react'
import { Bell, CheckCheck, Loader2 } from '@/components/ui/hugeIcons'
import { useNavigate, useParams } from 'react-router-dom'
import { listNotifications, markNotificationRead, markAllNotificationsRead } from '@/api/notifications'
import type { Notification } from '@/types'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return "Aujourd'hui"
  if (days === 1) return 'Hier'
  if (days < 7) return `Il y a ${days} j`
  return new Date(iso).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' })
}

function levelColor(level: string): string {
  if (level === 'success') return 'bg-success/10 text-[#1a7a3a]'
  if (level === 'warning') return 'bg-warning/10 text-[#c07000]'
  if (level === 'error') return 'bg-danger/10 text-danger'
  return 'bg-accent/10 text-accent'
}

export default function NotificationsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [markingAll, setMarkingAll] = useState(false)

  const load = useCallback(async () => {
    if (!projectId) return
    setStatus('loading')
    try {
      const data = await listNotifications(projectId)
      setNotifications(data)
      setStatus('success')
    } catch {
      setStatus('error')
    }
  }, [projectId])

  useEffect(() => { load() }, [load]) // eslint-disable-line react-hooks/set-state-in-effect

  async function handleRead(id: string) {
    try {
      const updated = await markNotificationRead(id)
      setNotifications((prev) => prev.map((n) => n.id === id ? updated : n))
    } catch { /* ignore */ }
  }

  async function handleReadAll() {
    if (!projectId) return
    setMarkingAll(true)
    try {
      await markAllNotificationsRead(projectId)
      setNotifications((prev) => prev.map((n) => ({ ...n, read_at: n.read_at ?? new Date().toISOString() })))
    } catch { /* ignore */ }
    finally { setMarkingAll(false) }
  }

  if (status === 'loading') return <LoadingState />

  const unreadCount = notifications.filter((n) => !n.read_at).length

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-[20px] font-semibold text-primary tracking-tight">Notifications</h1>
          <p className="mt-0.5 text-[14px] text-secondary">
            Restez informé des événements importants de votre projet.
          </p>
        </div>
        {unreadCount > 0 && (
          <Button
            size="sm"
            variant="secondary"
            icon={markingAll ? <Loader2 size={13} className="animate-spin" /> : <CheckCheck size={13} />}
            onClick={handleReadAll}
            disabled={markingAll}
          >
            Tout marquer comme lu
          </Button>
        )}
      </div>

      {status === 'error' && (
        <div className="mb-4 flex items-start justify-between gap-3 rounded-[14px] bg-danger/5 px-4 py-3 text-[14px] text-secondary">
          <div>
            <p className="font-medium text-primary">Notifications momentanément indisponibles</p>
            <p className="mt-0.5 text-[12px] text-secondary">La page reste accessible. Réessayez dans quelques instants.</p>
          </div>
          <Button size="sm" variant="secondary" onClick={load}>Réessayer</Button>
        </div>
      )}

      {status !== 'error' && notifications.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-surface-soft text-tertiary">
            <Bell size={22} />
          </div>
          <div>
            <p className="text-[15px] font-medium text-primary">Aucune notification</p>
            <p className="mt-1 max-w-xs text-[14px] text-secondary">
              Vous serez notifié lors des événements importants de votre projet.
            </p>
          </div>
        </div>
      ) : status !== 'error' ? (
        <div className="flex flex-col gap-2">
          {notifications.map((n) => {
            const isUnread = !n.read_at
            return (
              <div
                key={n.id}
                onClick={() => { if (n.link) navigate(n.link); if (!n.read_at) handleRead(n.id) }}
                className={`flex items-start gap-3 rounded-[14px] border px-4 py-3 transition-colors ${
                  n.link ? 'cursor-pointer hover:bg-surface-soft' : ''
                } ${
                  isUnread
                    ? 'border-border bg-surface'
                    : 'border-border bg-surface opacity-60'
                }`}
              >
                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] ${levelColor(n.level)}`}>
                  <Bell size={14} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-[14px] ${isUnread ? 'font-semibold' : 'font-medium'} text-primary`}>
                    {n.title}
                  </p>
                  <p className="mt-0.5 text-[12px] text-tertiary leading-snug">{n.message}</p>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <span className="text-[12px] text-tertiary whitespace-nowrap">{timeAgo(n.created_at)}</span>
                  {isUnread && (
                    <button
                      type="button"
                      onClick={() => handleRead(n.id)}
                      className="rounded-[6px] bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent hover:bg-accent/20 transition-colors"
                    >
                      Marquer comme lu
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
