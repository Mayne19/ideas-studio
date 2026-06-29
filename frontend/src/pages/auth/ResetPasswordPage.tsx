import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import AuthLayout from '@/components/layout/AuthLayout'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { resetPassword } from '@/api/auth'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const token = useMemo(() => params.get('token') ?? '', [params])
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    if (!token) {
      setError('Lien de réinitialisation manquant.')
      return
    }
    if (password !== passwordConfirm) {
      setError('Les mots de passe ne correspondent pas.')
      return
    }
    setLoading(true)
    try {
      await resetPassword(token, password, passwordConfirm)
      setDone(true)
      window.setTimeout(() => navigate('/login', { replace: true }), 1400)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de mettre à jour le mot de passe.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="mb-1">
          <h2 className="text-[18px] font-semibold text-primary">Nouveau mot de passe</h2>
          <p className="mt-0.5 text-[13px] text-secondary">
            Choisissez un mot de passe d’au moins 8 caractères.
          </p>
        </div>
        {error && <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">{error}</div>}
        {done && <div className="rounded-[10px] bg-success/8 px-3.5 py-2.5 text-[13px] text-success">Mot de passe mis à jour. Redirection...</div>}
        <Input
          label="Nouveau mot de passe"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="new-password"
          minLength={8}
          required
        />
        <Input
          label="Confirmer le mot de passe"
          type="password"
          value={passwordConfirm}
          onChange={(event) => setPasswordConfirm(event.target.value)}
          autoComplete="new-password"
          minLength={8}
          required
        />
        <Button type="submit" loading={loading} className="w-full justify-center rounded-full">
          Modifier le mot de passe
        </Button>
        <p className="text-center text-[13px] text-secondary">
          <Link to="/login" className="font-medium text-accent hover:underline">Retour à la connexion</Link>
        </p>
      </form>
    </AuthLayout>
  )
}
