import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,  // Для отправки cookies
})

api.interceptors.request.use((config) => {
  // Читаем CSRF-токен из cookie
  const csrfToken = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1]
  
  if (csrfToken && ['post', 'put', 'delete', 'patch'].includes(config.method?.toLowerCase() || '')) {
    config.headers['X-CSRF-Token'] = csrfToken
  }
  
  return config
})

interface User {
  id: number
  email: string
  username: string
  role: string
  is_2fa_enabled: boolean
  avatar_url: string | null
}

interface AuthContextType {
  user: User | null
  loading: boolean // <-- ДОБАВЛЕНО
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true) // <-- ДОБАВЛЕНО

  useEffect(() => {
    // === Обработка токена из URL после OAuth callback ===
    const urlParams = new URLSearchParams(window.location.search)
    const tokenFromUrl = urlParams.get('token')

    // Валидация формата JWT (header.payload.signature) перед сохранением
    // Это предотвращает Browser Storage Poisoning
    const jwtRegex = /^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/
    
    if (tokenFromUrl && jwtRegex.test(tokenFromUrl)) {
      localStorage.setItem('token', tokenFromUrl)
      window.history.replaceState({}, document.title, window.location.pathname)
    }

    // Проверяем наличие токена (из localStorage или только что из URL)
    const token = localStorage.getItem('token')
    if (token) {
      api.get('/users/me')
        .then(res => setUser(res.data))
        .catch(() => {
          localStorage.removeItem('token')
          setUser(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password })
    localStorage.setItem('token', res.data.access_token)
    const userRes = await api.get('/users/me')
    setUser(userRes.data)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export { api }