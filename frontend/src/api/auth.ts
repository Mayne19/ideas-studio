import { api } from './client'
import type { User, LoginResponse } from '@/types'

export function login(email: string, password: string): Promise<LoginResponse> {
  return api.post<LoginResponse>('/auth/login', { email, password }, { timeoutMs: 90000 })
}

export function register(firstName: string, lastName: string, email: string, password: string, username?: string, invitationToken?: string): Promise<User> {
  return api.post<User>('/auth/register', {
    first_name: firstName,
    last_name: lastName,
    email,
    password,
    username: username || undefined,
    invitation_token: invitationToken || undefined,
  })
}

export type RegistrationStatus = { open: boolean }

// Public : indique si l'inscription libre (sans invitation) est ouverte.
export function getRegistrationStatus(): Promise<RegistrationStatus> {
  return api.get<RegistrationStatus>('/auth/registration-status')
}

// Réservé au staff de l'instance.
export function getRegistrationSettings(): Promise<RegistrationStatus> {
  return api.get<RegistrationStatus>('/auth/registration-settings')
}

export function updateRegistrationSettings(open: boolean): Promise<RegistrationStatus> {
  return api.put<RegistrationStatus>('/auth/registration-settings', { open })
}

export function me(): Promise<User> {
  return api.get<User>('/auth/me')
}

export function logout(): Promise<void> {
  return api.post<void>('/auth/logout')
}

export function checkUsername(username: string): Promise<{ available: boolean }> {
  return api.post<{ available: boolean }>('/auth/username/check', { username })
}

export function forgotPassword(email: string): Promise<{ message: string; email_sent: boolean; dev_reset_url?: string | null }> {
  return api.post('/auth/forgot-password', { email })
}

export function resetPassword(token: string, password: string, password_confirm: string): Promise<{ message: string }> {
  return api.post('/auth/reset-password', { token, password, password_confirm })
}
