import type { ReactNode } from 'react'

type AuthLayoutProps = {
  children: ReactNode
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-full flex-col items-center justify-center bg-bg px-4 py-12">
      <div className="mb-8 text-center">
        <h1 className="text-[22px] font-semibold text-primary tracking-tight">
          Ideas Studio
        </h1>
        <p className="mt-1 text-[13px] text-secondary">
          CMS headless SEO assisté par IA
        </p>
      </div>
      <div className="w-full max-w-sm rounded-[8px] border border-border bg-bg p-8 shadow-card">
        {children}
      </div>
    </div>
  )
}
