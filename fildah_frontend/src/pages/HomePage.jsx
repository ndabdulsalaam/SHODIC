import { useState } from 'react'
import {
  FiArrowRight,
  FiBookOpen,
  FiCheckCircle,
  FiGlobe,
  FiHeart,
  FiMessageCircle,
  FiShield,
  FiTarget,
  FiTrendingUp,
  FiUsers,
} from 'react-icons/fi'
import { Link } from 'react-router-dom'
import ProductCard from '../components/ProductCard'
import { fallbackDifferentiators, fallbackHome, fallbackTestimonials } from '../data/fallbacks'
import { useApiResource } from '../hooks/useApiResource'

const trustIcons = [FiShield, FiHeart, FiUsers, FiTarget]
const diffIcons = [FiHeart, FiGlobe, FiTrendingUp]

const rxChatHelps = [
  {
    title: 'Medicine questions',
    summary: 'Ask about common uses, side effects, and practical medicine information in plain language.',
    icon: FiMessageCircle,
  },
  {
    title: 'Safer next steps',
    summary: 'Get guidance on when to speak with a pharmacist, doctor, or emergency service.',
    icon: FiShield,
  },
  {
    title: 'Everyday clarity',
    summary: 'Make health decisions with calmer context, not confusing search results.',
    icon: FiCheckCircle,
  },
]

const comingSoonCards = [
  {
    title: 'More focused health tools',
    summary: 'Future Fildah products will appear here when they are ready for public use.',
  },
]

export default function HomePage() {
  const { data } = useApiResource('/home/', fallbackHome)
  const product = data.primary_product || fallbackHome.primary_product
  const featuredProducts = data.featured_products?.length ? data.featured_products : [product]
  const posts = data.recent_posts || []
  const trustPoints = data.trust_points?.length ? data.trust_points : fallbackHome.trust_points
  const visibleTrustPoints = trustPoints.length >= 4 ? trustPoints : [...trustPoints, fallbackHome.trust_points[3]]
  const testimonials = data.testimonials?.length ? data.testimonials : fallbackTestimonials
  const differentiators = data.differentiators?.length ? data.differentiators : fallbackDifferentiators
  const productUrl = product.frontend_url || fallbackHome.primary_product.frontend_url
  const productStyle = {
    '--product-primary': product.primary_color,
    '--product-secondary': product.secondary_color,
  }

  const [newsletterEmail, setNewsletterEmail] = useState('')
  const [newsletterStatus, setNewsletterStatus] = useState('')

  function handleNewsletter(event) {
    event.preventDefault()
    if (!newsletterEmail) return
    setNewsletterStatus('Thank you! We will keep you updated.')
    setNewsletterEmail('')
    setTimeout(() => setNewsletterStatus(''), 4000)
  }

  return (
    <>
      {/* ── Hero ── */}
      <section className="hero-section" style={productStyle}>
        <div className="hero-section__content">
          <p className="eyebrow">Fildah health technology</p>
          <h1>{data.brand?.tagline || fallbackHome.brand.tagline}</h1>
          <p className="hero-section__lead">
            {data.brand?.description || fallbackHome.brand.description} Start with RxChat, a practical medicine
            information assistant made to help people ask clearer health questions.
          </p>
          <div className="hero-section__actions">
            <a className="button button--primary button--large" href={productUrl}>
              Open {product.name} <FiArrowRight aria-hidden="true" />
            </a>
            <Link className="button button--secondary button--large" to="/products">
              Explore products
            </Link>
          </div>
          <p className="hero-section__note">General health information only. Always speak with a licensed professional for clinical decisions.</p>
        </div>

        <div className="hero-preview" aria-label={`${product.name} product preview`}>
          <div className="hero-preview__topbar">
            <span className="hero-preview__dot" />
            <span className="hero-preview__dot" />
            <span className="hero-preview__dot" />
            <strong>{product.name}</strong>
          </div>
          <div className="hero-preview__body">
            <div className="chat-bubble chat-bubble--user">Can I take this medicine after food?</div>
            <div className="chat-bubble chat-bubble--assistant">
              It depends on the medicine. Share the name, dose, and who it is for, then confirm with your pharmacist
              if anything feels unclear.
            </div>
            <div className="hero-preview__panel">
              <FiShield aria-hidden="true" />
              <div>
                <strong>Safety boundary visible</strong>
                <span>RxChat explains when professional care is needed.</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust strip ── */}
      <section className="trust-strip" aria-label="Fildah trust signals">
        {visibleTrustPoints.map((point, index) => {
          const Icon = trustIcons[index] || FiShield
          return (
            <article className="trust-strip__item" key={point.title}>
              <Icon aria-hidden="true" />
              <span>{point.title}</span>
            </article>
          )
        })}
      </section>

      {/* ── Flagship product ── */}
      <section className="section flagship-section" style={productStyle}>
        <div className="section__heading">
          <p className="eyebrow">First live product</p>
          <h2>{product.name} helps you ask better medicine questions.</h2>
          <p>
            {product.short_description || product.summary} It is built for patients and caregivers who want a calmer,
            clearer starting point before making health decisions.
          </p>
        </div>
        <div className="use-case-grid">
          {rxChatHelps.map((item) => {
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
        <div className="flagship-section__actions">
          <a className="button button--product" href={productUrl}>
            Open {product.name} <FiArrowRight aria-hidden="true" />
          </a>
          <Link className="text-link" to={`/products/${product.slug}`}>
            See how it works <FiArrowRight aria-hidden="true" />
          </Link>
        </div>
      </section>

      {/* ── How Fildah is different ── */}
      <section className="section">
        <div className="section__heading">
          <p className="eyebrow">Why Fildah</p>
          <h2>What makes Fildah different.</h2>
        </div>
        <div className="diff-grid">
          {differentiators.map((item, index) => {
            const Icon = diffIcons[index] || FiHeart
            return (
              <article className="diff-card" key={item.title}>
                <Icon aria-hidden="true" />
                <h3>{item.title}</h3>
                <p>{item.summary}</p>
              </article>
            )
          })}
        </div>
      </section>

      {/* ── Products ── */}
      <section className="section section--band">
        <div className="section__heading section__heading--inline">
          <div>
            <p className="eyebrow">Products</p>
            <h2>Focused tools under one careful parent brand.</h2>
          </div>
          <Link className="text-link" to="/products">
            View products <FiArrowRight aria-hidden="true" />
          </Link>
        </div>
        <div className="product-grid">
          {featuredProducts.map((item) => (
            <ProductCard key={item.slug} product={item} />
          ))}
          {featuredProducts.length === 1 && comingSoonCards.map((item) => (
            <article className="product-card product-card--future" key={item.title}>
              <div className="product-card__header">
                <span className="product-card__mark" aria-hidden="true">F</span>
                <span className="status-pill">coming soon</span>
              </div>
              <div>
                <p className="eyebrow">Fildah roadmap</p>
                <h3>{item.title}</h3>
                <p>{item.summary}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* ── Social proof / Testimonials ── */}
      <section className="section">
        <div className="section__heading">
          <p className="eyebrow">What people say</p>
          <h2>Trusted by patients and professionals.</h2>
        </div>
        <div className="testimonial-grid">
          {testimonials.map((item) => (
            <article className="testimonial-card" key={item.name}>
              <p className="testimonial-card__quote">"{item.quote}"</p>
              <div className="testimonial-card__author">
                <span className="testimonial-card__avatar">{item.initials}</span>
                <div>
                  <span className="testimonial-card__name">
                    {item.name}
                    <span className="testimonial-card__role">{item.role}</span>
                  </span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* ── Blog / insights ── */}
      <section className="section">
        <div className="section__heading section__heading--inline">
          <div>
            <p className="eyebrow">Learn first</p>
            <h2>Read before you try.</h2>
            <p>For visitors who want more confidence first, Fildah insights can explain product updates and safer health technology choices.</p>
          </div>
          <Link className="text-link" to="/blog">
            View all <FiArrowRight aria-hidden="true" />
          </Link>
        </div>
        {posts.length ? (
          <div className="content-grid">
            {posts.map((post) => (
              <Link className="content-card" key={post.slug} to={`/blog/${post.slug}`}>
                <FiBookOpen aria-hidden="true" />
                <p className="eyebrow">{post.product?.name || 'Fildah'}</p>
                <h3>{post.title}</h3>
                <p>{post.excerpt}</p>
              </Link>
            ))}
          </div>
        ) : (
          <div className="empty-state empty-state--inline">
            <h3>Education notes are being prepared.</h3>
            <p>Product explainers and medicine-safety notes will appear here. You can still try RxChat now.</p>
            <a className="button button--primary" href={productUrl}>
              Open {product.name} <FiArrowRight aria-hidden="true" />
            </a>
          </div>
        )}
      </section>

      {/* ── Newsletter / early access ── */}
      <section className="newsletter-section">
        <h2>Stay informed on our latest products</h2>
        <p>Get early access to new Fildah tools, product updates, and health technology insights.</p>
        <form className="newsletter-form" onSubmit={handleNewsletter}>
          <input
            type="email"
            placeholder="Enter your email"
            value={newsletterEmail}
            onChange={(e) => setNewsletterEmail(e.target.value)}
            required
            aria-label="Email address for newsletter"
          />
          <button type="submit">Subscribe</button>
        </form>
        {newsletterStatus ? (
          <p className="newsletter-note">{newsletterStatus}</p>
        ) : (
          <p className="newsletter-note">No spam. Unsubscribe anytime.</p>
        )}
      </section>
    </>
  )
}
