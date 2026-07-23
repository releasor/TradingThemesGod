import { apiClient } from './client'

export interface AuthUser {
  id: number
  username: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface RegisterInput {
  username: string
  password: string
}

export interface LoginInput {
  username: string
  password: string
}

export async function register(input: RegisterInput): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/register', input)
  return data
}

export async function login(input: LoginInput): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', input)
  return data
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const { data } = await apiClient.get<AuthUser>('/auth/me')
  return data
}
