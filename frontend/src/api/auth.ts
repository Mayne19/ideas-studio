import { api } from './client'
import type { User, LoginResponse } from '@/types'

export function login(email: string, password: string): Promise<LoginResponse> {
  return api.post<LoginResponse>('/auth/login', { email, password })
}

export function register(name: string, email: string, password: string): Promise<User> {
  return api.post<User>('/auth/register', { name, email, password })
}

export function me(): Promise<User> {
  return api.get<User>('/auth/me')
}

export function logout(): Promise<void> {
  return api.post<void>('/auth/logout')
}
