import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div style={{ fontFamily: 'Arial, sans-serif' }}>
      <nav style={{
        background: '#2c3e50',
        padding: '12px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
          <Link to="/dashboard" style={{ color: 'white', textDecoration: 'none', fontWeight: 'bold', fontSize: 18 }}>
            Net Protector
          </Link>
          <Link to="/dashboard" style={{ color: '#bdc3c7', textDecoration: 'none' }}>Дашборд</Link>
          {user?.role === 'admin' && (
            <>
              <Link to="/upload" style={{ color: '#bdc3c7', textDecoration: 'none' }}>Загрузка</Link>
              <Link to="/admin" style={{ color: '#bdc3c7', textDecoration: 'none' }}>Админ</Link>
            </>
          )}
          <Link to="/profile" style={{ color: '#bdc3c7', textDecoration: 'none' }}>Профиль</Link>
          <Link to="/tokens" style={{ color: '#bdc3c7', textDecoration: 'none' }}>Токены</Link>
        </div>
        <div style={{ display: 'flex', gap: 15, alignItems: 'center' }}>
          <span style={{ color: '#bdc3c7', fontSize: 14 }}>
            {user?.username}
            <span style={{
              marginLeft: 8,
              padding: '2px 8px',
              background: user?.role === 'admin' ? '#e74c3c' : '#27ae60',
              borderRadius: 10,
              fontSize: 11,
              color: 'white'
            }}>
              {user?.role}
            </span>
          </span>
          <button
            onClick={handleLogout}
            style={{
              padding: '6px 14px',
              background: '#e74c3c',
              color: 'white',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: 13
            }}
          >
            Выйти
          </button>
        </div>
      </nav>
      <main>
        <Outlet />
      </main>
    </div>
  )
}