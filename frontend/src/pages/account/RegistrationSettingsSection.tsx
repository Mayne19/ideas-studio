import { useEffect, useState } from 'react'
import { getRegistrationSettings, updateRegistrationSettings } from '@/api/auth'
import PageSection from '@/components/ui/PageSection'
import ToggleSwitch from '@/components/ui/ToggleSwitch'

// Réglage d'instance réservé au staff : inscription libre ou sur invitation.
export default function RegistrationSettingsSection() {
  const [open, setOpen] = useState<boolean | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    getRegistrationSettings()
      .then((s) => { if (!cancelled) setOpen(s.open) })
      .catch(() => { if (!cancelled) setError('Impossible de charger le réglage des inscriptions.') })
    return () => { cancelled = true }
  }, [])

  async function handleChange(next: boolean) {
    setSaving(true)
    setError('')
    try {
      const res = await updateRegistrationSettings(next)
      setOpen(res.open)
    } catch {
      setError("Impossible d'enregistrer le réglage.")
    } finally {
      setSaving(false)
    }
  }

  return (
    <PageSection
      title="Administration de l'instance"
      description="Réglages globaux, visibles uniquement par l'administrateur de l'instance."
    >
      <ToggleSwitch
        checked={open === true}
        onChange={handleChange}
        disabled={open === null || saving}
        label="Inscription libre"
        description="Désactivée : seules les personnes invitées à un projet peuvent créer un compte (recommandé)."
        ariaLabel="Autoriser l'inscription libre sans invitation"
      />
      {error && <p className="mt-2 text-[12px] text-danger">{error}</p>}
    </PageSection>
  )
}
