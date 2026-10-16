import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { checkUsername, getRegistrationStatus } from '@/api/auth'
import AuthLayout from '@/components/layout/AuthLayout'
import Input from '@/components/ui/Input'
import Button from '@/components/ui/Button'

export default function RegisterPage() {
  const { register, user } = useAuth()
  const navigate = useNavigate()
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  // Lien d'invitation : /register?invitation=<jeton>. Sans invitation,
  // l'inscription n'est possible que si l'administrateur l'a ouverte.
  const [searchParams] = useSearchParams()
  const invitationToken = searchParams.get('invitation') ?? ''
  const [registrationOpen, setRegistrationOpen] = useState<boolean | null>(null)

  useEffect(() => {
    if (invitationToken) return
    let cancelled = false
    getRegistrationStatus()
      .then((s) => { if (!cancelled) setRegistrationOpen(s.open) })
      .catch(() => { if (!cancelled) setRegistrationOpen(null) })
    return () => { cancelled = true }
  }, [invitationToken])

  const closed = !invitationToken && registrationOpen === false

  if (user) {
    navigate('/projects', { replace: true })
    return null
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!firstName.trim()) {
      setError('Le prénom est requis.')
      return
    }
    if (password.length < 8) {
      setError('Le mot de passe doit contenir au moins 8 caractères.')
      return
    }
    const clean = username.trim().replace(/^@/, '')
    if (!clean) {
      setError("Le nom d'utilisateur est requis.")
      return
    }
    if (!/^[a-zA-Z0-9_-]+$/.test(clean)) {
      setError('Le nom d\'utilisateur ne doit contenir que des lettres, chiffres, tirets et underscores.')
      return
    }
    const result = await checkUsername(clean)
    if (!result.available) {
      setError('Ce nom d\'utilisateur est déjà pris.')
      return
    }
    setLoading(true)
    try {
      await register(firstName.trim(), lastName.trim(), email, password, clean, invitationToken || undefined)
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
          <p className="mt-0.5 text-[14px] text-secondary">
            Rejoignez Ideas Studio et commencez à produire du contenu SEO.
          </p>
        </div>

        {closed && (
          <div className="rounded-[10px] bg-warning/10 px-3.5 py-2.5 text-[14px] text-secondary">
            Les inscriptions sont actuellement sur invitation uniquement. Utilisez le lien reçu par email
            ou demandez une invitation à un administrateur.
          </div>
        )}

        {invitationToken && (
          <div className="rounded-[10px] bg-surface-soft px-3.5 py-2.5 text-[14px] text-secondary">
            Vous avez été invité : créez votre compte avec l'adresse email qui a reçu l'invitation.
          </div>
        )}

        {error && (
          <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[14px] text-danger">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Prénom"
            type="text"
            placeholder="Jean"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            required
            autoComplete="given-name"
            autoFocus
          />
          <Input
            label="Nom"
            type="text"
            placeholder="Dupont"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            autoComplete="family-name"
          />
        </div>

        <Input
          label="Nom d'utilisateur"
          type="text"
          placeholder="@votre-pseudo"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          hint="Lettres, chiffres, tirets et underscores. Requis."
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

        <Button type="submit" loading={loading} disabled={closed} className="mt-1 w-full justify-center rounded-full">
          Créer mon compte
        </Button>

        <p className="text-center text-[14px] text-secondary">
          Déjà un compte ?{' '}
          <Link to="/login" className="font-medium text-accent hover:underline">
            Se connecter
          </Link>
        </p>
      </form>
    </AuthLayout>
  )
}
