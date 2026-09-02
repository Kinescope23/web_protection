import { useAuth } from '../contexts/AuthContext'

export default function Profile() {
  const { user } = useAuth()
  return (
    <div style={{ padding: 20, maxWidth: 600, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1>👤 Профиль</h1>
      <p><strong>Email:</strong> {user?.email}</p>
      <p><strong>Username:</strong> {user?.username}</p>
      <p><strong>Роль:</strong> {user?.role}</p>
      <p><strong>2FA:</strong> {user?.is_2fa_enabled ? 'Включена' : 'Выключена'}</p>
    </div>
  )
}