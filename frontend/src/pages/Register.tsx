import { useState } from 'react'
import { api } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'

export default function Register() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [inviteKey, setInviteKey] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    try {
      await api.post('/auth/register', {
        email,
        username,
        password,
        invitation_key: inviteKey
      })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации')
    }
  }

  if (success) {
    return (
      <div style={{
        maxWidth: 400,
        margin: '100px auto',
        padding: 30,
        background: 'white',
        borderRadius: 10,
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        textAlign: 'center',
        fontFamily: 'Arial, sans-serif'
      }}>
        <h2 style={{ color: '#27ae60' }}>✅ Регистрация успешна!</h2>
        <p>Перенаправление на страницу входа...</p>
      </div>
    )
  }

  return (
    <div style={{
      maxWidth: 400,
      margin: '50px auto',
      padding: 30,
      background: 'white',
      borderRadius: 10,
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h2 style={{ textAlign: 'center', color: '#667eea', marginBottom: 25 }}>
        📝 Регистрация
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
          type="text"
          placeholder="Имя пользователя (3-64 символа)"
          value={username}
          onChange={e => setUsername(e.target.value)}
          required
          minLength={3}
          maxLength={64}
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
          placeholder="Пароль (минимум 8 символов)"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          minLength={8}
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
          type="text"
          placeholder="Ключ приглашения (от администратора)"
          value={inviteKey}
          onChange={e => setInviteKey(e.target.value)}
          required
          style={{
            width: '100%',
            padding: 12,
            marginBottom: 15,
            boxSizing: 'border-box',
            border: '1px solid #ddd',
            borderRadius: 5,
            background: '#f8f9fa'
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
            background: '#27ae60',
            color: 'white',
            border: 'none',
            borderRadius: 5,
            cursor: 'pointer',
            fontSize: 16,
            fontWeight: 'bold'
          }}
        >
          Зарегистрироваться
        </button>
      </form>

      <div style={{ textAlign: 'center', marginTop: 20, fontSize: 14 }}>
        Уже есть аккаунт?{' '}
        <Link
          to="/login"
          style={{
            color: '#667eea',
            textDecoration: 'none',
            fontWeight: 'bold'
          }}
        >
          Войти
        </Link>
      </div>
    </div>
  )
}