/* eslint-disable react-refresh/only-export-components */
import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
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

const ArticleEditorPage = lazy(() => import('@/pages/projects/editor/ArticleEditorPage'))
const IdeasPipelinePage = lazy(() => import('@/pages/projects/ideas/IdeasPipelinePage'))
const KanbanPage = lazy(() => import('@/pages/projects/kanban/KanbanPage'))
const PerformanceDashboardPage = lazy(() => import('@/pages/projects/performance/PerformanceDashboardPage'))
const PerformanceArticlesPage = lazy(() => import('@/pages/projects/performance/PerformanceArticlesPage'))
const ArticlePerformancePage = lazy(() => import('@/pages/projects/performance/ArticlePerformancePage'))
const RecommendationsPage = lazy(() => import('@/pages/projects/recommendations/RecommendationsPage'))
const GeneratePage = lazy(() => import('@/pages/projects/generate/GeneratePage'))
const CalendarPage = lazy(() => import('@/pages/projects/calendar/CalendarPage'))
const TrafficPage = lazy(() => import('@/pages/projects/traffic/TrafficPage'))
const NotificationsPage = lazy(() => import('@/pages/projects/notifications/NotificationsPage'))
const ProjectStrategyPage = lazy(() => import('@/pages/projects/settings/ProjectStrategyPage'))
const ProjectProvidersPage = lazy(() => import('@/pages/projects/settings/ProjectProvidersPage'))
const MediaPage = lazy(() => import('@/pages/projects/media/MediaPage'))
const AccountPage = lazy(() => import('@/pages/account/AccountPage'))

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
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/projects" replace />,
      },
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
            path: 'integration',
            element: <ProjectIntegrationPage />,
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
        element: (
          <Suspense fallback={<LoadingState />}>
            <KanbanPage />
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


