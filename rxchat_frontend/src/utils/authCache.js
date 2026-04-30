const AUTH_USER_CACHE_KEY = 'rxchat_auth_user'

function getStorage() {
    if (typeof window === 'undefined') return null
    return window.localStorage || null
}

export function readCachedAuthUser() {
    try {
        const storage = getStorage()
        const cached = storage?.getItem(AUTH_USER_CACHE_KEY)
            || (typeof window !== 'undefined' ? window.sessionStorage?.getItem(AUTH_USER_CACHE_KEY) : null)
        if (cached && storage && !storage.getItem(AUTH_USER_CACHE_KEY)) {
            storage.setItem(AUTH_USER_CACHE_KEY, cached)
        }
        return cached ? JSON.parse(cached) : null
    } catch {
        return null
    }
}

export function cacheAuthUser(user) {
    try {
        const storage = getStorage()
        if (!storage) return

        if (user?.id) {
            storage.setItem(AUTH_USER_CACHE_KEY, JSON.stringify(user))
            return
        }

        storage.removeItem(AUTH_USER_CACHE_KEY)
        if (typeof window !== 'undefined') {
            window.sessionStorage?.removeItem(AUTH_USER_CACHE_KEY)
        }
    } catch { /* storage may be unavailable */ }
}
