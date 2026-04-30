import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ChatPage from './pages/ChatPage'
import './index.css'

const AuthPage = lazy(() => import('./pages/AuthPage'))

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={null}>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/auth" element={<AuthPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default App
