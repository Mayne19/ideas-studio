/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { getProject } from '@/api/projects'
import type { Project } from '@/types'

type ProjectContextValue = {
  project: Project | null
  loading: boolean
  refetch: () => void
}

const ProjectContext = createContext<ProjectContextValue | null>(null)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const { projectId } = useParams<{ projectId?: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(false)
  const [tick, setTick] = useState(0)

  const refetch = useCallback(() => setTick((t) => t + 1), [])

  useEffect(() => {
    if (!projectId) return
    let cancelled = false
    Promise.resolve().then(() => { if (!cancelled) setLoading(true) })
    getProject(projectId)
      .then((p) => { if (!cancelled) { setProject(p); setLoading(false) } })
      .catch(() => { if (!cancelled) { setProject(null); setLoading(false) } })
    return () => { cancelled = true }
  }, [projectId, tick])

  return (
    <ProjectContext.Provider value={{ project, loading, refetch }}>
      {children}
    </ProjectContext.Provider>
  )
}

export function useProject(): ProjectContextValue {
  const ctx = useContext(ProjectContext)
  if (!ctx) throw new Error('useProject doit être utilisé dans ProjectProvider')
  return ctx
}
