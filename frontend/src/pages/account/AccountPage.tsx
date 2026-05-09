import { useState } from 'react'
import { User, Mail, Camera, Check, Loader2 } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import Button from '@/components/ui/Button'

export default function AccountPage() {
  const { user, refreshUser } = useAuth()
  const [name, setName] = useState(user?.name ?? '')
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
      await api.patch('/auth/me', { name: name.trim() })
      await refreshUser()
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch {
      setError('Impossible de sauvegarder les modifications.')
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
