import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from '../App'

describe('App Root Component', () => {
  it('renders without crashing', () => {
    // Note: Render triggers React Router inside App.tsx
    const { container } = render(<App />)
    expect(container).toBeInTheDocument()
  })
})
