import { useState } from 'react'
import { useAuth, api } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка входа')
    }
  }

  // OAuth вход через провайдера
  const handleOAuthLogin = (provider: string) => {
    // Перенаправляем на бэкенд, который редиректит на провайдера
    window.location.href = `/api/v1/auth/oauth/${provider}/login`
  }

  return (
    <div style={{
      maxWidth: 400,
      margin: '80px auto',
      padding: 30,
      background: 'white',
      borderRadius: 10,
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h2 style={{ textAlign: 'center', color: '#667eea', marginBottom: 25 }}>
        🔐 Вход в Net Protector
      </h2>

      <form onSubmit={handleSubmit}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
          style={{
            width: '100%',
            padding: 12,
            marginBottom: 15,
            boxSizing: 'border-box',
            border: '1px solid #ddd',
            borderRadius: 5
          }}
        />
        <input
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          style={{
            width: '100%',
            padding: 12,
            marginBottom: 15,
            boxSizing: 'border-box',
            border: '1px solid #ddd',
            borderRadius: 5
          }}
        />

        {error && (
          <div style={{ color: '#e74c3c', marginBottom: 15, textAlign: 'center', fontSize: 14 }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          style={{
            width: '100%',
            padding: 12,
            background: '#667eea',
            color: 'white',
            border: 'none',
            borderRadius: 5,
            cursor: 'pointer',
            fontSize: 16,
            fontWeight: 'bold'
          }}
        >
          Войти
        </button>
      </form>

      {/* Разделитель */}
      <div style={{
        textAlign: 'center',
        margin: '25px 0',
        color: '#95a5a6',
        fontSize: 14,
        position: 'relative'
      }}>
        <span style={{
          background: 'white',
          padding: '0 10px',
          position: 'relative',
          zIndex: 1
        }}>
          или войдите через
        </span>
        <div style={{
          position: 'absolute',
          top: '50%',
          left: 0,
          right: 0,
          height: '1px',
          background: '#ddd',
          zIndex: 0
        }}></div>
      </div>

      {/* Кнопки OAuth */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
        <button
          onClick={() => handleOAuthLogin('google')}
          style={{
            flex: 1,
            padding: 10,
            background: '#db4437',
            color: 'white',
            border: 'none',
            borderRadius: 5,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 'bold'
          }}
        >
          Google
        </button>
        <button
          onClick={() => handleOAuthLogin('github')}
          style={{
            flex: 1,
            padding: 10,
            background: '#333',
            color: 'white',
            border: 'none',
            borderRadius: 5,
            cursor: 'pointer',
            fontSize: 14,
            fontWeight: 'bold'
          }}
        >
          GitHub
        </button>
      </div>

      {/* Ссылка на регистрацию */}
      <div style={{ textAlign: 'center', marginTop: 20, fontSize: 14 }}>
        Нет аккаунта?{' '}
        <Link
          to="/register"
          style={{
            color: '#667eea',
            textDecoration: 'none',
            fontWeight: 'bold'
          }}
        >
          Зарегистрироваться
        </Link>
      </div>
    </div>
  )
}