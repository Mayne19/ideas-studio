/* eslint-disable react-refresh/only-export-components */
import { lazy, Suspense, useEffect } from 'react'
import { createBrowserRouter, Navigate, useParams, useRouteError } from 'react-router-dom'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import ForgotPasswordPage from '@/pages/auth/ForgotPasswordPage'
import ResetPasswordPage from '@/pages/auth/ResetPasswordPage'
import ProjectsPage from '@/pages/projects/ProjectsPage'
import ProjectDashboardPage from '@/pages/projects/ProjectDashboardPage'
import ProjectSettingsPage from '@/pages/projects/settings/ProjectSettingsPage'
import ProjectMembersPage from '@/pages/projects/settings/ProjectMembersPage'
import ProjectIntegrationPage from '@/pages/projects/settings/ProjectIntegrationPage'
import CategoriesPage from '@/pages/projects/categories/CategoriesPage'
import ArticlesPage from '@/pages/projects/articles/ArticlesPage'
import ArticlePreviewPage from '@/pages/projects/articles/ArticlePreviewPage'
import AppShell from '@/components/layout/AppShell'
import SettingsLayout from '@/components/layout/SettingsLayout'
import ProtectedRoute from '@/components/shared/ProtectedRoute'
import LoadingState from '@/components/ui/LoadingState'
import {
  ContactPage,
  FeaturesPage,
  LandingPage,
  LegalPage,
  SupportPage,
} from '@/pages/public/PublicPages'

const ArticleEditorPage = lazy(() => import('@/pages/projects/editor/ArticleEditorPage'))
const ArchivesPage = lazy(() => import('@/pages/projects/articles/ArchivesPage'))
const IdeasPipelinePage = lazy(() => import('@/pages/projects/ideas/IdeasPipelinePage'))
const KanbanPage = lazy(() => import('@/pages/projects/kanban/KanbanPage'))
const PerformanceDashboardPage = lazy(() => import('@/pages/projects/performance/PerformanceDashboardPage'))
const PerformanceArticlesPage = lazy(() => import('@/pages/projects/performance/PerformanceArticlesPage'))
const ArticlePerformancePage = lazy(() => import('@/pages/projects/performance/ArticlePerformancePage'))
const RecommendationsPage = lazy(() => import('@/pages/projects/recommendations/RecommendationsPage'))
const ValidationPage = lazy(() => import('@/pages/projects/validation/ValidationPage'))
const GeneratePage = lazy(() => import('@/pages/projects/generate/GeneratePage'))
const CalendarPage = lazy(() => import('@/pages/projects/calendar/CalendarPage'))
const TrafficPage = lazy(() => import('@/pages/projects/traffic/TrafficPage'))
const NotificationsPage = lazy(() => import('@/pages/projects/notifications/NotificationsPage'))
const ProjectStrategyPage = lazy(() => import('@/pages/projects/settings/ProjectStrategyPage'))
const ProjectProvidersPage = lazy(() => import('@/pages/projects/settings/ProjectProvidersPage'))
const ProjectCalloutsPage = lazy(() => import('@/pages/projects/settings/ProjectCalloutsPage'))
const ProjectPipelinePage = lazy(() => import('@/pages/projects/settings/ProjectPipelinePage'))
const ProjectAgentsPage = lazy(() => import('@/pages/projects/settings/ProjectAgentsPage'))
const MediaPage = lazy(() => import('@/pages/projects/media/MediaPage'))
const AccountPage = lazy(() => import('@/pages/account/AccountPage'))
const DocumentationPage = lazy(() => import('@/pages/DocumentationPage'))

function OptimizationsRedirect() {
  const { projectId } = useParams<{ projectId: string }>()
  return <Navigate to={`/projects/${projectId}/recommendations`} replace />
}

function RouteErrorFallback() {
  const error = useRouteError()
  const message = error instanceof Error ? error.message : String(error)
  const isChunkError =
    message.includes('dynamically imported module') ||
    message.includes('Failed to fetch dynamically imported module') ||
    message.includes('Importing a module script failed')

  useEffect(() => {
    if (!isChunkError) return
    const key = `ideas-studio:chunk-reload:${window.location.pathname}`
    if (window.sessionStorage.getItem(key)) return
    window.sessionStorage.setItem(key, '1')
    window.location.reload()
  }, [isChunkError])

  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      <div className="w-full max-w-md rounded-[8px] border border-border bg-surface p-6 text-center shadow-soft">
        <p className="text-[15px] font-semibold text-primary">
          {isChunkError ? "L'application vient d'être mise à jour." : 'Impossible de charger cette page.'}
        </p>
        <p className="mt-2 text-[13px] leading-relaxed text-secondary">
          {isChunkError
            ? 'Rechargez la page pour récupérer les derniers fichiers du frontend.'
            : 'Une erreur technique empêche cette page de s’afficher pour le moment.'}
        </p>
        <button
          type="button"
          onClick={() => {
            window.sessionStorage.removeItem(`ideas-studio:chunk-reload:${window.location.pathname}`)
            window.location.reload()
          }}
          className="mt-4 rounded-[6px] bg-primary px-4 py-2 text-[13px] font-medium text-bg transition-colors hover:opacity-90"
        >
          Rafraîchir
        </button>
      </div>
    </div>
  )
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/forgot-password',
    element: <ForgotPasswordPage />,
  },
  {
    path: '/reset-password',
    element: <ResetPasswordPage />,
  },
  {
    path: '/',
    element: <LandingPage />,
    errorElement: <RouteErrorFallback />,
  },
  {
    path: '/features',
    element: <FeaturesPage />,
    errorElement: <RouteErrorFallback />,
  },
  // Pricing temporairement désactivé
  // {
  //   path: '/pricing',
  //   element: <PricingPage />,
  //   errorElement: <RouteErrorFallback />,
  // },
  {
    path: '/support',
    element: <SupportPage />,
    errorElement: <RouteErrorFallback />,
  },
  {
    path: '/contact',
    element: <ContactPage />,
    errorElement: <RouteErrorFallback />,
  },
  {
    path: '/privacy',
    element: <LegalPage kind="privacy" />,
    errorElement: <RouteErrorFallback />,
  },
  {
    path: '/terms',
    element: <LegalPage kind="terms" />,
    errorElement: <RouteErrorFallback />,
  },
  {
    path: '/security',
    element: <LegalPage kind="security" />,
    errorElement: <RouteErrorFallback />,
  },
  {
    path: '/documentation',
    element: (
      <Suspense fallback={<LoadingState />}>
        <DocumentationPage />
      </Suspense>
    ),
    errorElement: <RouteErrorFallback />,
  },
  {
    path: '/docs',
    element: <Navigate to="/documentation" replace />,
  },
  {
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    errorElement: <RouteErrorFallback />,
    children: [
      {
        path: 'projects',
        element: <ProjectsPage />,
      },
      {
        path: 'projects/:projectId',
        element: <Navigate to="dashboard" replace />,
      },
      {
        path: 'projects/:projectId/dashboard',
        element: <ProjectDashboardPage />,
      },
      /* Settings group */
      {
        path: 'projects/:projectId/settings',
        element: <SettingsLayout />,
        children: [
          {
            index: true,
            element: <ProjectSettingsPage />,
          },
          {
            path: 'general',
            element: <ProjectSettingsPage />,
          },
          {
            path: 'strategy',
            element: (
              <Suspense fallback={<LoadingState />}>
                <ProjectStrategyPage />
              </Suspense>
            ),
          },
          {
            path: 'providers',
            element: (
              <Suspense fallback={<LoadingState />}>
                <ProjectProvidersPage />
              </Suspense>
            ),
          },
          {
            path: 'members',
            element: <ProjectMembersPage />,
          },
          {
            path: 'team',
            element: <ProjectMembersPage />,
          },
          {
            path: 'integration',
            element: <ProjectIntegrationPage />,
          },
          {
            path: 'callouts',
            element: (
              <Suspense fallback={<LoadingState />}>
                <ProjectCalloutsPage />
              </Suspense>
            ),
          },
          {
            path: 'pipeline',
            element: (
              <Suspense fallback={<LoadingState />}>
                <ProjectPipelinePage />
              </Suspense>
            ),
          },
          {
            path: 'agents',
            element: (
              <Suspense fallback={<LoadingState />}>
                <ProjectAgentsPage />
              </Suspense>
            ),
          },
          {
            path: 'profile',
            element: (
              <Suspense fallback={<LoadingState />}>
                <AccountPage />
              </Suspense>
            ),
          },
        ],
      },
      /* Convenience alias for integration */
      {
        path: 'projects/:projectId/connect',
        element: <Navigate to="settings/integration" replace />,
      },
      {
        path: 'projects/:projectId/articles',
        element: <ArticlesPage />,
      },
      {
        path: 'projects/:projectId/articles/:articleId/edit',
        element: (
          <Suspense fallback={<LoadingState />}>
            <ArticleEditorPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/articles/:articleId/preview',
        element: <ArticlePreviewPage />,
      },
      {
        path: 'projects/:projectId/archives',
        element: (
          <Suspense fallback={<LoadingState />}>
            <ArchivesPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/categories',
        element: <CategoriesPage />,
      },
      {
        path: 'projects/:projectId/ideas',
        element: (
          <Suspense fallback={<LoadingState />}>
            <IdeasPipelinePage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/kanban',
        element: <Navigate to="../production" replace />,
      },
      {
        path: 'projects/:projectId/production',
        element: (
          <Suspense fallback={<LoadingState />}>
            <KanbanPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/validation',
        element: (
          <Suspense fallback={<LoadingState />}>
            <ValidationPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/performance',
        element: (
          <Suspense fallback={<LoadingState />}>
            <PerformanceDashboardPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/performance/articles',
        element: (
          <Suspense fallback={<LoadingState />}>
            <PerformanceArticlesPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/performance/:articleId',
        element: (
          <Suspense fallback={<LoadingState />}>
            <ArticlePerformancePage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/recommendations',
        element: (
          <Suspense fallback={<LoadingState />}>
            <RecommendationsPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/optimizations',
        element: <OptimizationsRedirect />,
      },
      {
        path: 'projects/:projectId/generate',
        element: (
          <Suspense fallback={<LoadingState />}>
            <GeneratePage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/calendar',
        element: (
          <Suspense fallback={<LoadingState />}>
            <CalendarPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/traffic',
        element: (
          <Suspense fallback={<LoadingState />}>
            <TrafficPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/notifications',
        element: (
          <Suspense fallback={<LoadingState />}>
            <NotificationsPage />
          </Suspense>
        ),
      },
      {
        path: 'projects/:projectId/media',
        element: (
          <Suspense fallback={<LoadingState />}>
            <MediaPage />
          </Suspense>
        ),
      },
      {
        path: 'account',
        element: (
          <Suspense fallback={<LoadingState />}>
            <AccountPage />
          </Suspense>
        ),
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
])
