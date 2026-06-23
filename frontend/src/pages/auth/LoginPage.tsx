import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import AuthLayout from '@/components/layout/AuthLayout'
import Input from '@/components/ui/Input'
import Button from '@/components/ui/Button'

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (user) navigate('/projects', { replace: true })
  }, [navigate, user])

  if (user) return null

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (loading) return
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/projects', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Identifiants invalides')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="mb-1">
          <h2 className="text-[18px] font-semibold text-primary">Connexion</h2>
          <p className="mt-0.5 text-[13px] text-secondary">
            Entrez vos identifiants pour accéder à votre espace.
          </p>
        </div>

        {error && (
          <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
            {error}
          </div>
        )}

        <Input
          label="Adresse e-mail"
          type="email"
          placeholder="vous@exemple.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          autoFocus
        />
        <Input
          label="Mot de passe"
          type="password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
        <div className="-mt-2 flex justify-end">
          <Link to="/forgot-password" className="text-[12px] font-medium text-accent hover:underline">
            Mot de passe oublié ?
          </Link>
        </div>

        <Button type="submit" loading={loading} className="mt-1 w-full justify-center rounded-full">
          {loading ? 'Connexion en cours...' : 'Se connecter'}
        </Button>

        <p className="text-center text-[13px] text-secondary">
          Pas encore de compte ?{' '}
          <Link to="/register" className="font-medium text-accent hover:underline">
            Créer un compte
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
