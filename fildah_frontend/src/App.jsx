import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'

const AboutPage = lazy(() => import('./pages/AboutPage'))
const AccountPage = lazy(() => import('./pages/AccountPage'))
const BlogDetailPage = lazy(() => import('./pages/BlogDetailPage'))
const BlogPage = lazy(() => import('./pages/BlogPage'))
const DocDetailPage = lazy(() => import('./pages/DocDetailPage'))
const DocsPage = lazy(() => import('./pages/DocsPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))
const ProductDetailPage = lazy(() => import('./pages/ProductDetailPage'))
const ProductsPage = lazy(() => import('./pages/ProductsPage'))
const SupportPage = lazy(() => import('./pages/SupportPage'))

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={null}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="about" element={<AboutPage />} />
            <Route path="products" element={<ProductsPage />} />
            <Route path="products/:slug" element={<ProductDetailPage />} />
            <Route path="docs" element={<DocsPage />} />
            <Route path="docs/:slug" element={<DocDetailPage />} />
            <Route path="blog" element={<BlogPage />} />
            <Route path="blog/:slug" element={<BlogDetailPage />} />
            <Route path="contact" element={<SupportPage />} />
            <Route path="support" element={<SupportPage />} />
            <Route path="account" element={<AccountPage />} />
            <Route path="account/profile" element={<AccountPage view="profile" />} />
            <Route path="account/products" element={<AccountPage view="products" />} />
            <Route path="account/organizations" element={<AccountPage view="organizations" />} />
            <Route path="account/billing" element={<AccountPage view="billing" />} />
            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
