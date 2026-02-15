import { createContext, useContext, useState } from 'react';
import { DEFAULT_LANGUAGE } from '../languages';

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(
    () => localStorage.getItem('selectedLanguage') || DEFAULT_LANGUAGE
  );

  const setLanguage = (lang) => {
    setLanguageState(lang);
    localStorage.setItem('selectedLanguage', lang);
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used within LanguageProvider');
  return ctx;
}
