import { useState } from 'react'
import { api } from '../contexts/AuthContext'

export default function Admin() {
  return (
    <div style={{ padding: 20, maxWidth: 800, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1>Админ-панель</h1>
      <p>Управление пользователями и системой.</p>
      <p style={{ color: '#888' }}>Функционал в разработке...</p>
    </div>
  )

  const [inviteKey, setInviteKey] = useState('')
  const [mlThreshold, setMlThreshold] = useState(0.3)

  const generateKey = async () => {
    try {
      const res = await api.post('/admin/generate-invite')
      setInviteKey(res.data.invitation_key)
    } catch (e) { console.error(e) }
  }

  const saveMLSettings = async () => {
    try {
      await api.post('/admin/ml-settings', { threshold: mlThreshold })
      alert('Настройки ML сохранены')
    } catch (e) { console.error(e) }
  }

  return (
    <div style={{ padding: 20, maxWidth: 1200, margin: '0 auto' }}>
      <h1>Админ-панель</h1>
      
      {/* Секция 1: Управление доступом */}
      <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #ddd', marginBottom: 20 }}>
        <h3>Генерация ключа регистрации</h3>
        <p>Новые пользователи могут зарегистрироваться только с этим ключом.</p>
        <button onClick={generateKey} style={{ padding: '8px 16px', background: '#667eea', color: '#fff', border: 'none', borderRadius: 4 }}>
          Сгенерировать новый ключ
        </button>
        {inviteKey && (
          <div style={{ marginTop: 10, padding: 10, background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 4, fontFamily: 'monospace' }}>
            {inviteKey}
          </div>
        )}
      </div>

      {/* Секция 2: Настройки ML (Расширенный режим) */}
      <div style={{ background: '#fff', padding: 20, borderRadius: 8, border: '1px solid #ddd' }}>
        <h3>Настройки ML-модели (Расширенный режим)</h3>
        <label>
          Порог чувствительности аномалий (0.0 - 1.0): 
          <input 
            type="range" min="0" max="1" step="0.05" 
            value={mlThreshold} 
            onChange={(e) => setMlThreshold(parseFloat(e.target.value))}
            style={{ marginLeft: 10 }}
          />
          <span style={{ marginLeft: 10, fontWeight: 'bold' }}>{mlThreshold}</span>
        </label>
        <p style={{ fontSize: '0.9em', color: '#666' }}>
          Модель анализирует агрегированные окна трафика (30 секунд). 
          Более низкий порог увеличивает количество блокировок (включая ложные срабатывания).
        </p>
        <button onClick={saveMLSettings} style={{ marginTop: 10, padding: '8px 16px', background: '#27ae60', color: '#fff', border: 'none', borderRadius: 4 }}>
          Применить настройки
        </button>
      </div>
    </div>
  )
}