import { useState, useRef } from 'react'
import { User, Mail, Camera, Check, Loader2, AtSign, Moon, Lock, ArrowLeft, FolderOpen } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { useTheme } from '@/context/ThemeContext'
import { api } from '@/api/client'
import { checkUsername } from '@/api/auth'
import Button from '@/components/ui/Button'
import CopyButton from '@/components/ui/CopyButton'
import ToggleSwitch from '@/components/ui/ToggleSwitch'

export default function AccountPage() {
  const { user, refreshUser } = useAuth()
  const { isDark, toggleTheme } = useTheme()
  const [name, setName] = useState(user?.name ?? '')
  const [username, setUsername] = useState(user?.username ?? '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const [avatarUploading, setAvatarUploading] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const [passwordForm, setPasswordForm] = useState({ current_password: '', new_password: '' })
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordSaved, setPasswordSaved] = useState(false)
  const [passwordError, setPasswordError] = useState('')

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
    setPasswordSaving(true)
    setPasswordError('')
    setPasswordSaved(false)
    try {
      await api.post('/profile/password', passwordForm)
      setPasswordSaved(true)
      setPasswordForm({ current_password: '', new_password: '' })
      setTimeout(() => setPasswordSaved(false), 2500)
    } catch (err) {
      setPasswordError(err instanceof Error ? err.message : 'Impossible de changer le mot de passe.')
    } finally {
      setPasswordSaving(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-6">
        <div className="flex items-center gap-4 mb-4">
          <Link to="/projects" className="flex items-center gap-1.5 text-[13px] text-secondary hover:text-primary transition-colors">
            <ArrowLeft size={15} />
            Mes projets
          </Link>
          <Link to="/projects" className="flex items-center gap-1.5 text-[13px] text-accent hover:underline">
            <FolderOpen size={15} />
            Ouvrir le studio
          </Link>
        </div>
        <h1 className="text-[20px] font-semibold text-primary tracking-tight">Mon profil</h1>
        <p className="mt-0.5 text-[13px] text-secondary">
          Gérez vos informations personnelles.
        </p>
      </div>

      {/* Avatar */}
      <div className="mb-6 flex items-center gap-4">
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
            className="absolute bottom-0 right-0 flex h-6 w-6 items-center justify-center rounded-full bg-surface border border-border text-tertiary hover:bg-[#f0f0f2] transition-colors"
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
          <ToggleSwitch checked={isDark} onChange={() => toggleTheme()} ariaLabel="Activer le mode sombre" />
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
            <span className="flex items-center gap-1 text-[13px] text-success">
              <Check size={14} />
              Sauvegardé
            </span>
          )}
        </div>
      </form>

      {/* Password section */}
      <div className="mt-8 border-t border-border pt-6">
        <h2 className="text-[15px] font-semibold text-primary mb-1">Mot de passe</h2>
        <p className="text-[13px] text-secondary mb-4">
          Modifiez votre mot de passe.
        </p>
        <form onSubmit={handlePasswordChange} className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[12px] font-medium text-secondary">Mot de passe actuel</label>
            <div className="flex items-center gap-2 rounded-[10px] border border-border bg-surface px-3 py-2 focus-within:ring-1 focus-within:ring-accent/30 focus-within:border-accent/50 transition-colors">
              <Lock size={14} className="text-tertiary shrink-0" />
              <input
                type="password"
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                placeholder="Mot de passe actuel"
                className="flex-1 bg-transparent text-[13px] text-primary outline-none placeholder:text-tertiary"
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
                className="flex-1 bg-transparent text-[13px] text-primary outline-none placeholder:text-tertiary"
              />
            </div>
          </div>
          {passwordError && (
            <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
              {passwordError}
            </div>
          )}
          <div className="flex items-center gap-2">
            <Button type="submit" loading={passwordSaving} icon={passwordSaving ? <Loader2 size={14} className="animate-spin" /> : undefined}>
              Changer le mot de passe
            </Button>
            {passwordSaved && (
              <span className="flex items-center gap-1 text-[13px] text-success">
                <Check size={14} />
                Mot de passe modifié
              </span>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
