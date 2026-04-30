import { FiArrowRight, FiShield } from 'react-icons/fi'
import { Link } from 'react-router-dom'
import ProductCard from '../components/ProductCard'
import { fallbackProduct } from '../data/fallbacks'
import { useApiResource } from '../hooks/useApiResource'

export default function ProductsPage() {
  const { data } = useApiResource('/products/', { products: [fallbackProduct] })
  const products = data.products?.length ? data.products : [fallbackProduct]
  const flagship = products.find((product) => product.slug === 'rxchat') || products[0]
  const flagshipUrl = flagship.frontend_url || fallbackProduct.frontend_url
  const style = {
    '--product-primary': flagship.primary_color,
    '--product-secondary': flagship.secondary_color,
  }

  return (
    <section className="page-section products-page" style={style}>
      <div className="page-hero">
        <p className="eyebrow">Products</p>
        <h1>Start with RxChat. Discover what Fildah builds next.</h1>
        <p>
          Fildah builds focused health technology products for real user questions. RxChat is the live flagship
          product, with future tools added only when they are ready for public use.
        </p>
      </div>

      <article className="products-spotlight">
        <div>
          <p className="eyebrow">Live now</p>
          <h2>{flagship.name}</h2>
          <p>{flagship.long_description || flagship.short_description}</p>
          <div className="hero-section__actions">
            <a className="button button--product" href={flagshipUrl}>
              Open {flagship.name} <FiArrowRight aria-hidden="true" />
            </a>
            <Link className="button button--secondary" to={`/products/${flagship.slug}`}>
              Product details
            </Link>
          </div>
        </div>
        <div className="products-spotlight__note">
          <FiShield aria-hidden="true" />
          <strong>Built with safety boundaries</strong>
          <p>RxChat is a starting point for medicine information, not a replacement for a pharmacist or doctor.</p>
        </div>
      </article>

      <div className="product-grid">
        {products.map((product) => (
          <ProductCard key={product.slug} product={product} />
        ))}
        {products.length === 1 && (
          <article className="product-card product-card--future">
            <div className="product-card__header">
              <span className="product-card__mark" aria-hidden="true">F</span>
              <span className="status-pill">coming soon</span>
            </div>
            <div>
              <p className="eyebrow">Future products</p>
              <h3>More Fildah tools will appear here.</h3>
              <p>New products will be added to this directory when they have a clear use case and public access path.</p>
            </div>
          </article>
        )}
      </div>
    </section>
  )
}
