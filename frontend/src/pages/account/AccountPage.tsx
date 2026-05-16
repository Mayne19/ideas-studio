import { useState } from 'react'
import { User, Mail, Camera, Check, Loader2, AtSign, Moon } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { api } from '@/api/client'
import { checkUsername } from '@/api/auth'
import Button from '@/components/ui/Button'
import CopyButton from '@/components/ui/CopyButton'

export default function AccountPage() {
  const { user, refreshUser } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const [name, setName] = useState(user?.name ?? '')
  const [username, setUsername] = useState(user?.username ?? '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const initials = name
    ? name.split(' ').map((w) => w[0]).join('').toUpperCase().slice(0, 2)
    : '?'

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      const payload: Record<string, string> = { name: name.trim() }
      if (username.trim()) {
        const clean = username.trim().replace(/^@/, '')
        const result = await checkUsername(clean)
        if (!result.available && clean !== user?.username) {
          setError('Ce nom d\'utilisateur est déjà pris.')
          setSaving(false)
          return
        }
        payload.username = clean
      } else {
        payload.username = ''
      }
      await api.patch('/auth/me', payload)
      await refreshUser()
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de sauvegarder les modifications.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-6">
        <h1 className="text-[20px] font-semibold text-primary tracking-tight">Mon profil</h1>
        <p className="mt-0.5 text-[13px] text-secondary">
          Gérez vos informations personnelles.
        </p>
      </div>

      {/* Avatar */}
      <div className="mb-6 flex items-center gap-4">
        <div className="relative">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/10 text-accent text-[22px] font-bold">
            {initials}
          </div>
          <button
            className="absolute bottom-0 right-0 flex h-6 w-6 items-center justify-center rounded-full bg-surface border border-border text-tertiary hover:bg-[#f0f0f2] transition-colors"
            title="Photo de profil bientôt disponible"
            onClick={() => {}}
          >
            <Camera size={11} />
          </button>
        </div>
        <div>
          <p className="text-[13px] font-medium text-primary">{user?.name}</p>
          <p className="text-[12px] text-tertiary">{user?.email}</p>
        </div>
      </div>

      <form onSubmit={handleSave} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-[12px] font-medium text-secondary">Nom affiché</label>
          <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 focus-within:ring-1 focus-within:ring-accent/30 focus-within:border-accent/50 transition-colors">
            <User size={14} className="text-tertiary shrink-0" />
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Votre nom"
              className="flex-1 bg-transparent text-[13px] text-primary outline-none placeholder:text-tertiary"
            />
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[12px] font-medium text-secondary">Email</label>
          <div className="flex items-center gap-2 rounded-[10px] border border-border bg-[#f5f5f7] px-3 py-2">
            <Mail size={14} className="text-tertiary shrink-0" />
            <span className="text-[13px] text-tertiary">{user?.email}</span>
          </div>
          <p className="text-[11px] text-tertiary">L'email ne peut pas être modifié.</p>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[12px] font-medium text-secondary">Nom d'utilisateur</label>
          <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 focus-within:ring-1 focus-within:ring-accent/30 focus-within:border-accent/50 transition-colors">
            <AtSign size={14} className="text-tertiary shrink-0" />
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="votre-pseudo"
              className="flex-1 bg-transparent text-[13px] text-primary outline-none placeholder:text-tertiary"
            />
            {user?.username && (
              <CopyButton value={`@${user.username}`} label="Copier mon @username" />
            )}
          </div>
          <p className="text-[11px] text-tertiary">
            Les autres membres peuvent vous ajouter avec @{username || 'votre-pseudo'}.
          </p>
        </div>

        <div className="flex items-center justify-between gap-4 rounded-[14px] border border-border bg-surface px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px] bg-accent/10 text-accent">
              <Moon size={15} />
            </span>
            <div>
              <p className="text-[13px] font-medium text-primary">Mode sombre</p>
              <p className="text-[11px] text-tertiary">Choix sauvegardé sur cet appareil.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={toggleTheme}
            className={`relative h-7 w-12 rounded-full transition-colors ${isDark ? 'bg-accent' : 'bg-[#d8d8dc]'}`}
            aria-pressed={isDark}
            aria-label="Mode sombre"
          >
            <span
              className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-transform ${
                isDark ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {error && (
          <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
            {error}
          </div>
        )}

        <div className="flex items-center gap-2 pt-1">
          <Button type="submit" loading={saving} icon={saving ? <Loader2 size={14} className="animate-spin" /> : undefined}>
            Sauvegarder
          </Button>
          {saved && (
            <span className="flex items-center gap-1 text-[13px] text-[#1a7a3a]">
              <Check size={14} />
              Sauvegardé
            </span>
          )}
        </div>
      </form>

      {/* Password section — coming soon */}
      <div className="mt-8 border-t border-border pt-6">
        <h2 className="text-[15px] font-semibold text-primary mb-1">Mot de passe</h2>
        <p className="text-[13px] text-secondary mb-3">
          La modification du mot de passe sera disponible prochainement.
        </p>
        <button disabled className="rounded-[10px] border border-border bg-[#f5f5f7] px-4 py-2 text-[13px] text-tertiary cursor-not-allowed opacity-50">
          Changer le mot de passe
        </button>
      </div>
    </div>
  )
}
