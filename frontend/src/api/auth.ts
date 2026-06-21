import { api } from './client'
import type { User, LoginResponse } from '@/types'

export function login(email: string, password: string): Promise<LoginResponse> {
  return api.post<LoginResponse>('/auth/login', { email, password })
}

export function register(name: string, email: string, password: string, username?: string): Promise<User> {
  return api.post<User>('/auth/register', { name, email, password, username: username || undefined })
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
