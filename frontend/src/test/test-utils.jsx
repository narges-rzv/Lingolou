import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'
import { LanguageProvider } from '../context/LanguageContext'

function AllProviders({ children }) {
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

function customRender(ui, options) {
  return render(ui, { wrapper: AllProviders, ...options })
}

// Re-export everything from RTL
export * from '@testing-library/react'
// Override render method
export { customRender as render }
