import { FiBookOpen, FiArrowRight } from 'react-icons/fi'
import { Link } from 'react-router-dom'
import EmptyState from '../components/EmptyState'
import { fallbackDocs } from '../data/fallbacks'
import { useApiResource } from '../hooks/useApiResource'

export default function DocsPage() {
  const { data } = useApiResource('/docs/', { sections: fallbackDocs })
  const sections = data.sections || []

  return (
    <section className="page-section">
      <div className="page-hero">
        <p className="eyebrow">Documentation</p>
        <h1>Product and platform notes.</h1>
        <p>Reference material for Fildah, shared account behavior, and product-specific namespaces.</p>
      </div>
      {sections.length ? (
        <div className="content-grid">
          {sections.map((section) => (
            <Link className="content-card" key={section.slug} to={`/docs/${section.slug}`}>
              <FiBookOpen aria-hidden="true" />
              <p className="eyebrow">{section.product?.name || 'Fildah'}</p>
              <h3>{section.title}</h3>
              <p>{section.summary}</p>
              <span className="text-link">
                Read <FiArrowRight aria-hidden="true" />
              </span>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="Docs are being prepared." message="Published documentation will appear here." />
      )}
    </section>
  )
}
