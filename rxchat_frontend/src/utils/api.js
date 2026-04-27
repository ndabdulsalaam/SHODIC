const LOCAL_API_BASE_URL = 'http://localhost:8000'
const PRODUCTION_API_BASE_URL = 'https://api.fildah.com'

function isLocalHost(hostname) {
    return ['localhost', '127.0.0.1', '::1'].includes(hostname)
}

export function getApiBaseUrl() {
    const configured = import.meta.env.VITE_API_BASE_URL?.trim()
    if (configured) return configured.replace(/\/$/, '')

    if (typeof window !== 'undefined' && isLocalHost(window.location.hostname)) {
        return LOCAL_API_BASE_URL
    }

    return PRODUCTION_API_BASE_URL
}

export const API_BASE_URL = getApiBaseUrl()
