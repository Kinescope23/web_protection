import { useState, useEffect } from 'react'
import { api } from '../contexts/AuthContext'

interface Token {
  id: number
  name: string
  scopes: string | null
  created: string
}

export default function Tokens() {
  const [tokens, setTokens] = useState<Token[]>([])
  const [newTokenName, setNewTokenName] = useState('')
  const [generatedToken, setGeneratedToken] = useState('')
  const [error, setError] = useState('')

  const fetchTokens = async () => {
    try {
      const res = await api.get('/users/me/tokens')
      setTokens(res.data)
    } catch (err) {
      console.error('Ошибка загрузки токенов', err)
    }
  }

  useEffect(() => {
    fetchTokens()
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTokenName) return
    try {
      const res = await api.post('/users/me/tokens', { name: newTokenName, scopes: ['read', 'write'] })
      setGeneratedToken(res.data.token)
      setNewTokenName('')
      fetchTokens()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка создания токена')
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 800, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1>🔑 Управление API токенами</h1>
      <p style={{ color: '#666', marginBottom: 20 }}>
        Создавайте токены для доступа внешних приложений к API системы. 
        <strong> Внимание:</strong> токен отображается только один раз при создании!
      </p>

      {/* Форма создания */}
      <form onSubmit={handleCreate} style={{ background: '#f8f9fa', padding: 20, borderRadius: 8, marginBottom: 30 }}>
        <h3 style={{ marginTop: 0 }}>Создать новый токен</h3>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            type="text"
            placeholder="Название токена (например, 'Мобильное приложение')"
            value={newTokenName}
            onChange={(e) => setNewTokenName(e.target.value)}
            style={{ flex: 1, padding: 10, borderRadius: 4, border: '1px solid #ccc' }}
            required
          />
          <button type="submit" style={{ padding: '10px 20px', background: '#667eea', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
            Создать
          </button>
        </div>
        {error && <p style={{ color: '#e74c3c', marginTop: 10 }}>{error}</p>}
      </form>

      {/* Отображение нового токена */}
      {generatedToken && (
        <div style={{ background: '#fff3cd', border: '1px solid #ffeaa7', padding: 20, borderRadius: 8, marginBottom: 30 }}>
          <h3 style={{ marginTop: 0, color: '#856404' }}>⚠️ Сохраните ваш токен!</h3>
          <p style={{ fontSize: '1.2em', fontFamily: 'monospace', background: '#fff', padding: 10, borderRadius: 4, wordBreak: 'break-all' }}>
            {generatedToken}
          </p>
          <button onClick={() => setGeneratedToken('')} style={{ marginTop: 10, padding: '8px 16px', background: '#856404', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
            Я сохранил токен, скрыть
          </button>
        </div>
      )}

      {/* Список токенов */}
      <h3>Ваши активные токены</h3>
      {tokens.length === 0 ? (
        <p style={{ color: '#888' }}>У вас пока нет созданных токенов.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white', borderRadius: 8, overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <thead>
            <tr style={{ background: '#2c3e50', color: 'white' }}>
              <th style={{ padding: 12, textAlign: 'left' }}>Название</th>
              <th style={{ padding: 12, textAlign: 'left' }}>Права (Scopes)</th>
              <th style={{ padding: 12, textAlign: 'left' }}>Дата создания</th>
            </tr>
          </thead>
          <tbody>
            {tokens.map((t) => (
              <tr key={t.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 12 }}>{t.name}</td>
                <td style={{ padding: 12 }}>{t.scopes || 'Все'}</td>
                <td style={{ padding: 12 }}>{new Date(t.created).toLocaleDateString('ru-RU')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}