import { Outlet, useLocation } from 'react-router-dom'
import { ProjectProvider } from '@/context/ProjectContext'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { AppSidebar } from '@/components/app-sidebar'
import Topbar from './Topbar'

function AppShellInner() {
  const location = useLocation()
  const isEditor = /\/articles\/[^/]+\/edit/.test(location.pathname)
  const isProduction = location.pathname.endsWith('/production') || location.pathname.endsWith('/kanban')
  const fullHeight = isEditor || isProduction

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="flex h-full w-full overflow-hidden bg-bg">
        <AppSidebar />
        <SidebarInset className="relative flex flex-1 flex-col overflow-hidden min-w-0 bg-bg border-0 m-0 peer-data-[variant=inset]:m-0 peer-data-[variant=inset]:rounded-none peer-data-[state=collapsed]:peer-data-[variant=inset]:ml-0">
          <Topbar />
          <main className={fullHeight ? 'flex-1 overflow-hidden' : 'flex-1 overflow-y-auto p-8'}>
            <Outlet />
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  )
}

export default function AppShell() {
  return (
    <ProjectProvider>
      <AppShellInner />
    </ProjectProvider>
  )
}
