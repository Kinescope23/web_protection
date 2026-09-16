import { useState, useEffect, useRef } from 'react'
import { useAuth, api } from '../contexts/AuthContext'

interface SessionInfo {
  id: string
  ip_address: string
  user_agent: string
  created_at: string
  expires_at: string
  is_current: boolean
}

export default function Profile() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<'info' | 'password' | 'sessions' | 'avatar'>('info')

  return (
    <div style={{ padding: 20, maxWidth: 900, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: '#2c3e50', marginBottom: 20 }}>👤 Профиль</h1>

      {/* Вкладки */}
      <div style={{ display: 'flex', gap: 5, marginBottom: 25, borderBottom: '2px solid #ecf0f1' }}>
        <TabButton active={activeTab === 'info'} onClick={() => setActiveTab('info')}>Информация</TabButton>
        <TabButton active={activeTab === 'password'} onClick={() => setActiveTab('password')}>Смена пароля</TabButton>
        <TabButton active={activeTab === 'sessions'} onClick={() => setActiveTab('sessions')}>Активные сессии</TabButton>
        <TabButton active={activeTab === 'avatar'} onClick={() => setActiveTab('avatar')}>Аватар</TabButton>
      </div>

      {activeTab === 'info' && <InfoTab user={user} />}
      {activeTab === 'password' && <PasswordTab />}
      {activeTab === 'sessions' && <SessionsTab />}
      {activeTab === 'avatar' && <AvatarTab user={user} />}
    </div>
  )
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '10px 20px',
        background: 'transparent',
        border: 'none',
        borderBottom: active ? '3px solid #667eea' : '3px solid transparent',
        color: active ? '#667eea' : '#7f8c8d',
        cursor: 'pointer',
        fontWeight: active ? 'bold' : 'normal',
        fontSize: 15,
        marginBottom: -2
      }}
    >
      {children}
    </button>
  )
}

// === Вкладка: Информация ===
function InfoTab({ user }: { user: any }) {
  return (
    <div style={{ background: 'white', padding: 25, borderRadius: 8, border: '1px solid #e1e4e8' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginBottom: 25 }}>
        {user?.avatar_url ? (
          <img
            src={user.avatar_url}
            alt="Avatar"
            style={{ width: 100, height: 100, borderRadius: '50%', objectFit: 'cover', border: '3px solid #667eea' }}
          />
        ) : (
          <div style={{
            width: 100, height: 100, borderRadius: '50%',
            background: '#667eea', color: 'white',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 40, fontWeight: 'bold'
          }}>
            {user?.username?.[0]?.toUpperCase() || '?'}
          </div>
        )}
        <div>
          <h2 style={{ margin: 0, color: '#2c3e50' }}>{user?.username}</h2>
          <p style={{ margin: '5px 0', color: '#7f8c8d' }}>{user?.email}</p>
          <span style={{
            padding: '4px 12px',
            background: user?.role === 'admin' ? '#e74c3c' : '#27ae60',
            color: 'white',
            borderRadius: 12,
            fontSize: '0.85em'
          }}>
            {user?.role === 'admin' ? 'Администратор' : 'Пользователь'}
          </span>
        </div>
      </div>

      <div style={{ background: '#f8f9fa', padding: 15, borderRadius: 5 }}>
        <div style={{ marginBottom: 10 }}>
          <strong>2FA:</strong> {user?.is_2fa_enabled ? 'Включена' : 'Выключена'}
        </div>
        <div>
          <strong>ID пользователя:</strong> {user?.id}
        </div>
      </div>
    </div>
  )
}

// === Вкладка: Смена пароля ===
function PasswordTab() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setMessage('')
    setError('')

    if (newPassword !== confirmPassword) {
      setError('Новые пароли не совпадают')
      return
    }

    if (newPassword.length < 8) {
      setError('Пароль должен быть не менее 8 символов')
      return
    }

    setLoading(true)
    try {
      const res = await api.post('/users/me/password', {
        current_password: currentPassword,
        new_password: newPassword
      })
      setMessage(res.data.message || 'Пароль успешно изменён')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка смены пароля')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ background: 'white', padding: 25, borderRadius: 8, border: '1px solid #e1e4e8' }}>
      <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Смена пароля</h3>
      <p style={{ color: '#7f8c8d', fontSize: '0.9em', marginBottom: 20 }}>
        После смены пароля все активные сессии, кроме текущей, будут завершены.
      </p>

      <form onSubmit={handleSubmit}>
        <input
          type="password"
          placeholder="Текущий пароль"
          value={currentPassword}
          onChange={e => setCurrentPassword(e.target.value)}
          required
          style={inputStyle}
        />
        <input
          type="password"
          placeholder="Новый пароль (мин. 8 символов)"
          value={newPassword}
          onChange={e => setNewPassword(e.target.value)}
          required
          minLength={8}
          style={inputStyle}
        />
        <input
          type="password"
          placeholder="Подтвердите новый пароль"
          value={confirmPassword}
          onChange={e => setConfirmPassword(e.target.value)}
          required
          minLength={8}
          style={inputStyle}
        />

        {error && <div style={{ color: '#e74c3c', marginBottom: 15, fontSize: '0.9em' }}>{error}</div>}
        {message && <div style={{ color: '#27ae60', marginBottom: 15, fontSize: '0.9em' }}>{message}</div>}

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: '10px 20px',
            background: loading ? '#95a5a6' : '#e74c3c',
            color: 'white',
            border: 'none',
            borderRadius: 5,
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {loading ? 'Обработка...' : 'Сменить пароль'}
        </button>
      </form>
    </div>
  )
}

// === Вкладка: Активные сессии ===
function SessionsTab() {
  const [sessions, setSessions] = useState<SessionInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')

  const fetchSessions = async () => {
    try {
      const res = await api.get('/users/me/sessions')
      setSessions(res.data)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSessions()
  }, [])

  const revokeSession = async (sessionId: string) => {
    if (!confirm('Завершить эту сессию?')) return
    try {
      await api.delete(`/users/me/sessions/${sessionId}`)
      setMessage('Сессия завершена')
      fetchSessions()
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      console.error(err)
    }
  }

  const revokeAll = async () => {
    if (!confirm('Завершить ВСЕ другие сессии? Текущая сессия останется активной.')) return
    try {
      const res = await api.delete('/users/me/sessions')
      setMessage(res.data.message || 'Все сессии завершены')
      fetchSessions()
      setTimeout(() => setMessage(''), 3000)
    } catch (err) {
      console.error(err)
    }
  }

  const detectDevice = (ua: string) => {
    if (!ua) return 'Неизвестное устройство'
    if (ua.includes('Chrome')) return 'Chrome'
    if (ua.includes('Firefox')) return 'Firefox'
    if (ua.includes('Safari')) return 'Safari'
    if (ua.includes('Edge')) return 'Edge'
    return ua.substring(0, 40)
  }

  if (loading) return <div>Загрузка сессий...</div>

  return (
    <div style={{ background: 'white', padding: 25, borderRadius: 8, border: '1px solid #e1e4e8' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ margin: 0, color: '#2c3e50' }}>Активные сессии ({sessions.length})</h3>
        {sessions.length > 1 && (
          <button
            onClick={revokeAll}
            style={{
              padding: '8px 16px',
              background: '#e74c3c',
              color: 'white',
              border: 'none',
              borderRadius: 5,
              cursor: 'pointer',
              fontSize: '0.9em'
            }}
          >
            Завершить все другие
          </button>
        )}
      </div>

      {message && (
        <div style={{ padding: 10, marginBottom: 15, background: '#d1fae5', color: '#065f46', borderRadius: 5 }}>
          {message}
        </div>
      )}

      {sessions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 30, color: '#95a5a6' }}>
          Нет активных сессий
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sessions.map((s) => (
            <div
              key={s.id}
              style={{
                padding: 15,
                background: '#f8f9fa',
                borderRadius: 5,
                border: '1px solid #e1e4e8',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 'bold', marginBottom: 5 }}>
                  {detectDevice(s.user_agent)}
                </div>
                <div style={{ fontSize: '0.85em', color: '#666' }}>
                  IP: {s.ip_address || 'Неизвестно'}
                </div>
                <div style={{ fontSize: '0.8em', color: '#95a5a6', marginTop: 3 }}>
                  Создана: {s.created_at ? new Date(s.created_at).toLocaleString('ru-RU') : '-'}
                  {' • '}
                  Истекает: {s.expires_at ? new Date(s.expires_at).toLocaleString('ru-RU') : '-'}
                </div>
              </div>
              <button
                onClick={() => revokeSession(s.id)}
                style={{
                  padding: '6px 12px',
                  background: '#95a5a6',
                  color: 'white',
                  border: 'none',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontSize: '0.85em'
                }}
              >
                Завершить
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// === Вкладка: Аватар ===
function AvatarTab({ user }: { user: any }) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<string | null>(user?.avatar_url || null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setError('')
    setMessage('')

    // Валидация типа
    if (!file.type.startsWith('image/')) {
      setError('Можно загружать только изображения')
      return
    }

    // Валидация размера (5 МБ)
    if (file.size > 5 * 1024 * 1024) {
      setError('Файл слишком большой. Максимум: 5 МБ')
      return
    }

    setSelectedFile(file)

    // Превью
    const reader = new FileReader()
    reader.onload = (e) => setPreview(e.target?.result as string)
    reader.readAsDataURL(file)
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    setLoading(true)
    setError('')
    setMessage('')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const res = await api.post('/users/me/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setMessage(res.data.message || 'Аватар загружен')
      setSelectedFile(null)
      // Обновляем превью с серверным URL
      setPreview(res.data.avatar_url)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ background: 'white', padding: 25, borderRadius: 8, border: '1px solid #e1e4e8' }}>
      <h3 style={{ marginTop: 0, color: '#2c3e50' }}>Смена аватара</h3>
      <p style={{ color: '#7f8c8d', fontSize: '0.9em', marginBottom: 20 }}>
        Разрешённые форматы: JPG, PNG, WebP, GIF. Максимальный размер: 5 МБ.
      </p>

      <div style={{ display: 'flex', gap: 30, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* Превью */}
        <div style={{ textAlign: 'center' }}>
          {preview ? (
            <img
              src={preview}
              alt="Preview"
              style={{
                width: 180, height: 180, borderRadius: '50%',
                objectFit: 'cover', border: '4px solid #667eea'
              }}
            />
          ) : (
            <div style={{
              width: 180, height: 180, borderRadius: '50%',
              background: '#ecf0f1', display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              color: '#95a5a6', fontSize: 60
            }}>
              ?
            </div>
          )}
          <div style={{ marginTop: 10, fontSize: '0.85em', color: '#7f8c8d' }}>
            {selectedFile ? selectedFile.name : 'Текущий аватар'}
          </div>
        </div>

        {/* Управление */}
        <div style={{ flex: 1, minWidth: 250 }}>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            style={{
              padding: '10px 20px',
              background: '#667eea',
              color: 'white',
              border: 'none',
              borderRadius: 5,
              cursor: 'pointer',
              fontWeight: 'bold',
              marginBottom: 10,
              width: '100%'
            }}
          >
            Выбрать изображение
          </button>

          {selectedFile && (
            <button
              onClick={handleUpload}
              disabled={loading}
              style={{
                padding: '10px 20px',
                background: loading ? '#95a5a6' : '#27ae60',
                color: 'white',
                border: 'none',
                borderRadius: 5,
                cursor: loading ? 'not-allowed' : 'pointer',
                fontWeight: 'bold',
                width: '100%'
              }}
            >
              {loading ? 'Загрузка...' : 'Загрузить аватар'}
            </button>
          )}

          {error && <div style={{ color: '#e74c3c', marginTop: 15, fontSize: '0.9em' }}>{error}</div>}
          {message && <div style={{ color: '#27ae60', marginTop: 15, fontSize: '0.9em' }}>{message}</div>}
        </div>
      </div>
    </div>
  )
}

// === Общие стили ===
const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: 12,
  marginBottom: 15,
  boxSizing: 'border-box',
  border: '1px solid #ddd',
  borderRadius: 5
}