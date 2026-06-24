import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '@/context/AuthContext'
import LoadingState from '@/components/ui/LoadingState'

const LOADING_MESSAGES = [
  { after: 0, label: 'Chargement…' },
  { after: 5, label: 'Connexion au serveur…' },
  { after: 10, label: 'Réveil du serveur, cela peut prendre quelques instants…' },
]

type ProtectedRouteProps = {
  children: ReactNode
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { user, loading } = useAuth()
  const [message, setMessage] = useState(LOADING_MESSAGES[0]!.label)

  useEffect(() => {
    if (!loading) return
    const start = Date.now()
    const interval = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000
      let current = LOADING_MESSAGES[0]!.label
      for (const msg of LOADING_MESSAGES) {
        if (elapsed >= msg.after) current = msg.label
      }
      setMessage(current)
    }, 1000)
    return () => clearInterval(interval)
  }, [loading])

  if (loading) {
    return (
      <div className="flex min-h-full items-center justify-center">
        <LoadingState label={message} />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
