import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { checkUsername } from '@/api/auth'
import AuthLayout from '@/components/layout/AuthLayout'
import Input from '@/components/ui/Input'
import Button from '@/components/ui/Button'

export default function RegisterPage() {
  const { register, user } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (user) {
    navigate('/projects', { replace: true })
    return null
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.')
      return
    }
    if (username.trim()) {
      const clean = username.trim().replace(/^@/, '')
      const result = await checkUsername(clean)
      if (!result.available) {
        setError('Ce nom d\'utilisateur est déjà pris.')
        return
      }
    }
    setLoading(true)
    try {
      await register(name, email, password, username.trim().replace(/^@/, '') || undefined)
      navigate('/projects', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la création du compte')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="mb-1">
          <h2 className="text-[18px] font-semibold text-primary">Créer un compte</h2>
          <p className="mt-0.5 text-[13px] text-secondary">
            Rejoignez Ideas Studio et commencez à produire du contenu SEO.
          </p>
        </div>

        {error && (
          <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">
            {error}
          </div>
        )}

        <Input
          label="Nom complet"
          type="text"
          placeholder="Jean Dupont"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          autoComplete="name"
          autoFocus
        />
        <Input
          label="Nom d'utilisateur"
          type="text"
          placeholder="@votre-pseudo"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          hint="Lettres, chiffres et tirets bas. Optionnel."
        />
        <Input
          label="Adresse e-mail"
          type="email"
          placeholder="vous@exemple.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
        />
        <Input
          label="Mot de passe"
          type="password"
          placeholder="8 caractères minimum"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="new-password"
          hint="Au moins 8 caractères"
        />

        <Button type="submit" loading={loading} className="mt-1 w-full justify-center rounded-full">
          Créer mon compte
        </Button>

        <p className="text-center text-[13px] text-secondary">
          Déjà un compte ?{' '}
          <Link to="/login" className="font-medium text-accent hover:underline">
            Se connecter
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
