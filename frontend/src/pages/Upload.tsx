import { useState } from 'react'
import { useAuth, api } from '../contexts/AuthContext'

const CHUNK_SIZE = 10 * 1024 * 1024 // 10 МБ на чанк

export default function Upload() {
  const { user } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')

  const calculateSHA256 = async (file: File): Promise<string> => {
    const buffer = await file.arrayBuffer()
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
  }

  const handleUpload = async () => {
    if (!file) return
    setError('')
    setStatus('Вычисление контрольной суммы SHA-256...')
    
    const checksum = await calculateSHA256(file)
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
    
    setStatus('Инициализация загрузки...')
    const initForm = new FormData()
    initForm.append('filename', file.name)
    initForm.append('total_size', file.size.toString())
    initForm.append('total_chunks', totalChunks.toString())
    
    try {
      const initRes = await api.post('/upload/init', initForm)
      const uploadId = initRes.data.upload_id
      
      for (let i = 0; i < totalChunks; i++) {
        const start = i * CHUNK_SIZE
        const end = Math.min(start + CHUNK_SIZE, file.size)
        const chunk = file.slice(start, end)
        
        const chunkForm = new FormData()
        chunkForm.append('upload_id', uploadId)
        chunkForm.append('chunk_index', i.toString())
        chunkForm.append('file', chunk)
        
        await api.post('/upload/chunk', chunkForm)
        setProgress(Math.round(((i + 1) / totalChunks) * 100))
        setStatus(`Загружено ${i + 1} из ${totalChunks} чанков`)
      }
      
      setStatus('Сборка и проверка файла на сервере...')
      const completeForm = new FormData()
      completeForm.append('upload_id', uploadId)
      completeForm.append('checksum', checksum)
      
      await api.post('/upload/complete', completeForm)
      setStatus('Загрузка успешно завершена!')
      setProgress(100)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки')
      setStatus('')
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 600, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h1>Загрузка больших файлов (Chunked Upload)</h1>
      <p>Поддерживаются файлы до 5 ГБ. Файл автоматически разбивается на части по 10 МБ.</p>
      
      <input 
        type="file" 
        onChange={(e) => setFile(e.target.files?.[0] || null)} 
        style={{ marginBottom: 20, padding: 10, border: '1px solid #ddd', borderRadius: 5, width: '100%' }} 
      />
      
      <button 
        onClick={handleUpload} 
        disabled={!file}
        style={{ padding: '10px 20px', background: file ? '#667eea' : '#ccc', color: 'white', border: 'none', borderRadius: 5, cursor: file ? 'pointer' : 'not-allowed', width: '100%' }}
      >
        Начать загрузку
      </button>
      
      {status && <p style={{ marginTop: 20, fontWeight: 'bold', color: '#333' }}>{status}</p>}
      
      {progress > 0 && (
        <div style={{ marginTop: 10, background: '#eee', borderRadius: 5, overflow: 'hidden' }}>
          <div style={{ width: `${progress}%`, background: '#27ae60', height: 24, transition: 'width 0.3s', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontSize: 12 }}>
            {progress}%
          </div>
        </div>
      )}
      
      {error && <p style={{ color: '#e74c3c', marginTop: 20, background: '#fdecea', padding: 10, borderRadius: 5 }}>Ошибка: {error}</p>}
    </div>
  )
}