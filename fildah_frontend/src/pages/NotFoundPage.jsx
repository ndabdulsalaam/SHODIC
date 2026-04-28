import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <section className="page-section">
      <div className="empty-state">
        <p className="eyebrow">404</p>
        <h1>Page not found.</h1>
        <p>The Fildah page you are looking for is not available.</p>
        <Link className="button button--primary" to="/">
          Home
        </Link>
      </div>
    </section>
  )
}
