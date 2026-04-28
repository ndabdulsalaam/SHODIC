import { FiArrowLeft } from 'react-icons/fi'
import { Link, useParams } from 'react-router-dom'
import { fallbackDocs } from '../data/fallbacks'
import { useApiResource } from '../hooks/useApiResource'

export default function DocDetailPage() {
  const { slug } = useParams()
  const fallbackSection = fallbackDocs.find((section) => section.slug === slug) || fallbackDocs[0]
  const { data } = useApiResource(`/docs/${slug}/`, { section: fallbackSection })
  const section = data.section || fallbackSection

  return (
    <article className="article-page">
      <Link className="text-link" to="/docs">
        <FiArrowLeft aria-hidden="true" /> Docs
      </Link>
      <p className="eyebrow">{section.product?.name || 'Fildah'}</p>
      <h1>{section.title}</h1>
      <p className="article-page__summary">{section.summary}</p>
      <div className="rich-text">
        {section.body?.split('\n').map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    </article>
  )
}
