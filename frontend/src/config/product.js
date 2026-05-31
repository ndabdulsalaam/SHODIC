export const PRODUCT = Object.freeze({
    slug: 'shodic',
    name: 'SHODIC',
    subtitle: 'Hospital medication assistant',
    documentTitle: 'SHODIC — Hospital medication assistant',
    description: 'SHODIC is a hospital medication assistant for medication safety, drug interactions, and patient-centered medicine information.',
    apiNamespace: 'shodic',
})

export function productApiPath(path = '') {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`
    return `/${PRODUCT.apiNamespace}${normalizedPath}`
}
