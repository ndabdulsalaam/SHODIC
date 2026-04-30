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
    {
      title: 'Care before scale',
      summary: 'Products are shaped around practical support, clear boundaries, and patient confidence.',
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
  {
    slug: 'privacy',
    title: 'Privacy policy',
    summary: 'How Fildah thinks about privacy, account data, and product support information.',
    body: 'Fildah products should collect only the information needed to provide the service, support the user, and keep the platform reliable.\n\nFormal privacy policy text should be reviewed before launch. Until then, product pages should avoid asking users to share sensitive health details unless the product experience clearly needs that context.',
  },
]

export const fallbackTestimonials = [
  {
    quote: 'RxChat helped me understand my mother\'s prescription in a way I could explain to her. It felt safer than random search results.',
    name: 'Amina K.',
    role: 'Caregiver',
    initials: 'AK',
  },
  {
    quote: 'I used to worry about mixing my medicines. Now I get a clearer starting point before speaking with my pharmacist.',
    name: 'David O.',
    role: 'Patient',
    initials: 'DO',
  },
  {
    quote: 'As a community pharmacist, I appreciate tools that encourage patients to ask better questions instead of self-diagnosing.',
    name: 'Dr. Ngozi E.',
    role: 'Pharmacist',
    initials: 'NE',
  },
]

export const fallbackDifferentiators = [
  {
    title: 'Designed by practitioners',
    summary: 'Fildah products are shaped by healthcare professionals who understand clinical workflows and patient realities.',
  },
  {
    title: 'Built for African healthcare contexts',
    summary: 'Products reflect local pharmacy practices, medicine availability, and communication styles found across Nigeria and beyond.',
  },
  {
    title: 'Focused on real outcomes',
    summary: 'Every feature exists to improve a specific health decision, not to chase engagement metrics.',
  },
]
