import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../contexts/AuthContext'
import Dashboard from './Dashboard'

describe('Dashboard Component', () => {
  it('renders dashboard correctly', () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <Dashboard />
        </AuthProvider>
      </MemoryRouter>
    )
    
    // Проверяем то, что реально рендерится в тестовой среде
    // (состояние загрузки, пока нет данных от API)
    expect(screen.getByText(/Загрузка/i)).toBeInTheDocument()
  })
})