import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { healthCheck } from '@/api/client'
import Button from '@/components/ui/Button'
import { Edit3, Eye, EyeOff } from '@/components/ui/hugeIcons'

const LOADING_MESSAGES = [
  { after: 0, label: 'Chargement…' },
  { after: 5, label: 'Connexion au serveur…' },
  { after: 10, label: 'Réveil du serveur, cela peut prendre quelques instants…' },
]

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingMessage, setLoadingMessage] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  useEffect(() => {
    if (user) navigate('/projects', { replace: true })
  }, [navigate, user])

  useEffect(() => {
    healthCheck().catch(() => {})
  }, [])

  useEffect(() => {
    if (!loading) return
    const start = Date.now()
    const interval = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000
      let current = LOADING_MESSAGES[0]!.label
      for (const msg of LOADING_MESSAGES) {
        if (elapsed >= msg.after) current = msg.label
      }
      setLoadingMessage(current)
    }, 1000)
    return () => clearInterval(interval)
  }, [loading])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (loading) return
    setError('')
    setLoading(true)
    setLoadingMessage(LOADING_MESSAGES[0]!.label)
    login(email, password)
      .then(() => navigate('/projects', { replace: true }))
      .catch((err) => setError(err instanceof Error ? err.message : 'Identifiants invalides'))
      .finally(() => { setLoading(false); setLoadingMessage('') })
  }

  if (user) return null

  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-6 bg-app p-6 md:p-10">
      <div className="flex w-full max-w-sm flex-col gap-6">
        <Link to="/" className="flex items-center gap-2 self-center text-[15px] font-semibold text-primary">
          <span className="flex size-7 items-center justify-center rounded-[8px] bg-primary text-white">
            <Edit3 size={16} />
          </span>
          Ideas Studio
        </Link>

        <div className="rounded-[10px] border-2 border-border bg-surface shadow-none">
          <div className="border-b border-border px-6 py-5 text-center">
            <h1 className="text-[20px] font-semibold leading-tight text-primary">Bon retour</h1>
            <p className="mt-1.5 text-[14px] leading-snug text-secondary">
              Connectez-vous avec votre adresse e-mail.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4 px-6 py-6">
            {error && (
              <div className="rounded-[8px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
                {error}
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-[13px] font-medium text-primary">
                Email
              </label>
              <input
                id="email"
                type="email"
                placeholder="vous@exemple.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                autoFocus
                className="h-10 w-full rounded-[8px] border border-border bg-surface px-3.5 text-[14px] text-primary outline-none transition-colors placeholder:text-tertiary hover:border-border-strong focus:border-accent focus:ring-2 focus:ring-accent/10"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex items-center">
                <label htmlFor="password" className="text-[13px] font-medium text-primary">
                  Mot de passe
                </label>
                <Link to="/forgot-password" className="ml-auto text-[12px] font-medium text-accent underline-offset-4 hover:underline">
                  Mot de passe oublié ?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="h-10 w-full rounded-[8px] border border-border bg-surface px-3.5 pr-10 text-[14px] text-primary outline-none transition-colors placeholder:text-tertiary hover:border-border-strong focus:border-accent focus:ring-2 focus:ring-accent/10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-[6px] text-tertiary transition-colors hover:bg-surface-soft hover:text-primary"
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <Button type="submit" loading={loading} className="mt-1 w-full justify-center">
              {loading ? 'Connexion…' : 'Se connecter'}
            </Button>

            {loading && (
              <p className="text-center text-[12px] text-tertiary">{loadingMessage}</p>
            )}

            <p className="text-center text-[13px] text-secondary">
              Pas encore de compte ?{' '}
              <Link to="/register" className="font-medium text-accent underline-offset-4 hover:underline">
                Créer un compte
              </Link>
            </p>
          </form>
        </div>

        <p className="px-6 text-center text-[12px] leading-relaxed text-tertiary">
          En continuant, vous acceptez nos conditions d’utilisation et notre politique de confidentialité.
        </p>
      </div>
    </main>
  )
}
