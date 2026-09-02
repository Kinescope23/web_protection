import { useAuth } from '../contexts/AuthContext'

export default function Dashboard() {
  const { user } = useAuth()

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: '#2c3e50', marginBottom: 10 }}>🛡 Добро пожаловать в Net Protector</h1>
      <p style={{ fontSize: '1.2em', marginBottom: 30 }}>
        Вы вошли как <strong>{user?.username}</strong>
        <span style={{ 
          marginLeft: 10, 
          padding: '4px 12px', 
          background: user?.role === 'admin' ? '#e74c3c' : '#27ae60', 
          color: 'white', 
          borderRadius: 12, 
          fontSize: '0.8em' 
        }}>
          {user?.role === 'admin' ? 'Администратор' : 'Пользователь'}
        </span>
      </p>

      <div style={{ background: '#f8f9fa', padding: 20, borderRadius: 8, border: '1px solid #e9ecef' }}>
        <h3 style={{ marginTop: 0, color: '#495057' }}> Статус системы</h3>
        <p style={{ color: '#6c757d' }}>
          Система активна и работает в штатном режиме.
        </p>
        <p style={{ color: '#6c757d' }}>
          Используйте навигацию сверху для перехода к нужным разделам.
        </p>
      </div>
    </div>
  )
}