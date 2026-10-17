import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { lazy, Suspense } from 'react'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { AppShell } from '@/components/AppShell'
import { ChatHome } from '@/pages/ChatHome'
import { ConversationPage } from '@/pages/ConversationPage'
import { CrashPage, NotFoundPage } from '@/pages/NotFoundPage'

const LogPage = lazy(() => import('@/pages/LogPage').then((m) => ({ default: m.LogPage })))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 10_000 },
  },
})

const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    errorElement: <CrashPage />,
    children: [
      { index: true, element: <ChatHome /> },
      { path: 'c/:conversationId', element: <ConversationPage /> },
      {
        path: 'registro',
        element: (
          <Suspense fallback={<div className="ink-pulse m-8 h-48 rounded-xl bg-paper-deep" aria-hidden="true" />}>
            <LogPage />
          </Suspense>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
