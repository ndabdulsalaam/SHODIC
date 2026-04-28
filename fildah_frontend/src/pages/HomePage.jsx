import { FiArrowRight, FiShield, FiTarget, FiUsers } from 'react-icons/fi'
import { Link } from 'react-router-dom'
import ProductCard from '../components/ProductCard'
import { fallbackHome } from '../data/fallbacks'
import { useApiResource } from '../hooks/useApiResource'

const trustIcons = [FiShield, FiTarget, FiUsers]

export default function HomePage() {
  const { data } = useApiResource('/home/', fallbackHome)
  const product = data.primary_product || fallbackHome.primary_product
  const featuredProducts = data.featured_products?.length ? data.featured_products : [product]
  const posts = data.recent_posts || []

  return (
    <>
      <section className="hero-section">
        <div className="hero-section__content">
          <p className="eyebrow">Fildah parent platform</p>
          <h1>{data.brand?.tagline || fallbackHome.brand.tagline}</h1>
          <p className="hero-section__lead">{data.brand?.description || fallbackHome.brand.description}</p>
          <div className="hero-section__actions">
            <Link className="button button--primary" to="/products">
              Products <FiArrowRight aria-hidden="true" />
            </Link>
            <Link className="button button--secondary" to="/account">
              Account
            </Link>
          </div>
        </div>
        <div className="hero-product" style={{ '--product-primary': product.primary_color, '--product-secondary': product.secondary_color }}>
          {(product.logo_url || product.slug === 'rxchat') && (
            <img className="hero-product__image" src={product.logo_url || '/rx-logo.png'} alt={`${product.name} logo`} />
          )}
          <p className="eyebrow">First live product</p>
          <h2>{product.name}</h2>
          <p>{product.short_description || product.summary}</p>
          <a className="text-link" href={product.frontend_url}>
            Open {product.name} <FiArrowRight aria-hidden="true" />
          </a>
        </div>
      </section>

      <section className="section section--peek">
        <div className="section__heading">
          <p className="eyebrow">Product directory</p>
          <h2>Focused products with distinct identities.</h2>
        </div>
        <div className="product-grid">
          {featuredProducts.map((item) => (
            <ProductCard key={item.slug} product={item} />
          ))}
        </div>
      </section>

      <section className="section section--band">
        <div className="section__heading">
          <p className="eyebrow">Trust posture</p>
          <h2>Built for sensitive, practical work.</h2>
        </div>
        <div className="trust-grid">
          {(data.trust_points || fallbackHome.trust_points).map((point, index) => {
            const Icon = trustIcons[index] || FiShield
            return (
              <article className="trust-item" key={point.title}>
                <Icon aria-hidden="true" />
                <h3>{point.title}</h3>
                <p>{point.summary}</p>
              </article>
            )
          })}
        </div>
      </section>

      <section className="section">
        <div className="section__heading section__heading--inline">
          <div>
            <p className="eyebrow">Updates</p>
            <h2>Latest from Fildah.</h2>
          </div>
          <Link className="text-link" to="/blog">
            View all <FiArrowRight aria-hidden="true" />
          </Link>
        </div>
        {posts.length ? (
          <div className="content-grid">
            {posts.map((post) => (
              <Link className="content-card" key={post.slug} to={`/blog/${post.slug}`}>
                <p className="eyebrow">{post.product?.name || 'Fildah'}</p>
                <h3>{post.title}</h3>
                <p>{post.excerpt}</p>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state empty-state--inline">
            <h3>Updates are being prepared.</h3>
            <p>Product news and company notes will appear here as they are published.</p>
          </div>
        )}
      </section>
    </>
  )
}
