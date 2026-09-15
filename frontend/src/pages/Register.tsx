import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../contexts/AuthContext'

export default function Register() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    invitation_key: ''
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const res = await api.post('/auth/register', formData)
      setSuccess(true)
      // Если зарегистрировался как админ — покажем это
      if (res.data.role === 'admin') {
        setTimeout(() => navigate('/login'), 3000)
      } else {
        setTimeout(() => navigate('/login'), 2500)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации. Проверьте ключ и данные.')
    } finally {
      setIsLoading(false)
    }
  }

  if (success) {
    const isAdmin = formData.invitation_key === 'NP-MASTER-2026-SUPER-ADMIN'
    return (
      <div style={{ 
        maxWidth: 400, margin: '100px auto', padding: 30, 
        background: isAdmin ? '#fef3c7' : '#f0fdf4', 
        border: `1px solid ${isAdmin ? '#fcd34d' : '#bbf7d0'}`, 
        borderRadius: 8, textAlign: 'center' 
      }}>
        <h2 style={{ color: isAdmin ? '#92400e' : '#166534' }}>
          {isAdmin ? 'Администратор зарегистрирован!' : 'Регистрация успешна!'}
        </h2>
        <p>Перенаправление на страницу входа...</p>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 400, margin: '100px auto', padding: 30, background: 'white', borderRadius: 10, boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
      <h2 style={{ textAlign: 'center', color: '#667eea', marginBottom: 20 }}>Регистрация в Net Protector</h2>
      
      <div style={{ background: '#eff6ff', borderLeft: '4px solid #3b82f6', padding: 12, marginBottom: 20, fontSize: '0.9em', color: '#1e40af' }}>
        <strong>Внимание:</strong> Для регистрации необходим уникальный ключ приглашения.
        <br />
        <span style={{ fontSize: '0.85em', marginTop: 5, display: 'block' }}>
          Обычные пользователи получают ключ у администратора.
        </span>
      </div>

      <form onSubmit={handleSubmit}>
        <input
          name="email"
          type="email"
          placeholder="Email"
          value={formData.email}
          onChange={handleChange}
          required
          style={{ width: '100%', padding: 10, marginBottom: 10, boxSizing: 'border-box', border: '1px solid #ddd', borderRadius: 5 }}
        />
        <input
          name="username"
          type="text"
          placeholder="Имя пользователя (мин. 3 символа)"
          value={formData.username}
          onChange={handleChange}
          required
          minLength={3}
          style={{ width: '100%', padding: 10, marginBottom: 10, boxSizing: 'border-box', border: '1px solid #ddd', borderRadius: 5 }}
        />
        <input
          name="password"
          type="password"
          placeholder="Пароль (мин. 8 символов)"
          value={formData.password}
          onChange={handleChange}
          required
          minLength={8}
          style={{ width: '100%', padding: 10, marginBottom: 10, boxSizing: 'border-box', border: '1px solid #ddd', borderRadius: 5 }}
        />
        <input
          name="invitation_key"
          type="text"
          placeholder="Ключ приглашения"
          value={formData.invitation_key}
          onChange={handleChange}
          required
          style={{ 
            width: '100%', padding: 10, marginBottom: 10, 
            boxSizing: 'border-box', border: '1px solid #ddd', 
            borderRadius: 5, fontFamily: 'monospace',
            background: formData.invitation_key === 'NP-MASTER-2026-SUPER-ADMIN' ? '#fef3c7' : 'white'
          }}
        />
        
        {/* Подсказка о мастер-ключе */}
        {formData.invitation_key === 'NP-MASTER-2026-SUPER-ADMIN' && (
          <div style={{ 
            background: '#fef3c7', border: '1px solid #fcd34d', 
            padding: 10, marginBottom: 10, borderRadius: 5, 
            fontSize: '0.85em', color: '#92400e' 
          }}>
            <strong>Мастер-ключ активирован!</strong> Вы будете зарегистрированы как администратор.
          </div>
        )}
        
        {error && <div style={{ color: '#e74c3c', marginBottom: 10, textAlign: 'center', fontSize: '0.9em' }}>{error}</div>}
        
        <button 
          type="submit" 
          disabled={isLoading}
          style={{ 
            width: '100%', padding: 12, 
            background: isLoading ? '#9ca3af' : (formData.invitation_key === 'NP-MASTER-2026-SUPER-ADMIN' ? '#d97706' : '#667eea'), 
            color: 'white', border: 'none', borderRadius: 5, 
            cursor: isLoading ? 'not-allowed' : 'pointer', fontWeight: 'bold' 
          }}
        >
          {isLoading ? 'Обработка...' : (formData.invitation_key === 'NP-MASTER-2026-SUPER-ADMIN' ? '👑 Зарегистрировать администратора' : 'Зарегистрироваться')}
        </button>
      </form>
      
      <div style={{ marginTop: 20, textAlign: 'center', fontSize: '0.9em' }}>
        Уже есть аккаунт? <Link to="/login" style={{ color: '#667eea', textDecoration: 'none', fontWeight: 'bold' }}>Войти</Link>
      </div>
    </div>
  )
}