import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { LanguageProvider, useLanguage } from '../../context/LanguageContext'

function wrapper({ children }) {
  return <LanguageProvider>{children}</LanguageProvider>
}

describe('LanguageContext', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('defaults to DEFAULT_LANGUAGE', () => {
    const { result } = renderHook(() => useLanguage(), { wrapper })
    expect(result.current.language).toBe('Chinese (Mandarin)')
  })

  it('setLanguage updates state and localStorage', () => {
    const { result } = renderHook(() => useLanguage(), { wrapper })

    act(() => {
      result.current.setLanguage('Arabic')
    })

    expect(result.current.language).toBe('Arabic')
    expect(localStorage.getItem('selectedLanguage')).toBe('Arabic')
  })

  it('reads persisted language from localStorage', () => {
    localStorage.setItem('selectedLanguage', 'French')

    const { result } = renderHook(() => useLanguage(), { wrapper })
    expect(result.current.language).toBe('French')
  })
})
