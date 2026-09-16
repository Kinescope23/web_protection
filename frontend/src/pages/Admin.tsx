import { useState, useEffect } from 'react'
import { api } from '../contexts/AuthContext'

interface InvitationKey {
  id: number
  key: string
  is_used: boolean
  created_at: string
  created_by: number
}

interface MLModelInfo {
  name: string
  status: string
  is_active: boolean
}

export default function Admin() {
  const [inviteKey, setInviteKey] = useState('')
  const [keys, setKeys] = useState<InvitationKey[]>([])
  const [mlThreshold, setMlThreshold] = useState(0.65)
  const [stats, setStats] = useState<any>(null)
  const [message, setMessage] = useState('')
  const [availableModels, setAvailableModels] = useState<MLModelInfo[]>([])
  const [activeModel, setActiveModel] = useState('isolation_forest')

  useEffect(() => {
    fetchKeys()
    fetchStats()
    fetchModels()
  }, [])

  const fetchKeys = async () => {
    try {
      const res = await api.get('/admin/invitation-keys')
      setKeys(res.data)
    } catch (e) {
      console.error('Ошибка загрузки ключей', e)
    }
  }

  const fetchStats = async () => {
    try {
      const res = await api.get('/admin/stats')
      setStats(res.data)
      setMlThreshold(res.data.current_ml_threshold)
    } catch (e) {
      console.error('Ошибка загрузки статистики', e)
    }
  }

  const fetchModels = async () => {
    try {
      const res = await api.get('/admin/ml-models')
      setAvailableModels(res.data.models_info || [])
      setActiveModel(res.data.active_model || 'isolation_forest')
    } catch (e) {
      console.error('Ошибка загрузки моделей', e)
    }
  }

  const generateKey = async () => {
    try {
      const res = await api.post('/admin/generate-invite')
      setInviteKey(res.data.invitation_key)
      setMessage('Ключ успешно создан!')
      fetchKeys()
      setTimeout(() => setMessage(''), 3000)
    } catch (e) {
      setMessage('Ошибка создания ключа')
      console.error(e)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setMessage('Ключ скопирован в буфер обмена!')
    setTimeout(() => setMessage(''), 2000)
  }

  const saveMLSettings = async () => {
    try {
      await api.post('/admin/ml-settings', null, { 
        params: { threshold: mlThreshold } 
      })
      setMessage('Настройки ML сохранены')
      setTimeout(() => setMessage(''), 3000)
    } catch (e: any) {
      setMessage(e.response?.data?.detail || 'Ошибка сохранения настроек')
      console.error(e)
    }
  }

  const changeActiveModel = async (modelName: string) => {
    try {
      const res = await api.post('/admin/ml-model/active', null, {
        params: { model_name: modelName }
      })
      setMessage(res.data.message)
      setActiveModel(modelName)
      fetchModels()
      setTimeout(() => setMessage(''), 3000)
    } catch (e: any) {
      setMessage(e.response?.data?.detail || 'Ошибка смены модели')
      setTimeout(() => setMessage(''), 3000)
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 1200, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: '#2c3e50', marginBottom: 30 }}>Админ-панель</h1>

      {message && (
        <div style={{
          padding: 15,
          marginBottom: 20,
          background: message.includes('Ошибка') ? '#fee2e2' : '#d1fae5',
          border: `1px solid ${message.includes('Ошибка') ? '#fca5a5' : '#6ee7b7'}`,
          borderRadius: 8,
          color: message.includes('Ошибка') ? '#991b1b' : '#065f46',
          fontWeight: 'bold'
        }}>
          {message}
        </div>
      )}

      {stats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 15,
          marginBottom: 30
        }}>
          <div style={{ background: '#f0f9ff', padding: 20, borderRadius: 8, border: '1px solid #bae6fd' }}>
            <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#0369a1' }}>{stats.total_users}</div>
            <div style={{ color: '#0c4a6e' }}>Пользователей</div>
          </div>
          <div style={{ background: '#fef3c7', padding: 20, borderRadius: 8, border: '1px solid #fcd34d' }}>
            <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#92400e' }}>{stats.active_invitation_keys}</div>
            <div style={{ color: '#78350f' }}>Активных ключей</div>
          </div>
          <div style={{ background: '#f0fdf4', padding: 20, borderRadius: 8, border: '1px solid #86efac' }}>
            <div style={{ fontSize: '2em', fontWeight: 'bold', color: '#166534' }}>{stats.currently_blocked_ips}</div>
            <div style={{ color: '#14532d' }}>Заблокировано IP</div>
          </div>
        </div>
      )}

      {/* Секция 1: Управление ключами */}
      <div style={{ background: '#fff', padding: 25, borderRadius: 8, border: '1px solid #ddd', marginBottom: 30 }}>
        <h2 style={{ marginTop: 0, color: '#2c3e50' }}>Управление ключами приглашения</h2>
        <p style={{ color: '#666', marginBottom: 20 }}>
          Генерируйте ключи для регистрации новых пользователей. Каждый ключ можно использовать один раз.
        </p>

        <button
          onClick={generateKey}
          style={{
            padding: '12px 24px',
            background: '#667eea',
            color: '#fff',
            border: 'none',
            borderRadius: 5,
            cursor: 'pointer',
            fontSize: 16,
            fontWeight: 'bold',
            marginBottom: 20
          }}
        >
          Сгенерировать новый ключ
        </button>

        {inviteKey && (
          <div style={{
            background: '#f0f9ff',
            border: '2px solid #3b82f6',
            padding: 20,
            borderRadius: 8,
            marginBottom: 20
          }}>
            <h3 style={{ marginTop: 0, color: '#1e40af' }}>Новый ключ создан!</h3>
            <div style={{
              background: '#fff',
              padding: 15,
              borderRadius: 5,
              fontFamily: 'monospace',
              fontSize: '1.2em',
              wordBreak: 'break-all',
              marginBottom: 15,
              border: '1px solid #ddd'
            }}>
              {inviteKey}
            </div>
            <button
              onClick={() => copyToClipboard(inviteKey)}
              style={{
                padding: '8px 16px',
                background: '#3b82f6',
                color: '#fff',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer',
                marginRight: 10
              }}
            >
              Скопировать
            </button>
            <button
              onClick={() => setInviteKey('')}
              style={{
                padding: '8px 16px',
                background: '#6b7280',
                color: '#fff',
                border: 'none',
                borderRadius: 4,
                cursor: 'pointer'
              }}
            >
              Скрыть
            </button>
          </div>
        )}

        <h3 style={{ color: '#2c3e50', marginTop: 30 }}>История ключей</h3>
        {keys.length === 0 ? (
          <p style={{ color: '#888', fontStyle: 'italic' }}>Ключи ещё не создавались.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff' }}>
              <thead>
                <tr style={{ background: '#2c3e50', color: '#fff' }}>
                  <th style={{ padding: 12, textAlign: 'left' }}>Ключ</th>
                  <th style={{ padding: 12, textAlign: 'center' }}>Статус</th>
                  <th style={{ padding: 12, textAlign: 'left' }}>Создан</th>
                  <th style={{ padding: 12, textAlign: 'center' }}>Действия</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => (
                  <tr key={key.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: 12, fontFamily: 'monospace', fontSize: '0.9em' }}>
                      {key.key}
                    </td>
                    <td style={{ padding: 12, textAlign: 'center' }}>
                      {key.is_used ? (
                        <span style={{ background: '#fee2e2', color: '#991b1b', padding: '4px 12px', borderRadius: 12, fontSize: '0.85em' }}>
                          Использован
                        </span>
                      ) : (
                        <span style={{ background: '#d1fae5', color: '#065f46', padding: '4px 12px', borderRadius: 12, fontSize: '0.85em' }}>
                          Активен
                        </span>
                      )}
                    </td>
                    <td style={{ padding: 12, fontSize: '0.9em', color: '#666' }}>
                      {new Date(key.created_at).toLocaleString('ru-RU')}
                    </td>
                    <td style={{ padding: 12, textAlign: 'center' }}>
                      {!key.is_used && (
                        <button
                          onClick={() => copyToClipboard(key.key)}
                          style={{
                            padding: '6px 12px',
                            background: '#3b82f6',
                            color: '#fff',
                            border: 'none',
                            borderRadius: 4,
                            cursor: 'pointer',
                            fontSize: '0.85em'
                          }}
                        >
                          Копировать
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Секция 2: Настройки ML */}
      <div style={{ background: '#fff', padding: 25, borderRadius: 8, border: '1px solid #ddd' }}>
        <h2 style={{ marginTop: 0, color: '#2c3e50' }}>Настройки ML-модели</h2>
        <p style={{ color: '#666', marginBottom: 20 }}>
          Порог чувствительности определяет, насколько агрессивно система блокирует подозрительный трафик.
          Активная модель используется для анализа всех входящих окон метрик.
        </p>

        {/* Выбор активной модели */}
        <div style={{ marginBottom: 25, padding: 15, background: '#f8f9fa', borderRadius: 5 }}>
          <label style={{ display: 'block', marginBottom: 10, fontWeight: 'bold' }}>
            Активная модель для анализа трафика:
          </label>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {availableModels.map((model) => (
              <button
                key={model.name}
                onClick={() => changeActiveModel(model.name)}
                disabled={model.status !== 'loaded' || model.is_active}
                style={{
                  padding: '10px 20px',
                  background: model.is_active ? '#27ae60' : (model.status === 'loaded' ? '#667eea' : '#95a5a6'),
                  color: 'white',
                  border: model.is_active ? '2px solid #16a085' : '2px solid transparent',
                  borderRadius: 5,
                  cursor: (model.status === 'loaded' && !model.is_active) ? 'pointer' : 'not-allowed',
                  fontWeight: model.is_active ? 'bold' : 'normal',
                  fontSize: 14,
                  opacity: model.status === 'loaded' ? 1 : 0.6
                }}
              >
                {model.name.replace('_', ' ')}
                {model.is_active && ' (активна)'}
                {model.status !== 'loaded' && ' (не загружена)'}
              </button>
            ))}
          </div>
        </div>

        {/* Порог чувствительности */}
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: 'block', marginBottom: 10, fontWeight: 'bold' }}>
            Порог чувствительности: <span style={{ color: '#667eea', fontSize: '1.2em' }}>{mlThreshold.toFixed(2)}</span>
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={mlThreshold}
            onChange={(e) => setMlThreshold(parseFloat(e.target.value))}
            style={{ width: '100%' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85em', color: '#888', marginTop: 5 }}>
            <span>0.0 (очень строго)</span>
            <span>1.0 (очень мягко)</span>
          </div>
        </div>

        <button
          onClick={saveMLSettings}
          style={{
            padding: '12px 24px',
            background: '#27ae60',
            color: '#fff',
            border: 'none',
            borderRadius: 5,
            cursor: 'pointer',
            fontSize: 16,
            fontWeight: 'bold'
          }}
        >
          Сохранить настройки порога
        </button>
      </div>
    </div>
  )
}