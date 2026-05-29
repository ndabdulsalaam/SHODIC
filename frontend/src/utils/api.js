const LOCAL_API_BASE_URL = 'http://localhost:8000'

function isLocalHost(hostname) {
    return ['localhost', '127.0.0.1', '::1'].includes(hostname)
}

export function getApiBaseUrl() {
    const configured = import.meta.env.VITE_API_BASE_URL?.trim()
    if (configured) return configured.replace(/\/$/, '')

    if (typeof window !== 'undefined' && isLocalHost(window.location.hostname)) {
        return LOCAL_API_BASE_URL
    }

    throw new Error('VITE_API_BASE_URL must be set outside localhost.')
}

export const API_BASE_URL = getApiBaseUrl()

export function apiUrl(path) {
    return `${API_BASE_URL}${path}`
}

export class ApiError extends Error {
    constructor(message, { status, payload } = {}) {
        super(message)
        this.name = 'ApiError'
        this.status = status
        this.payload = payload
    }
}

export async function readApiResponse(response) {
    const contentType = response.headers.get('content-type') || ''
    if (contentType.includes('application/json')) {
        return response.json()
    }

    const text = await response.text()
    return text
        ? {
            error: response.status >= 500
                ? 'Server error. Please try again.'
                : text,
        }
        : null
}

export async function apiRequest(path, options = {}) {
    const response = await fetch(apiUrl(path), {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
        ...options,
    })

    const payload = await readApiResponse(response)

    if (!response.ok) {
        throw new ApiError(
            payload?.error || payload?.message || `API error: ${response.status}`,
            { status: response.status, payload },
        )
    }

    return payload
}
