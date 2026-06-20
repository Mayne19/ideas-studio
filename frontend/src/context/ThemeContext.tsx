import { createContext } from 'react'
import type { ReactNode } from 'react'

const ThemeContext = createContext<{ isDark: boolean } | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  return <ThemeContext.Provider value={{ isDark: false }}>{children}</ThemeContext.Provider>
}
