import { useState, useEffect } from 'react'
import { useAuth, api } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

interface AgentInfo {
  agent_id: string
  name: string
  domain: string | null
  is_active: boolean
  last_seen: string | null
}

interface UserInfo {
  id: number
  username: string
  email: string
  role: string
  agents_count: number
  agents: AgentInfo[]
  last_hour: { total_requests: number; blocked: number; bots: number }
  ml_model: string
  ml_threshold: number
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [users, setUsers] = useState<UserInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const res = await api.get('/dashboard/users')
        setUsers(res.data)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchUsers()
    const interval = setInterval(fetchUsers, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>Загрузка...</div>

  const isAdmin = user?.role === 'admin'

  return (
    <div style={{ padding: 20, maxWidth: 1200, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: '#2c3e50', marginBottom: 25 }}>
        {isAdmin ? 'Панель управления' : 'Мой дашборд'}
      </h1>

      {isAdmin && (
        <p style={{ color: '#7f8c8d', marginBottom: 20 }}>
          Нажмите на пользователя, чтобы просмотреть его метрики и настроить ML.
        </p>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
        {users.map((u) => (
          <div
            key={u.id}
            onClick={() => isAdmin && navigate(`/user/${u.id}`)}
            style={{
              background: 'white',
              padding: 20,
              borderRadius: 8,
              border: '1px solid #e1e4e8',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
              cursor: isAdmin ? 'pointer' : 'default',
              transition: 'box-shadow 0.2s',
            }}
            onMouseEnter={(e) => isAdmin && (e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)')}
            onMouseLeave={(e) => isAdmin && (e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)')}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
                <div style={{
                  width: 50, height: 50, borderRadius: '50%',
                  background: u.role === 'admin' ? '#e74c3c' : '#3498db',
                  color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 22, fontWeight: 'bold'
                }}>
                  {u.username[0].toUpperCase()}
                </div>
                <div>
                  <div style={{ fontWeight: 'bold', fontSize: 18, color: '#2c3e50' }}>
                    {u.username}
                    {u.id === user?.id && <span style={{ color: '#95a5a6', fontSize: 14, marginLeft: 8 }}>(вы)</span>}
                  </div>
                  <div style={{ fontSize: 13, color: '#7f8c8d' }}>{u.email}</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <span style={{
                  padding: '4px 12px', borderRadius: 12, fontSize: 12,
                  background: u.role === 'admin' ? '#fee2e2' : '#d1fae5',
                  color: u.role === 'admin' ? '#991b1b' : '#065f46'
                }}>
                  {u.role}
                </span>
                {isAdmin && <span style={{ color: '#95a5a6', fontSize: 20 }}>&rarr;</span>}
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10 }}>
              <MiniStat label="Агентов" value={u.agents_count} color="#3498db" />
              <MiniStat label="Запросов/ч" value={u.last_hour.total_requests} color="#2c3e50" />
              <MiniStat label="Заблокировано" value={u.last_hour.blocked} color="#e74c3c" />
              <MiniStat label="Ботов" value={u.last_hour.bots} color="#f39c12" />
              <MiniStat label="ML-модель" value={u.ml_model.replace('_', ' ')} color="#9b59b6" />
              <MiniStat label="Порог" value={u.ml_threshold.toFixed(2)} color="#16a085" />
            </div>

            {u.agents.length > 0 && (
              <div style={{ marginTop: 12, fontSize: 13, color: '#7f8c8d' }}>
                Агенты: {u.agents.map(a => (
                  <span key={a.agent_id} style={{
                    display: 'inline-block', padding: '2px 8px', margin: '2px 4px',
                    background: a.is_active ? '#d1fae5' : '#fee2e2',
                    borderRadius: 10, fontSize: 12
                  }}>
                    {a.name} ({a.agent_id})
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function MiniStat({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div style={{ padding: 8, background: '#f8f9fa', borderRadius: 5, textAlign: 'center' }}>
      <div style={{ fontSize: 11, color: '#95a5a6', marginBottom: 3 }}>{label}</div>
      <div style={{ fontWeight: 'bold', color, fontSize: 14 }}>{value}</div>
    </div>
  )
}