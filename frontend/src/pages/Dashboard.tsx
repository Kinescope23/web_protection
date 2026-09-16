import { useState, useEffect } from 'react'
import { useAuth, api } from '../contexts/AuthContext'

interface DashboardStats {
  last_hour: {
    total_requests: number
    blocked: number
    bot_detected: number
    avg_bot_probability: number
  }
  last_24h: {
    total_requests: number
    blocked: number
    bot_detected: number
  }
  risk_distribution: { low: number; medium: number; high: number }
  active_blocked_ips: number
  ml_model: string
  ml_threshold: number
  models_loaded: string[]
}

interface RecentLog {
  id: number
  agent_id: string
  src_ip: string
  method: string
  path: string
  verdict: string
  bot_probability: number | null
  risk_level: string | null
  is_bot: boolean | null
  ml_model_used: string | null
  timestamp: string
}

interface Threat {
  type: string
  value: string
  severity: string
  source: string
  detected_at: string
  bot_probability?: number
}

interface TrafficPoint {
  hour: string
  total: number
  blocked: number
  bots: number
}

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [logs, setLogs] = useState<RecentLog[]>([])
  const [threats, setThreats] = useState<Threat[]>([])
  const [traffic, setTraffic] = useState<TrafficPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Загрузка всех данных
  const fetchAll = async () => {
    try {
      const [statsRes, logsRes, threatsRes, trafficRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/dashboard/recent-logs?limit=15'),
        api.get('/dashboard/threats'),
        api.get('/dashboard/traffic-chart?hours=6'),
      ])
      setStats(statsRes.data)
      setLogs(logsRes.data)
      setThreats(threatsRes.data.threats || [])
      setTraffic(trafficRes.data.data || [])
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки данных')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
    // Автообновление каждые 5 секунд
    const interval = setInterval(fetchAll, 5000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !stats) {
    return <div style={{ padding: 40, textAlign: 'center' }}>Загрузка дашборда...</div>
  }

  if (error && !stats) {
    return <div style={{ padding: 40, textAlign: 'center', color: '#e74c3c' }}>{error}</div>
  }

  // Цвета для уровней риска
  const riskColors = {
    low: '#27ae60',
    medium: '#f39c12',
    high: '#e74c3c',
  }

  // Максимальное значение для нормализации графика
  const maxTraffic = Math.max(...traffic.map(p => p.total), 1)

  return (
    <div style={{ padding: 20, maxWidth: 1400, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      {/* Заголовок */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 25 }}>
        <div>
          <h1 style={{ margin: 0, color: '#2c3e50' }}>Дашборд Net Protector</h1>
          <p style={{ margin: '5px 0 0', color: '#7f8c8d' }}>
            Добро пожаловать, <strong>{user?.username}</strong>
            <span style={{
              marginLeft: 10,
              padding: '2px 10px',
              background: user?.role === 'admin' ? '#e74c3c' : '#27ae60',
              color: 'white',
              borderRadius: 12,
              fontSize: '0.75em'
            }}>
              {user?.role === 'admin' ? 'Администратор' : 'Пользователь'}
            </span>
          </p>
        </div>
        <div style={{ fontSize: '0.85em', color: '#95a5a6' }}>
          Обновлено: {new Date().toLocaleTimeString('ru-RU')}
        </div>
      </div>

      {/* Сообщение об ошибке */}
      {error && (
        <div style={{
          padding: 10,
          marginBottom: 15,
          background: '#fee2e2',
          border: '1px solid #fca5a5',
          borderRadius: 5,
          color: '#991b1b',
          fontSize: '0.9em'
        }}>
          {error}
        </div>
      )}

      {/* Карточки статистики */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 15,
        marginBottom: 25
      }}>
        <StatCard
          title="Запросов за час"
          value={stats?.last_hour.total_requests || 0}
          color="#3498db"
          icon=""
        />
        <StatCard
          title="Заблокировано"
          value={stats?.last_hour.blocked || 0}
          color="#e74c3c"
          icon=""
        />
        <StatCard
          title="Обнаружено ботов"
          value={stats?.last_hour.bot_detected || 0}
          color="#f39c12"
          icon=""
        />
        <StatCard
          title="Активных блокировок IP"
          value={stats?.active_blocked_ips || 0}
          color="#9b59b6"
          icon=""
        />
        <StatCard
          title="Средняя вероятность бота"
          value={`${((stats?.last_hour.avg_bot_probability || 0) * 100).toFixed(1)}%`}
          color="#16a085"
          icon=""
        />
      </div>

      {/* График трафика */}
      <div style={{
        background: 'white',
        padding: 20,
        borderRadius: 8,
        border: '1px solid #e1e4e8',
        marginBottom: 25,
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        <h3 style={{ margin: '0 0 15px', color: '#2c3e50' }}>Трафик за последние 6 часов</h3>
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 180, padding: '10px 0' }}>
          {traffic.map((point, idx) => (
            <div key={idx} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-end',
                width: '100%',
                height: '100%',
                gap: 2
              }}>
                {/* Боты (красный) */}
                <div style={{
                  height: `${(point.bots / maxTraffic) * 100}%`,
                  background: '#e74c3c',
                  minHeight: point.bots > 0 ? 2 : 0,
                  borderRadius: '2px 2px 0 0',
                  transition: 'height 0.3s'
                }} title={`Боты: ${point.bots}`} />
                {/* Заблокированные (оранжевый) */}
                <div style={{
                  height: `${(point.blocked / maxTraffic) * 100}%`,
                  background: '#f39c12',
                  minHeight: point.blocked > 0 ? 2 : 0,
                  transition: 'height 0.3s'
                }} title={`Заблокировано: ${point.blocked}`} />
                {/* Всего (синий) */}
                <div style={{
                  height: `${(point.total / maxTraffic) * 100}%`,
                  background: '#3498db',
                  minHeight: 4,
                  borderRadius: '0 0 2px 2px',
                  transition: 'height 0.3s'
                }} title={`Всего: ${point.total}`} />
              </div>
              <div style={{ fontSize: '0.7em', color: '#7f8c8d', marginTop: 5 }}>{point.hour}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 20, marginTop: 10, fontSize: '0.85em' }}>
          <div><span style={{ display: 'inline-block', width: 12, height: 12, background: '#3498db', marginRight: 5, borderRadius: 2 }}></span>Всего</div>
          <div><span style={{ display: 'inline-block', width: 12, height: 12, background: '#f39c12', marginRight: 5, borderRadius: 2 }}></span>Заблокировано</div>
          <div><span style={{ display: 'inline-block', width: 12, height: 12, background: '#e74c3c', marginRight: 5, borderRadius: 2 }}></span>Боты</div>
        </div>
      </div>

      {/* Два блока в ряд: Угрозы + Распределение риска */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 25 }}>
        {/* Активные угрозы */}
        <div style={{
          background: 'white',
          padding: 20,
          borderRadius: 8,
          border: '1px solid #e1e4e8',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
        }}>
          <h3 style={{ margin: '0 0 15px', color: '#2c3e50' }}>Активные угрозы ({threats.length})</h3>
          {threats.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 30, color: '#95a5a6' }}>
              <div style={{ fontSize: '2em', marginBottom: 10 }}></div>
              Угроз не обнаружено
            </div>
          ) : (
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {threats.slice(0, 10).map((threat, idx) => (
                <div key={idx} style={{
                  padding: 10,
                  marginBottom: 8,
                  background: threat.severity === 'high' ? '#fee2e2' : threat.severity === 'medium' ? '#fef3c7' : '#d1fae5',
                  borderLeft: `4px solid ${riskColors[threat.severity as keyof typeof riskColors] || '#95a5a6'}`,
                  borderRadius: 4,
                  fontSize: '0.9em'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontFamily: 'monospace' }}>{threat.value}</strong>
                    <span style={{
                      padding: '2px 8px',
                      background: riskColors[threat.severity as keyof typeof riskColors] || '#95a5a6',
                      color: 'white',
                      borderRadius: 10,
                      fontSize: '0.8em'
                    }}>
                      {threat.severity}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8em', color: '#666', marginTop: 4 }}>
                    {threat.type === 'blocked_ip' ? 'Заблокирован глобально' : `Бот (p=${threat.bot_probability?.toFixed(2)})`}
                    {' • '}
                    {threat.detected_at ? new Date(threat.detected_at).toLocaleTimeString('ru-RU') : ''}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Распределение по уровню риска */}
        <div style={{
          background: 'white',
          padding: 20,
          borderRadius: 8,
          border: '1px solid #e1e4e8',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
        }}>
          <h3 style={{ margin: '0 0 15px', color: '#2c3e50' }}>Распределение по уровню риска</h3>
          <RiskBar
            label="Низкий"
            value={stats?.risk_distribution.low || 0}
            max={Math.max(
              stats?.risk_distribution.low || 0,
              stats?.risk_distribution.medium || 0,
              stats?.risk_distribution.high || 0,
              1
            )}
            color="#27ae60"
          />
          <RiskBar
            label="Средний"
            value={stats?.risk_distribution.medium || 0}
            max={Math.max(
              stats?.risk_distribution.low || 0,
              stats?.risk_distribution.medium || 0,
              stats?.risk_distribution.high || 0,
              1
            )}
            color="#f39c12"
          />
          <RiskBar
            label="Высокий"
            value={stats?.risk_distribution.high || 0}
            max={Math.max(
              stats?.risk_distribution.low || 0,
              stats?.risk_distribution.medium || 0,
              stats?.risk_distribution.high || 0,
              1
            )}
            color="#e74c3c"
          />

          <div style={{
            marginTop: 20,
            padding: 15,
            background: '#f8f9fa',
            borderRadius: 5,
            fontSize: '0.85em'
          }}>
            <div><strong>ML-модель:</strong> {stats?.ml_model}</div>
            <div><strong>Порог:</strong> {(stats?.ml_threshold || 0).toFixed(2)}</div>
            <div><strong>Загружено моделей:</strong> {stats?.models_loaded?.join(', ') || 'нет'}</div>
          </div>
        </div>
      </div>

      {/* Таблица последних событий */}
      <div style={{
        background: 'white',
        padding: 20,
        borderRadius: 8,
        border: '1px solid #e1e4e8',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        <h3 style={{ margin: '0 0 15px', color: '#2c3e50' }}>Последние события</h3>
        {logs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 30, color: '#95a5a6' }}>
            Событий пока нет
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9em' }}>
              <thead>
                <tr style={{ background: '#2c3e50', color: 'white' }}>
                  <th style={{ padding: 10, textAlign: 'left' }}>Время</th>
                  <th style={{ padding: 10, textAlign: 'left' }}>Источник</th>
                  <th style={{ padding: 10, textAlign: 'left' }}>Путь</th>
                  <th style={{ padding: 10, textAlign: 'center' }}>Вердикт</th>
                  <th style={{ padding: 10, textAlign: 'center' }}>P(бот)</th>
                  <th style={{ padding: 10, textAlign: 'center' }}>Риск</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: 10, fontSize: '0.85em', color: '#666' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString('ru-RU') : '-'}
                    </td>
                    <td style={{ padding: 10, fontFamily: 'monospace', fontSize: '0.85em' }}>
                      {log.src_ip}
                    </td>
                    <td style={{ padding: 10, fontSize: '0.85em' }}>
                      {log.path}
                    </td>
                    <td style={{ padding: 10, textAlign: 'center' }}>
                      <span style={{
                        padding: '3px 10px',
                        borderRadius: 10,
                        fontSize: '0.8em',
                        fontWeight: 'bold',
                        background: log.verdict === 'blocked' ? '#fee2e2' : '#d1fae5',
                        color: log.verdict === 'blocked' ? '#991b1b' : '#065f46'
                      }}>
                        {log.verdict === 'blocked' ? 'BLOCKED' : 'ALLOWED'}
                      </span>
                    </td>
                    <td style={{ padding: 10, textAlign: 'center', fontFamily: 'monospace' }}>
                      {log.bot_probability !== null ? (log.bot_probability * 100).toFixed(1) + '%' : '-'}
                    </td>
                    <td style={{ padding: 10, textAlign: 'center' }}>
                      {log.risk_level ? (
                        <span style={{
                          padding: '3px 10px',
                          borderRadius: 10,
                          fontSize: '0.8em',
                          fontWeight: 'bold',
                          background: riskColors[log.risk_level as keyof typeof riskColors] || '#95a5a6',
                          color: 'white'
                        }}>
                          {log.risk_level.toUpperCase()}
                        </span>
                      ) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// === Вспомогательные компоненты ===

function StatCard({ title, value, color, icon }: { title: string; value: string | number; color: string; icon: string }) {
  return (
    <div style={{
      background: 'white',
      padding: 20,
      borderRadius: 8,
      border: '1px solid #e1e4e8',
      borderLeft: `4px solid ${color}`,
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ fontSize: '0.85em', color: '#7f8c8d', fontWeight: 'bold' }}>{title}</div>
        <div style={{ fontSize: '1.5em' }}>{icon}</div>
      </div>
      <div style={{ fontSize: '2em', fontWeight: 'bold', color: color }}>
        {value}
      </div>
    </div>
  )
}

function RiskBar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const percentage = max > 0 ? (value / max) * 100 : 0
  return (
    <div style={{ marginBottom: 15 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, fontSize: '0.9em' }}>
        <span style={{ fontWeight: 'bold' }}>{label}</span>
        <span style={{ color: '#666' }}>{value}</span>
      </div>
      <div style={{ background: '#ecf0f1', borderRadius: 4, overflow: 'hidden', height: 20 }}>
        <div style={{
          width: `${percentage}%`,
          height: '100%',
          background: color,
          transition: 'width 0.5s',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          paddingRight: 8,
          color: 'white',
          fontSize: '0.75em',
          fontWeight: 'bold'
        }}>
          {percentage > 15 && `${percentage.toFixed(0)}%`}
        </div>
      </div>
    </div>
  )
}