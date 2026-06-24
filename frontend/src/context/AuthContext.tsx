/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { login as apiLogin, register as apiRegister, me as apiMe, logout as apiLogout } from '@/api/auth'
import { healthCheck } from '@/api/client'
import type { User } from '@/types'

type AuthState = {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (firstName: string, lastName: string, email: string, password: string, username?: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState<boolean>(
    () => !!localStorage.getItem('token'),
  )

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return
    healthCheck().catch(() => {})
    apiMe()
      .then((profile) => setUser(profile))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const res = await apiLogin(email, password)
    localStorage.setItem('token', res.access_token)
    const profile = await apiMe()
    setUser(profile)
  }

  async function register(firstName: string, lastName: string, email: string, password: string, username?: string) {
    await apiRegister(firstName, lastName, email, password, username)
    await login(email, password)
  }

  async function refreshUser() {
    const profile = await apiMe()
    setUser(profile)
  }

  async function logout() {
    try {
      await apiLogout()
    } catch {
      // ignore backend errors on logout
    }
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth doit être utilisé dans AuthProvider')
  return ctx
}
