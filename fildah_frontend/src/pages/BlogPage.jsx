import { FiArrowRight } from 'react-icons/fi'
import { Link } from 'react-router-dom'
import EmptyState from '../components/EmptyState'
import { useApiResource } from '../hooks/useApiResource'

export default function BlogPage() {
  const { data } = useApiResource('/blog/', { posts: [] })
  const posts = data.posts || []

  return (
    <section className="page-section">
      <div className="page-hero">
        <p className="eyebrow">Blog and updates</p>
        <h1>Company notes, product updates, and launch context.</h1>
        <p>Published updates from the Fildah parent brand and its product teams.</p>
      </div>
      {posts.length ? (
        <div className="content-grid">
          {posts.map((post) => (
            <Link className="content-card" key={post.slug} to={`/blog/${post.slug}`}>
              <p className="eyebrow">{post.product?.name || 'Fildah'}</p>
              <h3>{post.title}</h3>
              <p>{post.excerpt}</p>
              <span className="text-link">
                Read <FiArrowRight aria-hidden="true" />
              </span>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState title="No updates yet." message="Published company and product updates will appear here." />
      )}
    </section>
  )
}
