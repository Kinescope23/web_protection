import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

  const linkStyle = (path: string): React.CSSProperties => ({
    padding: '8px 16px',
    textDecoration: 'none',
    color: isActive(path) ? '#fff' : '#ecf0f1',
    background: isActive(path) ? '#34495e' : 'transparent',
    borderRadius: 4,
    transition: 'background 0.2s',
  })

  return (
    <nav style={{
      background: '#2c3e50',
      padding: '0 20px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      minHeight: 60,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <Link to="/dashboard" style={{ color: '#fff', textDecoration: 'none', fontSize: 18, fontWeight: 'bold' }}>
          🛡 Net Protector
        </Link>
        <div style={{ display: 'flex', gap: 10 }}>
          <Link to="/dashboard" style={linkStyle('/dashboard')}>Дашборд</Link>
          <Link to="/upload" style={linkStyle('/upload')}>Загрузка</Link>
          <Link to="/profile" style={linkStyle('/profile')}>Профиль</Link>
          <Link to="/tokens" style={linkStyle('/tokens')}>Токены</Link>
          {user?.role === 'admin' && (
            <Link to="/admin" style={linkStyle('/admin')}>Админ</Link>
          )}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
        <span style={{ color: '#ecf0f1', fontSize: 14 }}>
           {user?.username} ({user?.role})
        </span>
        <button
          onClick={logout}
          style={{
            padding: '6px 12px',
            background: '#e74c3c',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer',
            fontSize: 13,
          }}
        >
          Выйти
        </button>
      </div>
    </nav>
  )
}