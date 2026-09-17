import { render, screen } from '@testing-library/react'

// Простой smoke-тест без импорта App (чтобы не тянуть роутинг и контексты)
describe('Smoke test', () => {
  test('Jest работает корректно', () => {
    expect(1 + 1).toBe(2)
  })

  test('Рендеринг элемента', () => {
    render(<div data-testid="test">Net Protector</div>)
    expect(screen.getByTestId('test')).toHaveTextContent('Net Protector')
  })
})