import { useState, useEffect, useRef } from 'react'
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
}

interface AgentInfo {
  id: number
  agent_id: string
  user_id: number
  username: string
  name: string
  domain: string | null
  is_active: boolean
  last_seen: string | null
  created_at: string | null
}

interface UserInfo {
  id: number
  username: string
  email: string
  role: string
}

export default function Admin() {
  // Ключи
  const [inviteKey, setInviteKey] = useState('')
  const [keys, setKeys] = useState<InvitationKey[]>([])

  // ML-модели
  const [availableModels, setAvailableModels] = useState<MLModelInfo[]>([])
  const [modelFile, setModelFile] = useState<File | null>(null)
  const [scalerFile, setScalerFile] = useState<File | null>(null)
  const [uploadingModel, setUploadingModel] = useState(false)
  const modelInputRef = useRef<HTMLInputElement>(null)
  const scalerInputRef = useRef<HTMLInputElement>(null)

  // Агенты
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [users, setUsers] = useState<UserInfo[]>([])
  const [newAgentId, setNewAgentId] = useState('')
  const [newAgentName, setNewAgentName] = useState('')
  const [newAgentDomain, setNewAgentDomain] = useState('')
  const [newAgentUserId, setNewAgentUserId] = useState<number | ''>('')

  // Общие
  const [stats, setStats] = useState<any>(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    fetchKeys()
    fetchStats()
    fetchModels()
    fetchAgents()
    fetchUsers()
  }, [])

  // === Загрузка данных ===

  const fetchKeys = async () => {
    try {
      const res = await api.get('/admin/invitation-keys')
      setKeys(res.data)
    } catch (e) { console.error(e) }
  }

  const fetchStats = async () => {
    try {
      const res = await api.get('/admin/stats')
      setStats(res.data)
    } catch (e) { console.error(e) }
  }

  const fetchModels = async () => {
    try {
      const res = await api.get('/admin/ml-models')
      setAvailableModels(res.data.models_info || [])
    } catch (e) { console.error(e) }
  }

  const fetchAgents = async () => {
    try {
      const res = await api.get('/admin/agents')
      setAgents(res.data)
    } catch (e) { console.error(e) }
  }

  const fetchUsers = async () => {
    try {
      const res = await api.get('/dashboard/users')
      setUsers(res.data.map((u: any) => ({
        id: u.id,
        username: u.username,
        email: u.email,
        role: u.role
      })))
    } catch (e) { console.error(e) }
  }

  // === Управление ключами ===

  const generateKey = async () => {
    try {
      const res = await api.post('/admin/generate-invite')
      setInviteKey(res.data.invitation_key)
      showMessage('Ключ успешно создан!')
      fetchKeys()
    } catch (e: any) {
      showMessage(e.response?.data?.detail || 'Ошибка создания ключа', true)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    showMessage('Ключ скопирован в буфер обмена!')
  }

  // === Управление ML-моделями ===

  const handleModelUpload = async () => {
    if (!modelFile || !scalerFile) return
    setUploadingModel(true)
    try {
      const formData = new FormData()
      formData.append('model_file', modelFile)
      formData.append('scaler_file', scalerFile)
      await api.post('/admin/ml-models', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      showMessage('Модель успешно загружена')
      setModelFile(null)
      setScalerFile(null)
      if (modelInputRef.current) modelInputRef.current.value = ''
      if (scalerInputRef.current) scalerInputRef.current.value = ''
      fetchModels()
    } catch (e: any) {
      showMessage(e.response?.data?.detail || 'Ошибка загрузки модели', true)
    } finally {
      setUploadingModel(false)
    }
  }

  const handleDeleteModel = async (modelName: string) => {
    if (!confirm(`Удалить модель '${modelName}'?`)) return
    try {
      await api.delete(`/admin/ml-models/${modelName}`)
      showMessage(`Модель '${modelName}' удалена`)
      fetchModels()
    } catch (e: any) {
      showMessage(e.response?.data?.detail || 'Ошибка удаления', true)
    }
  }

  // === Управление агентами ===

  const createAgent = async () => {
    if (!newAgentId || !newAgentName || !newAgentUserId) {
      showMessage('Заполните все обязательные поля', true)
      return
    }
    try {
      await api.post('/admin/agents', null, {
        params: {
          agent_id: newAgentId,
          user_id: newAgentUserId,
          name: newAgentName,
          domain: newAgentDomain
        }
      })
      showMessage(`Агент '${newAgentId}' создан`)
      setNewAgentId('')
      setNewAgentName('')
      setNewAgentDomain('')
      setNewAgentUserId('')
      fetchAgents()
    } catch (e: any) {
      showMessage(e.response?.data?.detail || 'Ошибка создания агента', true)
    }
  }

  const deleteAgent = async (agentDbId: number, agentId: string) => {
    if (!confirm(`Удалить агента '${agentId}'?`)) return
    try {
      await api.delete(`/admin/agents/${agentDbId}`)
      showMessage(`Агент '${agentId}' удалён`)
      fetchAgents()
    } catch (e: any) {
      showMessage(e.response?.data?.detail || 'Ошибка удаления агента', true)
    }
  }

  // === Утилиты ===

  const showMessage = (text: string, isError = false) => {
    setMessage(isError ? `Ошибка: ${text}` : text)
    setTimeout(() => setMessage(''), 3000)
  }

  return (
    <div style={{ padding: 20, maxWidth: 1200, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: '#2c3e50', marginBottom: 30 }}>Админ-панель</h1>

      {message && (
        <div style={{
          padding: 15,
          marginBottom: 20,
          background: message.startsWith('Ошибка') ? '#fee2e2' : '#d1fae5',
          border: `1px solid ${message.startsWith('Ошибка') ? '#fca5a5' : '#6ee7b7'}`,
          borderRadius: 8,
          color: message.startsWith('Ошибка') ? '#991b1b' : '#065f46',
          fontWeight: 'bold'
        }}>
          {message}
        </div>
      )}

      {/* Статистика */}
      {stats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 15,
          marginBottom: 30
        }}>
          <StatBox color="#0369a1" bg="#f0f9ff" border="#bae6fd" value={stats.total_users} label="Пользователей" />
          <StatBox color="#92400e" bg="#fef3c7" border="#fcd34d" value={stats.active_invitation_keys} label="Активных ключей" />
          <StatBox color="#166534" bg="#f0fdf4" border="#86efac" value={stats.currently_blocked_ips} label="Заблокировано IP" />
          <StatBox color="#7c3aed" bg="#faf5ff" border="#d8b4fe" value={stats.total_agents} label="Агентов" />
        </div>
      )}

      {/* === Секция 1: Агенты === */}
      <Section title="Управление агентами">
        <p style={{ color: '#666', marginBottom: 20 }}>
          Создайте агента и привяжите его к пользователю. После этого агент сможет отправлять метрики,
          а администратор — видеть их на дашборде пользователя.
        </p>

        {/* Форма создания агента */}
        <div style={{ padding: 15, background: '#f0f9ff', borderRadius: 5, border: '1px solid #bae6fd', marginBottom: 20 }}>
          <h4 style={{ marginTop: 0, color: '#0369a1' }}>Создать нового агента</h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 10, marginBottom: 15 }}>
            <input
              type="text"
              placeholder="ID агента (например: agent-001)"
              value={newAgentId}
              onChange={e => setNewAgentId(e.target.value)}
              style={inputStyle}
            />
            <input
              type="text"
              placeholder="Имя агента (например: Web Server 1)"
              value={newAgentName}
              onChange={e => setNewAgentName(e.target.value)}
              style={inputStyle}
            />
            <input
              type="text"
              placeholder="Домен (example.com) — опционально"
              value={newAgentDomain}
              onChange={e => setNewAgentDomain(e.target.value)}
              style={inputStyle}
            />
            <select
              value={newAgentUserId}
              onChange={e => setNewAgentUserId(e.target.value ? parseInt(e.target.value) : '')}
              style={inputStyle}
            >
              <option value="">-- Выберите пользователя --</option>
              {users.map(u => (
                <option key={u.id} value={u.id}>
                  {u.username} ({u.email}) — {u.role}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={createAgent}
            disabled={!newAgentId || !newAgentName || !newAgentUserId}
            style={{
              padding: '10px 20px',
              background: (!newAgentId || !newAgentName || !newAgentUserId) ? '#95a5a6' : '#667eea',
              color: 'white',
              border: 'none',
              borderRadius: 5,
              cursor: (!newAgentId || !newAgentName || !newAgentUserId) ? 'not-allowed' : 'pointer',
              fontWeight: 'bold'
            }}
          >
            Создать агента
          </button>
        </div>

        {/* Список агентов */}
        <h4 style={{ color: '#2c3e50' }}>Зарегистрированные агенты ({agents.length})</h4>
        {agents.length === 0 ? (
          <p style={{ color: '#888', fontStyle: 'italic' }}>Агенты ещё не зарегистрированы.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff' }}>
              <thead>
                <tr style={{ background: '#2c3e50', color: '#fff' }}>
                  <th style={thStyle}>ID агента</th>
                  <th style={thStyle}>Имя</th>
                  <th style={thStyle}>Владелец</th>
                  <th style={thStyle}>Домен</th>
                  <th style={thStyle}>Последняя активность</th>
                  <th style={thStyle}>Действия</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((a) => (
                  <tr key={a.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ ...tdStyle, fontFamily: 'monospace' }}>{a.agent_id}</td>
                    <td style={tdStyle}>{a.name}</td>
                    <td style={tdStyle}>
                      <span style={{
                        padding: '2px 8px',
                        background: '#e0e7ff',
                        color: '#3730a3',
                        borderRadius: 10,
                        fontSize: '0.85em'
                      }}>
                        {a.username}
                      </span>
                    </td>
                    <td style={tdStyle}>{a.domain || '—'}</td>
                    <td style={{ ...tdStyle, fontSize: '0.85em', color: '#666' }}>
                      {a.last_seen ? new Date(a.last_seen).toLocaleString('ru-RU') : 'никогда'}
                    </td>
                    <td style={tdStyle}>
                      <button
                        onClick={() => deleteAgent(a.id, a.agent_id)}
                        style={{
                          padding: '6px 12px',
                          background: '#e74c3c',
                          color: 'white',
                          border: 'none',
                          borderRadius: 4,
                          cursor: 'pointer',
                          fontSize: '0.85em'
                        }}
                      >
                        Удалить
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* === Секция 2: Ключи приглашения === */}
      <Section title="Управление ключами приглашения">
        <p style={{ color: '#666', marginBottom: 20 }}>
          Генерируйте ключи для регистрации новых пользователей.
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
              style={{ padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', marginRight: 10 }}
            >
              Скопировать
            </button>
            <button
              onClick={() => setInviteKey('')}
              style={{ padding: '8px 16px', background: '#6b7280', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
            >
              Скрыть
            </button>
          </div>
        )}

        <h4 style={{ color: '#2c3e50', marginTop: 30 }}>История ключей</h4>
        {keys.length === 0 ? (
          <p style={{ color: '#888', fontStyle: 'italic' }}>Ключи ещё не создавались.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff' }}>
              <thead>
                <tr style={{ background: '#2c3e50', color: '#fff' }}>
                  <th style={thStyle}>Ключ</th>
                  <th style={thStyle}>Статус</th>
                  <th style={thStyle}>Создан</th>
                  <th style={thStyle}>Действия</th>
                </tr>
              </thead>
              <tbody>
                {keys.map((key) => (
                  <tr key={key.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: '0.9em' }}>{key.key}</td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      <span style={{
                        background: key.is_used ? '#fee2e2' : '#d1fae5',
                        color: key.is_used ? '#991b1b' : '#065f46',
                        padding: '4px 12px',
                        borderRadius: 12,
                        fontSize: '0.85em'
                      }}>
                        {key.is_used ? 'Использован' : 'Активен'}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, fontSize: '0.9em', color: '#666' }}>
                      {new Date(key.created_at).toLocaleString('ru-RU')}
                    </td>
                    <td style={{ ...tdStyle, textAlign: 'center' }}>
                      {!key.is_used && (
                        <button
                          onClick={() => copyToClipboard(key.key)}
                          style={{ padding: '6px 12px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: '0.85em' }}
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
      </Section>

      {/* === Секция 3: ML-модели === */}
      <Section title="Управление ML-моделями">
        <p style={{ color: '#666', marginBottom: 20 }}>
          Загружайте новые пары файлов (.pkl и _scaler.pkl) или удаляйте неиспользуемые модели.
          Выбор активной модели и настройка порога чувствительности выполняются для каждого пользователя
          отдельно на странице метрик пользователя.
        </p>

        {/* Список моделей */}
        <div style={{ marginBottom: 25, padding: 15, background: '#f8f9fa', borderRadius: 5 }}>
          <label style={{ display: 'block', marginBottom: 10, fontWeight: 'bold' }}>Доступные модели:</label>
          {availableModels.length === 0 ? (
            <p style={{ color: '#888', fontStyle: 'italic' }}>Модели не найдены</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {availableModels.map((model) => (
                <div key={model.name} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: 12,
                  background: 'white',
                  borderRadius: 5,
                  border: '1px solid #e1e4e8'
                }}>
                  <div>
                    <strong style={{ fontSize: '1.05em' }}>{model.name.replace(/_/g, ' ')}</strong>
                    {model.status === 'loaded' ? (
                      <span style={{
                        marginLeft: 10, padding: '2px 10px', background: '#d1fae5',
                        color: '#065f46', borderRadius: 10, fontSize: '0.8em'
                      }}>
                        Загружена
                      </span>
                    ) : (
                      <span style={{
                        marginLeft: 10, padding: '2px 10px', background: '#fee2e2',
                        color: '#991b1b', borderRadius: 10, fontSize: '0.8em'
                      }}>
                        Не загружена
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteModel(model.name)}
                    disabled={model.status !== 'loaded'}
                    style={{
                      padding: '6px 14px',
                      background: model.status !== 'loaded' ? '#95a5a6' : '#e74c3c',
                      color: 'white',
                      border: 'none',
                      borderRadius: 4,
                      cursor: model.status !== 'loaded' ? 'not-allowed' : 'pointer',
                      fontSize: '0.85em'
                    }}
                  >
                    Удалить
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Загрузка новой модели */}
        <div style={{ padding: 15, background: '#f0f9ff', borderRadius: 5, border: '1px solid #bae6fd' }}>
          <h4 style={{ marginTop: 0, color: '#0369a1' }}>Загрузить новую модель</h4>
          <div style={{ display: 'flex', gap: 15, flexWrap: 'wrap', marginBottom: 15 }}>
            <div style={{ flex: 1, minWidth: 250 }}>
              <label style={{ display: 'block', fontSize: '0.9em', color: '#666', marginBottom: 5 }}>Файл модели (.pkl)</label>
              <input
                ref={modelInputRef}
                type="file"
                accept=".pkl"
                onChange={(e) => setModelFile(e.target.files?.[0] || null)}
                style={{ width: '100%' }}
              />
              {modelFile && <div style={{ fontSize: '0.8em', color: '#0369a1', marginTop: 5 }}>Выбран: {modelFile.name}</div>}
            </div>
            <div style={{ flex: 1, minWidth: 250 }}>
              <label style={{ display: 'block', fontSize: '0.9em', color: '#666', marginBottom: 5 }}>Файл скейлера (_scaler.pkl)</label>
              <input
                ref={scalerInputRef}
                type="file"
                accept=".pkl"
                onChange={(e) => setScalerFile(e.target.files?.[0] || null)}
                style={{ width: '100%' }}
              />
              {scalerFile && <div style={{ fontSize: '0.8em', color: '#0369a1', marginTop: 5 }}>Выбран: {scalerFile.name}</div>}
            </div>
          </div>
          <button
            onClick={handleModelUpload}
            disabled={!modelFile || !scalerFile || uploadingModel}
            style={{
              padding: '10px 20px',
              background: (!modelFile || !scalerFile || uploadingModel) ? '#95a5a6' : '#27ae60',
              color: 'white',
              border: 'none',
              borderRadius: 5,
              cursor: (!modelFile || !scalerFile || uploadingModel) ? 'not-allowed' : 'pointer',
              fontWeight: 'bold'
            }}
          >
            {uploadingModel ? 'Загрузка...' : 'Загрузить модель'}
          </button>
        </div>
      </Section>
    </div>
  )
}

// === Вспомогательные компоненты ===

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: '#fff', padding: 25, borderRadius: 8, border: '1px solid #ddd', marginBottom: 30 }}>
      <h2 style={{ marginTop: 0, color: '#2c3e50' }}>{title}</h2>
      {children}
    </div>
  )
}

function StatBox({ color, bg, border, value, label }: { color: string; bg: string; border: string; value: number; label: string }) {
  return (
    <div style={{ background: bg, padding: 20, borderRadius: 8, border: `1px solid ${border}` }}>
      <div style={{ fontSize: '2em', fontWeight: 'bold', color }}>{value}</div>
      <div style={{ color: color, fontSize: '0.9em' }}>{label}</div>
    </div>
  )
}

// === Стили ===

const inputStyle: React.CSSProperties = {
  padding: 10,
  border: '1px solid #ddd',
  borderRadius: 5,
  fontSize: 14
}

const thStyle: React.CSSProperties = {
  padding: 12,
  textAlign: 'left'
}

const tdStyle: React.CSSProperties = {
  padding: 12
}