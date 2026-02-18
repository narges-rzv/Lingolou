import { render, type RenderOptions } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { LanguageProvider } from '../context/LanguageContext'
import type { ReactElement, ReactNode } from 'react'

function AllProviders({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <LanguageProvider>
        <AuthProvider>
          {children}
        </AuthProvider>
      </LanguageProvider>
    </BrowserRouter>
  )
}

function customRender(ui: ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return render(ui, { wrapper: AllProviders, ...options })
}

// Re-export everything from RTL
export * from '@testing-library/react'
// Override render method
export { customRender as render }
