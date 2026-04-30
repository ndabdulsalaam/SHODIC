import { FiArrowUpRight } from 'react-icons/fi'
import { Link } from 'react-router-dom'

function formatStatus(status) {
  return (status || 'active').replace(/_/g, ' ')
}

export default function ProductCard({ product, compact = false }) {
  const isRxChat = product.slug === 'rxchat'
  const audience = isRxChat ? 'Patients and caregivers' : 'Focused health users'
  const benefit = isRxChat
    ? 'Plain-language medicine guidance with visible safety boundaries.'
    : product.short_description || product.summary || 'A focused health technology product from Fildah.'
  const style = {
    '--product-primary': product.primary_color || '#5CB832',
    '--product-secondary': product.secondary_color || '#1A6BC4',
  }

  return (
    <article className={compact ? 'product-card product-card--compact' : 'product-card'} style={style}>
      <div className="product-card__header">
        <span className="product-card__mark" aria-hidden="true">
          {product.name?.slice(0, 2) || 'Fx'}
        </span>
        <span className="status-pill">{formatStatus(product.status)}</span>
      </div>
      <div>
        <p className="eyebrow">{product.category || 'Product'}</p>
        <h3>{product.name}</h3>
        <p>{product.tagline || product.summary || product.short_description}</p>
      </div>
      <dl className="product-card__facts">
        <div>
          <dt>Audience</dt>
          <dd>{audience}</dd>
        </div>
        <div>
          <dt>Benefit</dt>
          <dd>{benefit}</dd>
        </div>
      </dl>
      <div className="product-card__actions">
        <Link className="text-link" to={`/products/${product.slug}`}>
          Details <FiArrowUpRight aria-hidden="true" />
        </Link>
        {product.frontend_url && (
          <a className="text-link" href={product.frontend_url}>
            Open <FiArrowUpRight aria-hidden="true" />
          </a>
        )}
      </div>
    </article>
  )
}
