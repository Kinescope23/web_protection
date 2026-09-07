import { useState } from 'react'
import { api } from '../contexts/AuthContext'
import { useNavigate, Link } from 'react-router-dom'

const MASTER_KEY = 'NP-MASTER-2026-SUPER-ADMIN'

export default function Register() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [inviteKey, setInviteKey] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const isMasterKey = inviteKey === MASTER_KEY

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    
    try {
      const res = await api.post('/auth/register', {
        email,
        username,
        password,
        invitation_key: inviteKey
      })
      setSuccess(true)
      setTimeout(() => navigate('/login'), res.data.role === 'admin' ? 3000 : 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации')
    } finally {
      setIsLoading(false)
    }
  }

  if (success) {
    return (
      <div style={{
        maxWidth: 400,
        margin: '100px auto',
        padding: 30,
        background: isMasterKey ? '#fef3c7' : '#f0fdf4',
        border: `1px solid ${isMasterKey ? '#fcd34d' : '#bbf7d0'}`,
        borderRadius: 10,
        boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        textAlign: 'center',
        fontFamily: 'Arial, sans-serif'
      }}>
        <h2 style={{ color: isMasterKey ? '#92400e' : '#166534' }}>
          {isMasterKey ? 'Администратор зарегистрирован!' : 'Регистрация успешна!'}
        </h2>
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
        Регистрация
      </h2>

      <div style={{
        background: '#eff6ff',
        borderLeft: '4px solid #3b82f6',
        padding: 12,
        marginBottom: 20,
        fontSize: '0.9em',
        color: '#1e40af',
        borderRadius: 4
      }}>
        <strong>Внимание:</strong> Для регистрации необходим ключ приглашения.
        <br />
        <span style={{ fontSize: '0.85em', marginTop: 5, display: 'block' }}>
          Обычные пользователи получают ключ у администратора.
        </span>
      </div>

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
            fontFamily: 'monospace',
            background: isMasterKey ? '#fef3c7' : '#f8f9fa'
          }}
        />

        {/* Подсказка о мастер-ключе */}
        {isMasterKey && (
          <div style={{
            background: '#fef3c7',
            border: '1px solid #fcd34d',
            padding: 10,
            marginBottom: 15,
            borderRadius: 5,
            fontSize: '0.85em',
            color: '#92400e'
          }}>
            <strong>Мастер-ключ активирован!</strong> Вы будете зарегистрированы как администратор.
          </div>
        )}

        {error && (
          <div style={{ color: '#e74c3c', marginBottom: 15, textAlign: 'center', fontSize: 14 }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading}
          style={{
            width: '100%',
            padding: 12,
            background: isLoading ? '#9ca3af' : (isMasterKey ? '#d97706' : '#27ae60'),
            color: 'white',
            border: 'none',
            borderRadius: 5,
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: 16,
            fontWeight: 'bold'
          }}
        >
          {isLoading ? 'Обработка...' : (isMasterKey ? 'Зарегистрировать администратора' : 'Зарегистрироваться')}
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