import {
  FiArrowLeft,
  FiArrowRight,
  FiArrowUpRight,
  FiCheckCircle,
  FiMessageCircle,
  FiShield,
  FiUsers,
} from 'react-icons/fi'
import { Link, useParams } from 'react-router-dom'
import { fallbackProduct } from '../data/fallbacks'
import { useApiResource } from '../hooks/useApiResource'

const rxChatFeatures = [
  'Plain-language medicine information for everyday questions.',
  'Prompts that ask for context before giving general guidance.',
  'Visible safety reminders for urgent symptoms and clinical decisions.',
  'A patient-friendly starting point before speaking with a professional.',
]

const rxChatUseCases = [
  {
    title: 'For patients',
    summary: 'Understand medicine instructions, possible side effects, and when to ask for help.',
    icon: FiUsers,
  },
  {
    title: 'For caregivers',
    summary: 'Ask clearer questions while supporting someone else with their medicines.',
    icon: FiMessageCircle,
  },
  {
    title: 'For safety',
    summary: 'Stay aware of boundaries, red flags, and when professional care matters.',
    icon: FiShield,
  },
]

const howItWorks = [
  'Ask your medicine or health-product question in simple words.',
  'Add helpful context such as age group, dose, symptoms, or existing medicines.',
  'Use the answer as a guide for better next questions, not as a final diagnosis or prescription.',
]

export default function ProductDetailPage() {
  const { slug } = useParams()
  const { data } = useApiResource(`/products/${slug}/`, { product: fallbackProduct })
  const product = data.product || fallbackProduct
  const productUrl = product.frontend_url || (product.slug === 'rxchat' ? fallbackProduct.frontend_url : '')
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
          {productUrl && (
            <a className="button button--product" href={productUrl}>
              Open {product.name} <FiArrowUpRight aria-hidden="true" />
            </a>
          )}
        </div>
        <div className="product-preview" aria-label={`${product.name} product preview`}>
          <div className="product-preview__header">
            {(product.logo_url || product.slug === 'rxchat') ? (
              <img src={product.logo_url || '/rx-logo.png'} alt={`${product.name} logo`} />
            ) : (
              <span>{product.name?.slice(0, 2) || 'Fx'}</span>
            )}
            <div>
              <strong>{product.name}</strong>
              <small>{product.status?.replace(/_/g, ' ') || 'active'}</small>
            </div>
          </div>
          <div className="chat-bubble chat-bubble--user">I have a medicine question.</div>
          <div className="chat-bubble chat-bubble--assistant">
            I can help with general information. Share the medicine name and what you want to understand.
          </div>
        </div>
      </div>

      <div className="product-detail__body">
        <article>
          <p className="eyebrow">What it does</p>
          <h2>Medicine guidance that stays practical and careful.</h2>
          <p>{product.long_description || product.short_description}</p>
          <ul className="feature-list">
            {rxChatFeatures.map((feature) => (
              <li key={feature}>
                <FiCheckCircle aria-hidden="true" />
                <span>{feature}</span>
              </li>
            ))}
          </ul>
        </article>
        <aside className="product-facts">
          <div>
            <FiUsers aria-hidden="true" />
            <span>Who it is for</span>
            <strong>Patients, caregivers, and people preparing better medicine questions.</strong>
          </div>
          <div>
            <FiShield aria-hidden="true" />
            <span>Safety model</span>
            <strong>General information with professional-care reminders.</strong>
          </div>
          <div>
            <FiArrowUpRight aria-hidden="true" />
            <span>Access</span>
            <strong>{product.frontend_url ? 'Available now' : 'Coming soon'}</strong>
          </div>
        </aside>
      </div>

      <section className="product-detail__section">
        <div className="section__heading">
          <p className="eyebrow">Use cases</p>
          <h2>Built for the questions people actually ask.</h2>
        </div>
        <div className="use-case-grid">
          {rxChatUseCases.map((item) => {
            const Icon = item.icon
            return (
              <article className="use-case-card" key={item.title}>
                <Icon aria-hidden="true" />
                <h3>{item.title}</h3>
                <p>{item.summary}</p>
              </article>
            )
          })}
        </div>
      </section>

      <section className="product-detail__section product-detail__section--split">
        <div>
          <p className="eyebrow">How it works</p>
          <h2>A simple flow from question to next step.</h2>
        </div>
        <ol className="step-list">
          {howItWorks.map((step, index) => (
            <li key={step}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="product-cta">
        <div>
          <p className="eyebrow">Ready to try it?</p>
          <h2>Open {product.name} and ask your first medicine question.</h2>
          <p>Use it as a practical starting point, then speak with a licensed professional for personal clinical decisions.</p>
        </div>
        <div className="product-cta__actions">
          {productUrl && (
            <a className="button button--primary" href={productUrl}>
              Open {product.name} <FiArrowRight aria-hidden="true" />
            </a>
          )}
          <Link className="button button--secondary" to="/contact">
            Contact Fildah
          </Link>
        </div>
      </section>
    </section>
  )
}
