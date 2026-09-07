import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Profile from './pages/Profile'
import Tokens from './pages/Tokens'
import Admin from './pages/Admin'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  
  // Ждем завершения проверки токена
  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center', fontFamily: 'Arial' }}>Загрузка системы...</div>
  }
  
  return user ? <>{children}</> : <Navigate to="/login" />
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>Загрузка...</div>
  if (!user) return <Navigate to="/login" />
  if (user.role !== 'admin') return <Navigate to="/dashboard" />
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      {/* Публичные роуты (без Layout) */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      {/* Защищённые роуты (с Layout) */}
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
        <Route path="profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="tokens" element={<ProtectedRoute><Tokens /></ProtectedRoute>} />
        <Route path="admin" element={<AdminRoute><Admin /></AdminRoute>} />
      </Route>
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}