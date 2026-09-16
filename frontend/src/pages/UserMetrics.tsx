import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../contexts/AuthContext'

export default function UserMetrics() {
  const { userId } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [models, setModels] = useState<any[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [threshold, setThreshold] = useState(0.65)
  const [message, setMessage] = useState('')

  const fetchData = async () => {
    try {
      const [metricsRes, modelsRes] = await Promise.all([
        api.get(`/dashboard/user/${userId}?hours=6`),
        api.get('/admin/ml-models')
      ])
      setData(metricsRes.data)
      setModels(modelsRes.data.models_info || [])
      setSelectedModel(metricsRes.data.ml_settings?.model || 'isolation_forest')
      setThreshold(metricsRes.data.ml_settings?.threshold || 0.65)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [userId])

  const saveML = async () => {
    try {
      await api.post(`/admin/user/${userId}/ml-settings`, null, {
        params: { ml_model: selectedModel, threshold }
      })
      setMessage('Настройки ML сохранены')
      setTimeout(() => setMessage(''), 3000)
    } catch (e: any) {
      setMessage(e.response?.data?.detail || 'Ошибка')
    }
  }

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>Загрузка...</div>
  if (!data) return <div style={{ padding: 40, textAlign: 'center', color: '#e74c3c' }}>Пользователь не найден</div>

  const riskColors: Record<string, string> = { low: '#27ae60', medium: '#f39c12', high: '#e74c3c' }
  
  // ИСПРАВЛЕНО: Явная типизация для Math.max
  const maxTraffic = Math.max(...data.traffic_chart.map((p: any) => p.total as number), 1)

  return (
    <div style={{ padding: 20, maxWidth: 1200, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <button onClick={() => navigate('/dashboard')} style={{
        padding: '8px 16px', background: '#ecf0f1', border: 'none', borderRadius: 5,
        cursor: 'pointer', marginBottom: 20, fontSize: 14
      }}>
        &larr; Назад к списку
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 15, marginBottom: 25 }}>
        <div style={{
          width: 60, height: 60, borderRadius: '50%', background: '#3498db',
          color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 28, fontWeight: 'bold'
        }}>
          {data.user.username[0].toUpperCase()}
        </div>
        <div>
          <h1 style={{ margin: 0, color: '#2c3e50' }}>{data.user.username}</h1>
          <div style={{ color: '#7f8c8d' }}>{data.user.email} | {data.user.role}</div>
        </div>
      </div>

      {message && (
        <div style={{ padding: 10, marginBottom: 15, background: '#d1fae5', color: '#065f46', borderRadius: 5 }}>
          {message}
        </div>
      )}

      {/* Карточки статистики */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 15, marginBottom: 25 }}>
        <StatCard title="Запросов/ч" value={data.stats.total} color="#3498db" />
        <StatCard title="Заблокировано" value={data.stats.blocked} color="#e74c3c" />
        <StatCard title="Ботов" value={data.stats.bots} color="#f39c12" />
        <StatCard title="P(бот) среднее" value={`${(data.stats.avg_bot_prob * 100).toFixed(1)}%`} color="#9b59b6" />
      </div>

      {/* Агенты */}
      <div style={{ background: 'white', padding: 20, borderRadius: 8, border: '1px solid #e1e4e8', marginBottom: 25 }}>
        <h3 style={{ marginTop: 0 }}>Агенты ({data.agents.length})</h3>
        {data.agents.length === 0 ? (
          <p style={{ color: '#95a5a6' }}>Нет подключённых агентов</p>
        ) : (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {data.agents.map((a: any) => (
              <div key={a.agent_id} style={{
                padding: 12, background: '#f8f9fa', borderRadius: 5, border: '1px solid #e1e4e8', minWidth: 200
              }}>
                <div style={{ fontWeight: 'bold' }}>{a.name}</div>
                <div style={{ fontSize: 12, color: '#666' }}>ID: {a.agent_id}</div>
                {a.domain && <div style={{ fontSize: 12, color: '#666' }}>Домен: {a.domain}</div>}
                <div style={{ fontSize: 12, marginTop: 5 }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: 10,
                    background: a.is_active ? '#d1fae5' : '#fee2e2',
                    color: a.is_active ? '#065f46' : '#991b1b'
                  }}>
                    {a.is_active ? 'Онлайн' : 'Офлайн'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Настройки ML для этого пользователя */}
      <div style={{ background: 'white', padding: 20, borderRadius: 8, border: '1px solid #e1e4e8', marginBottom: 25 }}>
        <h3 style={{ marginTop: 0 }}>Настройки ML для {data.user.username}</h3>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label style={{ display: 'block', marginBottom: 5, fontWeight: 'bold', fontSize: 14 }}>Модель:</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              style={{ width: '100%', padding: 10, borderRadius: 5, border: '1px solid #ddd', fontSize: 14 }}
            >
              {models.filter((m: any) => m.status === 'loaded').map((m: any) => (
                <option key={m.name} value={m.name}>{m.name.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1, minWidth: 250 }}>
            <label style={{ display: 'block', marginBottom: 5, fontWeight: 'bold', fontSize: 14 }}>
              Порог: <span style={{ color: '#667eea' }}>{threshold.toFixed(2)}</span>
            </label>
            <input
              type="range" min="0" max="1" step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>
          <button onClick={saveML} style={{
            padding: '10px 20px', background: '#27ae60', color: 'white',
            border: 'none', borderRadius: 5, cursor: 'pointer', fontWeight: 'bold'
          }}>
            Сохранить
          </button>
        </div>
      </div>

      {/* График */}
      <div style={{ background: 'white', padding: 20, borderRadius: 8, border: '1px solid #e1e4e8', marginBottom: 25 }}>
        <h3 style={{ marginTop: 0 }}>Трафик за 6 часов</h3>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 150 }}>
          {data.traffic_chart.map((p: any, i: number) => (
            <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
              <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', width: '100%', height: '100%', gap: 2 }}>
                <div style={{ height: `${((p.bots as number) / maxTraffic) * 100}%`, background: '#e74c3c', minHeight: (p.bots as number) > 0 ? 2 : 0 }} />
                <div style={{ height: `${((p.blocked as number) / maxTraffic) * 100}%`, background: '#f39c12', minHeight: (p.blocked as number) > 0 ? 2 : 0 }} />
                <div style={{ height: `${((p.total as number) / maxTraffic) * 100}%`, background: '#3498db', minHeight: 4 }} />
              </div>
              <div style={{ fontSize: 11, color: '#7f8c8d', marginTop: 5 }}>{p.hour}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Угрозы + Риск */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 25 }}>
        <div style={{ background: 'white', padding: 20, borderRadius: 8, border: '1px solid #e1e4e8' }}>
          <h3 style={{ marginTop: 0 }}>Угрозы ({data.threats.length})</h3>
          {data.threats.length === 0 ? (
            <p style={{ color: '#95a5a6', textAlign: 'center' }}>Угроз нет</p>
          ) : data.threats.map((t: any, i: number) => (
            <div key={i} style={{
              padding: 8, marginBottom: 5, borderLeft: `4px solid ${riskColors[t.severity] || '#95a5a6'}`,
              background: '#f8f9fa', borderRadius: 4, fontSize: 13
            }}>
              <strong>{t.value}</strong> — p={t.bot_probability?.toFixed(2)} ({t.severity})
            </div>
          ))}
        </div>
        <div style={{ background: 'white', padding: 20, borderRadius: 8, border: '1px solid #e1e4e8' }}>
          <h3 style={{ marginTop: 0 }}>Распределение риска</h3>
          {['low', 'medium', 'high'].map(level => {
            const val = (data.risk_distribution[level] as number) || 0
            // ИСПРАВЛЕНО: Явная типизация для Math.max
            const max = Math.max(...Object.values(data.risk_distribution).map(v => v as number), 1)
            return (
              <div key={level} style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 3 }}>
                  <span>{level}</span><span>{val}</span>
                </div>
                <div style={{ background: '#ecf0f1', borderRadius: 4, height: 16 }}>
                  <div style={{ width: `${(val / max) * 100}%`, height: '100%', background: riskColors[level], borderRadius: 4 }} />
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Таблица логов */}
      <div style={{ background: 'white', padding: 20, borderRadius: 8, border: '1px solid #e1e4e8' }}>
        <h3 style={{ marginTop: 0 }}>Последние события</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#2c3e50', color: 'white' }}>
              <th style={{ padding: 8, textAlign: 'left' }}>Время</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Агент</th>
              <th style={{ padding: 8, textAlign: 'center' }}>Вердикт</th>
              <th style={{ padding: 8, textAlign: 'center' }}>P(бот)</th>
              <th style={{ padding: 8, textAlign: 'center' }}>Риск</th>
            </tr>
          </thead>
          <tbody>
            {data.recent_logs.map((l: any) => (
              <tr key={l.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{l.timestamp ? new Date(l.timestamp).toLocaleTimeString('ru-RU') : '-'}</td>
                <td style={{ padding: 8, fontFamily: 'monospace' }}>{l.agent_id}</td>
                <td style={{ padding: 8, textAlign: 'center' }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: 10, fontSize: 11,
                    background: l.verdict === 'blocked' ? '#fee2e2' : '#d1fae5',
                    color: l.verdict === 'blocked' ? '#991b1b' : '#065f46'
                  }}>{l.verdict}</span>
                </td>
                <td style={{ padding: 8, textAlign: 'center' }}>
                  {l.bot_probability !== null ? (l.bot_probability * 100).toFixed(1) + '%' : '-'}
                </td>
                <td style={{ padding: 8, textAlign: 'center' }}>
                  <span style={{
                    padding: '2px 8px', borderRadius: 10, fontSize: 11, color: 'white',
                    background: riskColors[l.risk_level] || '#95a5a6'
                  }}>{l.risk_level || '-'}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatCard({ title, value, color }: { title: string; value: string | number; color: string }) {
  return (
    <div style={{ background: 'white', padding: 15, borderRadius: 8, border: '1px solid #e1e4e8', borderLeft: `4px solid ${color}` }}>
      <div style={{ fontSize: 12, color: '#7f8c8d' }}>{title}</div>
      <div style={{ fontSize: 24, fontWeight: 'bold', color }}>{value}</div>
    </div>
  )
}