import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { ProjectProvider } from '@/context/ProjectContext'
import Sidebar from './Sidebar'
import Topbar from './Topbar'

function AppShellInner() {
  const location = useLocation()
  const isEditor = /\/articles\/[^/]+\/edit/.test(location.pathname)
  const isProduction = location.pathname.endsWith('/production') || location.pathname.endsWith('/kanban')
  const fullHeight = isEditor || isProduction

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="flex h-full overflow-hidden bg-app">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((v) => !v)} />
      <div className="flex flex-1 flex-col overflow-hidden min-w-0">
        <Topbar />
        <main className={fullHeight ? 'flex-1 overflow-hidden' : 'flex-1 overflow-y-auto p-8'}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default function AppShell() {
  return (
    <ProjectProvider>
      <AppShellInner />
    </ProjectProvider>
  )
}
