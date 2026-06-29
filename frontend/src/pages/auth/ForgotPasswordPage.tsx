import { useState } from 'react'
import { Link } from 'react-router-dom'
import AuthLayout from '@/components/layout/AuthLayout'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { forgotPassword } from '@/api/auth'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [devLink, setDevLink] = useState<string | null>(null)
  const [error, setError] = useState('')

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setMessage('')
    setDevLink(null)
    setLoading(true)
    try {
      const result = await forgotPassword(email)
      setMessage(result.message)
      setDevLink(result.dev_reset_url ?? null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de préparer la réinitialisation.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="mb-1">
          <h2 className="text-[18px] font-semibold text-primary">Mot de passe oublié</h2>
          <p className="mt-0.5 text-[13px] text-secondary">
            Entrez votre email. Si un compte existe, un lien de réinitialisation sera préparé.
          </p>
        </div>
        {error && <div className="rounded-[10px] bg-danger/8 px-3.5 py-2.5 text-[13px] text-danger">{error}</div>}
        {message && (
          <div className="rounded-[12px] bg-success/8 px-3.5 py-3 text-[13px] text-secondary">
            <p>{message}</p>
            {devLink && (
              <a href={devLink} className="mt-2 block break-all font-medium text-accent hover:underline">
                Ouvrir le lien de dev
              </a>
            )}
          </div>
        )}
        <Input
          label="Adresse e-mail"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="vous@exemple.com"
          autoComplete="email"
          required
          autoFocus
        />
        <Button type="submit" loading={loading} className="w-full justify-center rounded-full">
          Envoyer le lien
        </Button>
        <p className="text-center text-[13px] text-secondary">
          <Link to="/login" className="font-medium text-accent hover:underline">Retour à la connexion</Link>
        </p>
      </form>
    </AuthLayout>
  )
}
