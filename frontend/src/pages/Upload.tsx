import { useState, useRef } from 'react'
import { api } from '../contexts/AuthContext'

const CHUNK_SIZE = 10 * 1024 * 1024 // 10 МБ

export default function Upload() {
  const [file, setFile] = useState<File | null>(null)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Вычисление SHA-256 хеша файла в браузере
  const calculateSHA256 = async (file: File): Promise<string> => {
    const buffer = await file.arrayBuffer()
    const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
    const hashArray = Array.from(new Uint8Array(hashBuffer))
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('')
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFile(selectedFile)
      setProgress(0)
      setStatus('')
      setError('')
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setIsUploading(true)
    setError('')
    setStatus('Вычисление контрольной суммы файла...')

    try {
      // 1. Вычисляем SHA-256
      const checksum = await calculateSHA256(file)
      const totalSize = file.size
      const totalChunks = Math.ceil(totalSize / CHUNK_SIZE)

      // 2. Инициализация загрузки (ОТПРАВЛЯЕМ JSON!)
      setStatus('Инициализация загрузки...')
      const initRes = await api.post('/upload/init', {
        filename: file.name,
        total_size: totalSize,
        checksum: checksum
      }, {
        headers: { 'Content-Type': 'application/json' }
      })

      const { upload_id } = initRes.data

      // 3. Загрузка чанков (ОТПРАВЛЯЕМ FormData!)
      setStatus(`Загрузка файла... (0/${totalChunks} чанков)`)
      for (let i = 0; i < totalChunks; i++) {
        const start = i * CHUNK_SIZE
        const end = Math.min(start + CHUNK_SIZE, totalSize)
        const chunk = file.slice(start, end)

        const formData = new FormData()
        formData.append('upload_id', upload_id)
        formData.append('chunk_index', i.toString())
        formData.append('file', chunk)

        await api.post('/upload/chunk', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })

        const currentProgress = Math.round(((i + 1) / totalChunks) * 100)
        setProgress(currentProgress)
        setStatus(`Загрузка файла... (${i + 1}/${totalChunks} чанков)`)
      }

      // 4. Завершение загрузки
      setStatus('Сборка и проверка файла на сервере...')
      await api.post(`/upload/complete?upload_id=${upload_id}`)

      setStatus('Загрузка успешно завершена!')
      setFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (err: any) {
      console.error(err)
      setError(err.response?.data?.detail || 'Ошибка при загрузке файла')
      setStatus('')
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 600, margin: '0 auto', fontFamily: 'Arial, sans-serif' }}>
      <h2 style={{ color: '#2c3e50', marginBottom: 20 }}>Загрузка файлов</h2>
      
      <div style={{
        background: 'white',
        padding: 30,
        borderRadius: 8,
        border: '1px solid #e1e4e8',
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
      }}>
        <p style={{ color: '#666', marginBottom: 20 }}>
          Поддерживается загрузка файлов размером до 1 ГБ. Файл разбивается на чанки по 10 МБ для надежной передачи.
        </p>

        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileSelect}
          disabled={isUploading}
          style={{
            width: '100%',
            padding: 10,
            marginBottom: 20,
            border: '1px solid #ddd',
            borderRadius: 5
          }}
        />

        {file && (
          <div style={{ marginBottom: 20, padding: 15, background: '#f8f9fa', borderRadius: 5 }}>
            <div style={{ fontWeight: 'bold', marginBottom: 5 }}>{file.name}</div>
            <div style={{ fontSize: '0.9em', color: '#666' }}>
              Размер: {(file.size / (1024 * 1024)).toFixed(2)} МБ
            </div>
          </div>
        )}

        {status && (
          <div style={{ marginBottom: 15, color: '#3498db', fontWeight: 'bold' }}>
            {status}
          </div>
        )}

        {progress > 0 && progress < 100 && (
          <div style={{ marginBottom: 20 }}>
            <div style={{
              height: 20,
              background: '#ecf0f1',
              borderRadius: 10,
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${progress}%`,
                height: '100%',
                background: '#3498db',
                transition: 'width 0.3s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: '0.8em',
                fontWeight: 'bold'
              }}>
                {progress}%
              </div>
            </div>
          </div>
        )}

        {error && (
          <div style={{
            marginBottom: 15,
            padding: 10,
            background: '#fee2e2',
            color: '#991b1b',
            borderRadius: 5,
            fontSize: '0.9em'
          }}>
            {error}
          </div>
        )}

        <button
          onClick={handleUpload}
          disabled={!file || isUploading}
          style={{
            width: '100%',
            padding: 12,
            background: (!file || isUploading) ? '#95a5a6' : '#27ae60',
            color: 'white',
            border: 'none',
            borderRadius: 5,
            cursor: (!file || isUploading) ? 'not-allowed' : 'pointer',
            fontSize: 16,
            fontWeight: 'bold'
          }}
        >
          {isUploading ? 'Загрузка...' : 'Начать загрузку'}
        </button>
      </div>
    </div>
  )
}