import { useState, useRef } from 'react'
import { User, Mail, Camera, Check, Loader2, AtSign, Lock, Copy } from '@/components/ui/hugeIcons'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { checkUsername } from '@/api/auth'
import PageSection from '@/components/ui/PageSection'
import Button from '@/components/ui/Button'
import type { User as AuthUser } from '@/types'

type AccountUser = Pick<AuthUser, 'first_name' | 'last_name' | 'name' | 'email' | 'username'> & {
  display_name?: string | null
}

function getDisplayName(user: AccountUser) {
  if (user.display_name) return user.display_name
  if (user.first_name) return user.first_name
  if (user.name) return user.name.split(' ')[0]
  return user.username ?? ''
}

export default function AccountPage() {
  const { user, refreshUser } = useAuth()
  const [firstName, setFirstName] = useState(user?.first_name ?? user?.name?.split(' ')[0] ?? '')
  const [lastName, setLastName] = useState(user?.last_name ?? user?.name?.split(' ').slice(1).join(' ') ?? '')
  const [displayName, setDisplayName] = useState(() => (user ? getDisplayName(user) : ''))
  const [username, setUsername] = useState(user?.username ?? '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const [avatarUploading, setAvatarUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordSaved, setPasswordSaved] = useState(false)
  const [passwordError, setPasswordError] = useState('')

  const [copied, setCopied] = useState(false)

  const effectiveDisplayName = displayName.trim() || firstName.trim() || username || '?'

  const initials = effectiveDisplayName
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  async function handleCopyUsername() {
    if (!user?.username) return
    try {
      await navigator.clipboard.writeText(`@${user.username}`)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setError("Impossible de copier le nom d'utilisateur.")
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    const finalName = displayName.trim() || firstName.trim()
    if (!finalName) return
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      const payload: Record<string, string> = { name: finalName, first_name: firstName.trim(), last_name: lastName.trim() }
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

  async function handleAvatarUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setAvatarUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const token = localStorage.getItem('token')
      const res = await fetch(`${import.meta.env['VITE_API_URL'] || 'http://localhost:8000'}/profile/avatar`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      })
      if (!res.ok) throw new Error('Upload échoué')
      await refreshUser()
    } catch {
      setError('Impossible de mettre à jour la photo de profil.')
    } finally {
      setAvatarUploading(false)
    }
  }

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault()
    if (!passwordForm.current_password || !passwordForm.new_password) return
    if (passwordForm.new_password.length < 6) {
      setPasswordError('Le mot de passe doit contenir au moins 6 caractères.')
      return
    }
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError('Les nouveaux mots de passe ne correspondent pas.')
      return
    }
    setPasswordSaving(true)
    setPasswordError('')
    setPasswordSaved(false)
    try {
      await api.post('/profile/password', { current_password: passwordForm.current_password, new_password: passwordForm.new_password })
      setPasswordSaved(true)
      setShowPasswordForm(false)
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
      setTimeout(() => setPasswordSaved(false), 2500)
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : 'Impossible de changer le mot de passe.')
    } finally {
      setPasswordSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="mb-2">
        <h1 className="text-[20px] font-semibold text-primary tracking-tight">Mon profil</h1>
        <p className="mt-0.5 text-[14px] text-secondary">
          Gérez vos informations personnelles.
        </p>
      </div>

      {/* Avatar */}
      <div className="flex items-center gap-4">
        <div className="relative">
          {user?.avatar_url ? (
            <img
              src={user.avatar_url}
              alt="Photo de profil"
              className="h-16 w-16 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-accent/10 text-accent text-[22px] font-bold">
              {initials}
            </div>
          )}
          <button
            className="absolute bottom-0 right-0 flex h-6 w-6 items-center justify-center rounded-full bg-surface border border-border text-tertiary hover:bg-surface-soft transition-colors"
            title="Changer la photo de profil"
            onClick={() => fileRef.current?.click()}
            disabled={avatarUploading}
          >
            {avatarUploading ? <Loader2 size={11} className="animate-spin" /> : <Camera size={11} />}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            className="hidden"
            onChange={handleAvatarUpload}
          />
        </div>
        <div>
          <p className="text-[14px] font-medium text-primary">{effectiveDisplayName}</p>
          <p className="text-[12px] text-tertiary">{user?.email ?? '—'}</p>
        </div>
      </div>

      <PageSection title="Informations personnelles" description="Gérez votre nom, email et nom d'utilisateur.">
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-[12px] font-medium text-secondary">Prénom</label>
              <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 focus-within:ring-1 focus-within:ring-accent/30 focus-within:border-accent/50 transition-colors">
                <User size={14} className="text-tertiary shrink-0" />
                <input
                  type="text"
                  value={firstName}
                  onChange={(e) => {
                    setFirstName(e.target.value)
                    if (!displayName || displayName === (user?.first_name ?? user?.name?.split(' ')[0] ?? '')) {
                      setDisplayName(e.target.value || username)
                    }
                  }}
                  placeholder="Votre prénom"
                  className="flex-1 bg-transparent text-[14px] text-primary outline-none placeholder:text-tertiary"
                />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[12px] font-medium text-secondary">Nom</label>
              <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 focus-within:ring-1 focus-within:ring-accent/30 focus-within:border-accent/50 transition-colors">
                <User size={14} className="text-tertiary shrink-0" />
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Votre nom"
                  className="flex-1 bg-transparent text-[14px] text-primary outline-none placeholder:text-tertiary"
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-[12px] font-medium text-secondary">Email</label>
              <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface-soft px-3 py-2">
                <Mail size={14} className="text-tertiary shrink-0" />
                <span className="text-[14px] text-tertiary">{user?.email ?? '—'}</span>
              </div>
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
                  className="flex-1 bg-transparent text-[14px] text-primary outline-none placeholder:text-tertiary"
                />
                {user?.username && (
                  <button
                    type="button"
                    onClick={handleCopyUsername}
                    className="flex h-7 w-7 items-center justify-center rounded-[8px] text-tertiary hover:bg-surface-muted hover:text-primary transition-colors shrink-0"
                    title="Copier mon @username"
                  >
                    {copied ? <Check size={12} className="text-success" /> : <Copy size={12} />}
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-[12px] font-medium text-secondary">Nom affiché</label>
              <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 focus-within:ring-1 focus-within:ring-accent/30 focus-within:border-accent/50 transition-colors">
                <User size={14} className="text-tertiary shrink-0" />
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder={firstName || username || 'Votre prénom'}
                  className="flex-1 bg-transparent text-[14px] text-primary outline-none placeholder:text-tertiary"
                />
              </div>
              <p className="text-[12px] text-tertiary">
                Par défaut, votre prénom est utilisé{username ? ', sinon votre nom d\'utilisateur' : ''}.
              </p>
            </div>

            {/* Profile preview */}
            <div className="flex flex-col gap-1">
              <label className="text-[12px] font-medium text-secondary">Aperçu du profil</label>
              <div className="flex items-center gap-3 rounded-[10px] border border-border bg-surface-soft px-3 py-2.5">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent text-[12px] font-bold">
                  {initials}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12px] font-medium text-primary">
                    {effectiveDisplayName}
                  </p>
                  {user?.username && (
                    <p className="truncate text-[12px] text-tertiary">@{user.username}</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">
              {error}
            </div>
          )}

          <div className="flex items-center gap-2 pt-1">
            <Button type="submit" loading={saving} icon={saving ? <Loader2 size={14} className="animate-spin" /> : undefined}>
              Sauvegarder
            </Button>
            {saved && (
              <span className="flex items-center gap-1 text-[14px] text-success">
                <Check size={14} />
                Sauvegardé
              </span>
            )}
          </div>
        </form>
      </PageSection>

      <PageSection
        title="Mot de passe"
        description={!showPasswordForm ? "Modifiez votre mot de passe." : undefined}
        action={!showPasswordForm ? (
          <button
            onClick={() => setShowPasswordForm(true)}
            className="flex items-center gap-1.5 rounded-[10px] bg-accent px-3.5 py-1.5 text-[12px] font-medium text-white transition-colors hover:bg-accent/90"
          >
            <Lock size={13} />
            Changer le mot de passe
          </button>
        ) : undefined}
      >
        {showPasswordForm && (
          <form onSubmit={handlePasswordChange} className="flex flex-col gap-3 mt-3">
            <div className="flex flex-col gap-1">
              <label className="text-[12px] font-medium text-secondary">Mot de passe actuel</label>
              <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 focus-within:ring-1 focus-within:ring-accent/30 focus-within:border-accent/50 transition-colors">
                <Lock size={14} className="text-tertiary shrink-0" />
                <input
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                  placeholder="Mot de passe actuel"
                  className="flex-1 bg-transparent text-[14px] text-primary outline-none placeholder:text-tertiary"
                />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[12px] font-medium text-secondary">Nouveau mot de passe</label>
              <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 focus-within:ring-1 focus-within:ring-accent/30 focus-within:border-accent/50 transition-colors">
                <Lock size={14} className="text-tertiary shrink-0" />
                <input
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                  placeholder="Nouveau mot de passe (6 caractères minimum)"
                  className="flex-1 bg-transparent text-[14px] text-primary outline-none placeholder:text-tertiary"
                />
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[12px] font-medium text-secondary">Confirmer le nouveau mot de passe</label>
              <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 focus-within:ring-1 focus-within:ring-accent/30 focus-within:border-accent/50 transition-colors">
                <Lock size={14} className="text-tertiary shrink-0" />
                <input
                  type="password"
                  value={passwordForm.confirm_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                  placeholder="Confirmez le nouveau mot de passe"
                  className="flex-1 bg-transparent text-[14px] text-primary outline-none placeholder:text-tertiary"
                />
              </div>
            </div>
            {passwordError && (
              <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">
                {passwordError}
              </div>
            )}
            <div className="flex items-center gap-2">
              <Button type="submit" loading={passwordSaving} icon={passwordSaving ? <Loader2 size={14} className="animate-spin" /> : undefined}>
                Valider le changement
              </Button>
              <button
                type="button"
                onClick={() => { setShowPasswordForm(false); setPasswordForm({ current_password: '', new_password: '', confirm_password: '' }); setPasswordError('') }}
                className="text-[12px] text-tertiary hover:text-secondary transition-colors"
              >
                Annuler
              </button>
              {passwordSaved && (
                <span className="flex items-center gap-1 text-[14px] text-success">
                  <Check size={14} />
                  Mot de passe modifié
                </span>
              )}
            </div>
          </form>
        )}
      </PageSection>
    </div>
  )
}
