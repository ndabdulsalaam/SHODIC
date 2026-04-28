export const fallbackProduct = {
  slug: 'rxchat',
  name: 'RxChat',
  tagline: 'Medication answers and pharmacy guidance with practical safety boundaries.',
  summary: 'An AI pharmacy assistant for medication questions, drug information, and safer health decisions.',
  short_description: 'An AI pharmacy assistant for medication questions, drug information, and safer health decisions.',
  long_description:
    'RxChat is the first product under Fildah. It helps people ask clearer questions about medicines, possible interactions, OTC choices, and healthcare next steps while keeping clinical safety guidance visible.',
  category: 'Health AI',
  status: 'active',
  frontend_url: 'https://rxchat.fildah.com',
  marketing_path: '/products/rxchat',
  api_namespace: '/rxchat/',
  primary_color: '#5CB832',
  secondary_color: '#1A6BC4',
  is_featured: true,
}

export const fallbackHome = {
  brand: {
    name: 'Fildah',
    tagline: 'Health technology products built with care, trust, and practical support.',
    description:
      'Fildah is the parent brand for focused health and technology products, starting with RxChat.',
  },
  primary_product: fallbackProduct,
  featured_products: [fallbackProduct],
  recent_posts: [],
  trust_points: [
    {
      title: 'Privacy-aware by default',
      summary: 'Account, support, and product access flows are designed around clear user control.',
    },
    {
      title: 'Healthcare safety posture',
      summary: 'Health products carry careful boundaries, escalation guidance, and source-aware design.',
    },
    {
      title: 'Built for local realities',
      summary: 'Fildah products can reflect Nigeria-first workflows while remaining globally usable.',
    },
  ],
}

export const fallbackDocs = [
  {
    slug: 'overview',
    title: 'Fildah overview',
    summary: 'How the parent platform, product sites, and shared API fit together.',
    body: 'Fildah is the central brand and product directory. Product experiences can run on their own subdomains while shared backend services remain available.',
  },
  {
    slug: 'rxchat',
    title: 'RxChat',
    summary: 'Product notes for the RxChat pharmacy assistant.',
    body: 'RxChat lives at rxchat.fildah.com and uses the /rxchat/ API namespace.',
  },
]
