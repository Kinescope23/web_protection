import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка входа')
    }
  }

  return (
    <div style={{ 
      maxWidth: 400, 
      margin: '100px auto', 
      padding: 30, 
      background: 'white', 
      borderRadius: 10, 
      boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
      fontFamily: 'Arial, sans-serif'
    }}>
      <h2 style={{ textAlign: 'center', color: '#667eea', marginTop: 0 }}>Вход в Net Protector</h2>
      <form onSubmit={handleSubmit}>
        <input 
          type="email" 
          placeholder="Email" 
          value={email} 
          onChange={e => setEmail(e.target.value)} 
          required 
          style={{ width: '100%', padding: 10, marginBottom: 10, boxSizing: 'border-box', border: '1px solid #ddd', borderRadius: 5 }} 
        />
        <input 
          type="password" 
          placeholder="Пароль" 
          value={password} 
          onChange={e => setPassword(e.target.value)} 
          required 
          style={{ width: '100%', padding: 10, marginBottom: 10, boxSizing: 'border-box', border: '1px solid #ddd', borderRadius: 5 }} 
        />
        {error && <div style={{ color: 'red', marginBottom: 10, textAlign: 'center' }}>{error}</div>}
        <button 
          type="submit" 
          style={{ width: '100%', padding: 10, background: '#667eea', color: 'white', border: 'none', borderRadius: 5, cursor: 'pointer' }}
        >
          Войти
        </button>
      </form>
    </div>
  )
}