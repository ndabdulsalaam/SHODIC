import ProductCard from '../components/ProductCard'
import { fallbackProduct } from '../data/fallbacks'
import { useApiResource } from '../hooks/useApiResource'

export default function ProductsPage() {
  const { data } = useApiResource('/products/', { products: [fallbackProduct] })
  const products = data.products?.length ? data.products : [fallbackProduct]

  return (
    <section className="page-section">
      <div className="page-hero">
        <p className="eyebrow">Products</p>
        <h1>Independent product experiences under Fildah.</h1>
        <p>
          Each product can keep its own interface, colors, and domain while remaining easy to discover
          from the parent brand.
        </p>
      </div>
      <div className="product-grid">
        {products.map((product) => (
          <ProductCard key={product.slug} product={product} />
        ))}
      </div>
    </section>
  )
}
