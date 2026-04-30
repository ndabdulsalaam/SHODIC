import { useEffect } from 'react'
import { FiArrowUpRight, FiInstagram, FiLinkedin, FiMenu, FiTwitter, FiX } from 'react-icons/fi'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useState } from 'react'
import BrandLogo from './BrandLogo'

const RXCHAT_URL = 'https://rxchat.fildah.com'

const navItems = [
  { label: 'Products', path: '/products' },
  { label: 'About', path: '/about' },
  { label: 'Blog', path: '/blog' },
  { label: 'Contact', path: '/contact' },
]

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

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
      <ScrollToTop />
      <header className="site-header">
        <div className="site-header__inner">
          <BrandLogo />
          <nav className="site-nav" aria-label="Primary navigation">
            <NavItems />
          </nav>
          <div className="site-header__actions">
            <a className="button button--header" href={RXCHAT_URL}>
              RxChat <FiArrowUpRight aria-hidden="true" />
            </a>
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
            <a className="mobile-nav__rxchat" href={RXCHAT_URL}>
              Open RxChat <FiArrowUpRight aria-hidden="true" />
            </a>
            <NavItems onNavigate={() => setMenuOpen(false)} />
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
            <p>Health technology products built with care,<br />trust, and practical support.</p>
          </div>
          <nav className="site-footer__nav" aria-label="Footer navigation">
            <NavLink to="/products">Products</NavLink>
            <NavLink to="/about">About</NavLink>
            <NavLink to="/blog">Blog</NavLink>
            <NavLink to="/contact">Contact</NavLink>
            <NavLink to="/docs">Docs</NavLink>
            <NavLink to="/docs/privacy">Privacy Policy</NavLink>
          </nav>
          <div className="site-footer__bottom">
            <p className="site-footer__copyright">© {new Date().getFullYear()} Fildah. All rights reserved.</p>
            <div className="site-footer__social">
              <a href="https://twitter.com/fildahHQ" target="_blank" rel="noopener noreferrer" aria-label="Fildah on Twitter">
                <FiTwitter />
              </a>
              <a href="https://linkedin.com/company/fildah" target="_blank" rel="noopener noreferrer" aria-label="Fildah on LinkedIn">
                <FiLinkedin />
              </a>
              <a href="https://instagram.com/fildah" target="_blank" rel="noopener noreferrer" aria-label="Fildah on Instagram">
                <FiInstagram />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
