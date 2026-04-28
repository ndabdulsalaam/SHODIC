import { FiHeart, FiLayers, FiMapPin } from 'react-icons/fi'
import { useApiResource } from '../hooks/useApiResource'

const fallbackAbout = {
  page: {
    title: 'About Fildah',
    summary:
      'Fildah is a parent brand for focused health and technology products that are useful, trustworthy, and built for real-world workflows.',
    body:
      'Fildah builds practical technology products with a health-first sense of responsibility.\n\nRxChat is the first product in the Fildah family. Future products can join the same parent platform while keeping their own product identity, domain, routes, and user experience.',
  },
}

const principles = [
  {
    title: 'Care before scale',
    summary: 'Products should be useful without blurring important safety or support boundaries.',
    icon: FiHeart,
  },
  {
    title: 'Distinct product craft',
    summary: 'Every product gets its own color, interaction model, and audience-specific experience.',
    icon: FiLayers,
  },
  {
    title: 'Local relevance',
    summary: 'Fildah can support Nigeria-first product decisions while remaining clear and globally usable.',
    icon: FiMapPin,
  },
]

export default function AboutPage() {
  const { data } = useApiResource('/pages/about/', fallbackAbout)
  const page = data.page || fallbackAbout.page

  return (
    <section className="page-section">
      <div className="page-hero">
        <p className="eyebrow">About</p>
        <h1>{page.title}</h1>
        <p>{page.summary}</p>
      </div>
      <div className="about-layout">
        <article className="rich-text">
          {page.body?.split('\n').map((paragraph) => (
            paragraph ? <p key={paragraph}>{paragraph}</p> : null
          ))}
        </article>
        <div className="principle-list">
          {principles.map((principle) => {
            const Icon = principle.icon
            return (
              <article className="trust-item" key={principle.title}>
                <Icon aria-hidden="true" />
                <h3>{principle.title}</h3>
                <p>{principle.summary}</p>
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}
