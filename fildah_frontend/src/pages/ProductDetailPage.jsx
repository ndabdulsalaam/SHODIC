import { FiArrowLeft, FiArrowUpRight, FiDatabase, FiGlobe, FiLink } from 'react-icons/fi'
import { Link, useParams } from 'react-router-dom'
import { fallbackProduct } from '../data/fallbacks'
import { useApiResource } from '../hooks/useApiResource'

export default function ProductDetailPage() {
  const { slug } = useParams()
  const { data } = useApiResource(`/products/${slug}/`, { product: fallbackProduct })
  const product = data.product || fallbackProduct
  const style = {
    '--product-primary': product.primary_color,
    '--product-secondary': product.secondary_color,
  }

  return (
    <section className="page-section product-detail" style={style}>
      <Link className="text-link" to="/products">
        <FiArrowLeft aria-hidden="true" /> Products
      </Link>
      <div className="product-detail__hero">
        <div>
          <p className="eyebrow">{product.category || 'Product'}</p>
          <h1>{product.name}</h1>
          <p>{product.tagline || product.short_description}</p>
          {product.frontend_url && (
            <a className="button button--product" href={product.frontend_url}>
              Open {product.name} <FiArrowUpRight aria-hidden="true" />
            </a>
          )}
        </div>
        {(product.logo_url || product.slug === 'rxchat') ? (
          <img className="product-detail__image" src={product.logo_url || '/rx-logo.png'} alt={`${product.name} logo`} />
        ) : (
          <div className="product-detail__mark" aria-hidden="true">
            {product.name?.slice(0, 2) || 'Fx'}
          </div>
        )}
      </div>

      <div className="product-detail__body">
        <article>
          <h2>Product overview</h2>
          <p>{product.long_description || product.short_description}</p>
        </article>
        <aside className="product-facts">
          <div>
            <FiGlobe aria-hidden="true" />
            <span>Frontend</span>
            <strong>{product.frontend_url || 'Coming soon'}</strong>
          </div>
          <div>
            <FiDatabase aria-hidden="true" />
            <span>API namespace</span>
            <strong>{product.api_namespace || 'Not assigned'}</strong>
          </div>
          <div>
            <FiLink aria-hidden="true" />
            <span>Status</span>
            <strong>{product.status}</strong>
          </div>
        </aside>
      </div>
    </section>
  )
}
