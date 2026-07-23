import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuthStore } from '@/stores/auth'

const SETTINGS_PATH = '/settings/models'

export function useNavigateToSettings() {
  const navigate = useNavigate()
  const token = useAuthStore((state) => state.token)

  return useCallback(() => {
    if (token) {
      navigate(SETTINGS_PATH)
      return
    }
    navigate('/login', { state: { from: SETTINGS_PATH } })
  }, [navigate, token])
}
