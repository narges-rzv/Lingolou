import { createContext, useContext, useState, type ReactNode } from 'react';
import { DEFAULT_LANGUAGE } from '../languages';

interface LanguageContextValue {
  language: string;
  setLanguage: (lang: string) => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState(
    () => localStorage.getItem('selectedLanguage') || DEFAULT_LANGUAGE
  );

  const setLanguage = (lang: string) => {
    setLanguageState(lang);
    localStorage.setItem('selectedLanguage', lang);
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
