import { FiArrowLeft } from 'react-icons/fi'
import { Link, useParams } from 'react-router-dom'
import { useApiResource } from '../hooks/useApiResource'

const fallbackPost = {
  title: 'Fildah update',
  slug: 'fildah-update',
  excerpt: 'Updates from the Fildah parent brand.',
  body: 'Published updates will appear here.',
  product: null,
}

export default function BlogDetailPage() {
  const { slug } = useParams()
  const { data } = useApiResource(`/blog/${slug}/`, { post: fallbackPost })
  const post = data.post || fallbackPost

  return (
    <article className="article-page">
      <Link className="text-link" to="/blog">
        <FiArrowLeft aria-hidden="true" /> Blog
      </Link>
      <p className="eyebrow">{post.product?.name || 'Fildah'}</p>
      <h1>{post.title}</h1>
      <p className="article-page__summary">{post.excerpt}</p>
      <div className="rich-text">
        {post.body?.split('\n').map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
    </article>
  )
}
