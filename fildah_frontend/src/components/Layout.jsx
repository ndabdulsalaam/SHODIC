import { useState } from 'react'
import { FiMenu, FiUser, FiX } from 'react-icons/fi'
import { NavLink, Outlet } from 'react-router-dom'
import BrandLogo from './BrandLogo'

const navItems = [
  { label: 'Products', path: '/products' },
  { label: 'Docs', path: '/docs' },
  { label: 'Blog', path: '/blog' },
  { label: 'About', path: '/about' },
  { label: 'Support', path: '/support' },
]

function NavItems({ onNavigate }) {
  return navItems.map((item) => (
    <NavLink
      className={({ isActive }) => (isActive ? 'site-nav__link site-nav__link--active' : 'site-nav__link')}
      key={item.path}
      onClick={onNavigate}
      to={item.path}
    >
      {item.label}
    </NavLink>
  ))
}

export default function Layout() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="site-header__inner">
          <BrandLogo />
          <nav className="site-nav" aria-label="Primary navigation">
            <NavItems />
          </nav>
          <div className="site-header__actions">
            <NavLink className="icon-link" to="/account" aria-label="Account">
              <FiUser />
            </NavLink>
            <button
              className="icon-button site-header__menu"
              type="button"
              aria-label={menuOpen ? 'Close navigation' : 'Open navigation'}
              onClick={() => setMenuOpen((value) => !value)}
            >
              {menuOpen ? <FiX /> : <FiMenu />}
            </button>
          </div>
        </div>
        {menuOpen && (
          <nav className="mobile-nav" aria-label="Mobile navigation">
            <NavItems onNavigate={() => setMenuOpen(false)} />
            <NavLink className="mobile-nav__account" to="/account" onClick={() => setMenuOpen(false)}>
              Account
            </NavLink>
          </nav>
        )}
      </header>

      <main>
        <Outlet />
      </main>

      <footer className="site-footer">
        <div className="site-footer__inner">
          <div>
            <BrandLogo />
            <p>Focused health technology products under one careful parent brand.</p>
          </div>
          <div className="site-footer__links">
            <NavLink to="/products">Products</NavLink>
            <NavLink to="/docs">Docs</NavLink>
            <NavLink to="/blog">Blog</NavLink>
            <NavLink to="/support">Support</NavLink>
          </div>
        </div>
      </footer>
    </div>
  )
}
