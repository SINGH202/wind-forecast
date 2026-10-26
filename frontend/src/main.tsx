import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // The API client retries a waking service. A second retry layer would
      // multiply those attempts and drop the loading state between them.
      retry: false,
    },
  },
})
const root = document.getElementById('root')

if (!root) {
  throw new Error('root element is missing')
}

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
