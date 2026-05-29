export const PRODUCT = Object.freeze({
    slug: 'shodic',
    name: 'SHODIC',
    apiNamespace: 'shodic',
})

export function productApiPath(path = '') {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`
    return `/${PRODUCT.apiNamespace}${normalizedPath}`
}
