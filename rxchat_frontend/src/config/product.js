export const PRODUCT = Object.freeze({
    slug: 'rxchat',
    name: 'RxChat',
    apiNamespace: 'rxchat',
})

export function productApiPath(path = '') {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`
    return `/${PRODUCT.apiNamespace}${normalizedPath}`
}
