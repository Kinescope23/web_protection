import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Register from './Register'

describe('Register Component', () => {
  it('renders registration form correctly', () => {
    render(
      <MemoryRouter>
        <Register />
      </MemoryRouter>
    )
    expect(screen.getByText(/регистрация|создать аккаунт/i)).toBeInTheDocument()
    

    expect(screen.getByPlaceholderText(/email/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/пароль/i)).toBeInTheDocument()
  })
})