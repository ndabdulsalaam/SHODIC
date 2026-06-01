export const PRODUCT = Object.freeze({
    slug: 'shodic',
    name: 'SHO-DIC',
    subtitle: 'Hospital medication assistant',
    documentTitle: 'SHO-DIC — Hospital medication assistant',
    description: 'SHO-DIC is a hospital medication assistant for medication safety, drug interactions, and patient-centered medicine information.',
    apiNamespace: 'shodic',
})

export function productApiPath(path = '') {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`
    return `/${PRODUCT.apiNamespace}${normalizedPath}`
}
