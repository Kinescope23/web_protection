import { render, screen } from '@testing-library/react'
import App from './App'

describe('App Component', () => {
  it('renders login form correctly', () => {
    render(<App />)
    
    // Проверяем заголовок формы
    expect(screen.getByText(/Вход в Net Protector/i)).toBeInTheDocument()
    
    // Проверяем поля ввода по placeholder
    expect(screen.getByPlaceholderText(/Email/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Пароль/i)).toBeInTheDocument()
    
    // Проверяем кнопки
    expect(screen.getByRole('button', { name: /Войти/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Google/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /GitHub/i })).toBeInTheDocument()
  })
})