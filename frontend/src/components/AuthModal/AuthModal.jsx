import { useState, useMemo, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { HiOutlineXMark } from 'react-icons/hi2'
import './AuthModal.css'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

function AuthModal({ onClose, onLogin, initialMode = 'login' }) {
    const [isLogin, setIsLogin] = useState(initialMode === 'login')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [username, setUsername] = useState('')
    const [firstName, setFirstName] = useState('')
    const [lastName, setLastName] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const [usernameStatus, setUsernameStatus] = useState(null) // null | 'checking' | 'available' | 'taken' | 'error'
    const [usernameError, setUsernameError] = useState('')
    const navigate = useNavigate()

    const passwordsMatch = useMemo(() => {
        if (!confirmPassword) return null
        return password === confirmPassword
    }, [password, confirmPassword])

    const canSubmit = useMemo(() => {
        if (isLogin) return email && password
        return (
            email &&
            password &&
            username &&
            firstName &&
            password.length >= 8 &&
            passwordsMatch === true &&
            usernameStatus === 'available'
        )
    }, [isLogin, email, password, username, firstName, passwordsMatch, usernameStatus])

    // Debounced username availability check
    const checkUsername = useCallback(async (value) => {
        if (!value || value.length < 3) {
            setUsernameStatus(null)
            setUsernameError('')
            return
        }
        setUsernameStatus('checking')
        try {
            const res = await fetch(`${API}/auth/check-username/?username=${encodeURIComponent(value)}`, {
                credentials: 'include',
            })
            const data = await res.json()
            if (data.available) {
                setUsernameStatus('available')
                setUsernameError('')
            } else {
                setUsernameStatus(data.error ? 'error' : 'taken')
                setUsernameError(data.error || 'Username is taken')
            }
        } catch {
            setUsernameStatus('error')
            setUsernameError('Could not check availability')
        }
    }, [])

    useEffect(() => {
        if (isLogin) return
        const timer = setTimeout(() => checkUsername(username), 400)
        return () => clearTimeout(timer)
    }, [username, isLogin, checkUsername])

    const handleForgotPassword = async () => {
        if (!email) {
            setError('Please enter your email address first')
            return
        }
        setLoading(true)
        setError('')
        try {
            const res = await fetch(`${API}/auth/forgot-password/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email }),
            })
            const data = await res.json()
            if (data.otp_required) {
                navigate(`/auth?step=otp&email=${encodeURIComponent(data.email)}&purpose=password_reset`)
                onClose()
            } else {
                setError(data.message || 'Check your email for the reset code')
            }
        } catch {
            setError('Network error. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const endpoint = isLogin ? '/auth/login/' : '/auth/register/'
            const body = isLogin
                ? { identifier: email, password }
                : { email, password, username, first_name: firstName, last_name: lastName }

            const res = await fetch(`${API}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify(body),
            })

            const data = await res.json()

            if (!res.ok) {
                setError(data.error || 'Something went wrong')
                return
            }

            if (data.otp_required) {
                // Navigate to OTP verification page
                const purpose = isLogin ? 'login' : 'registration'
                navigate(`/auth?step=otp&email=${encodeURIComponent(data.email)}&purpose=${purpose}`)
                onClose()
                return
            }

            // Login successful (trusted device)
            if (onLogin) onLogin(data)
            onClose()
        } catch {
            setError('Network error. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleGoogleLogin = () => {
        window.location.href = `${API}/auth/google/login/`
    }

    return (
        <div className="auth-overlay" onClick={onClose}>
            <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
                {/* Close button */}
                <button className="auth-modal__close" onClick={onClose} aria-label="Close">
                    <HiOutlineXMark size={20} />
                </button>

                {/* Logo */}
                <div className="auth-modal__logo">
                    <div className="auth-modal__logo-icon">Rx</div>
                    <div className="auth-modal__logo-text">
                        Rx<span>Chat</span>
                    </div>
                </div>

                <h1 className="auth-modal__title">
                    {isLogin ? 'Welcome back' : 'Create a free account'}
                </h1>

                {error && <div className="auth-modal__error">{error}</div>}

                {/* Form */}
                <form className="auth-modal__form" onSubmit={handleSubmit}>
                    {!isLogin && (
                        <>
                            <div className="auth-modal__field">
                                <label className="auth-modal__label" htmlFor="auth-username">Username</label>
                                <input
                                    id="auth-username"
                                    className={`auth-modal__input ${usernameStatus === 'available'
                                        ? 'auth-modal__input--match'
                                        : usernameStatus === 'taken' || usernameStatus === 'error'
                                            ? 'auth-modal__input--mismatch'
                                            : ''
                                        }`}
                                    type="text"
                                    placeholder="e.g. Nurudeen_Rx"
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value.replace(/\s/g, ''))}
                                    required
                                    minLength={3}
                                />
                                {usernameStatus && (
                                    <div className={`auth-modal__match-indicator auth-modal__match-indicator--${usernameStatus === 'available' ? 'match' : 'mismatch'
                                        }`}>
                                        {usernameStatus === 'checking' && '⏳ Checking...'}
                                        {usernameStatus === 'available' && '✓ Username available'}
                                        {usernameStatus === 'taken' && '✗ Username is taken'}
                                        {usernameStatus === 'error' && `✗ ${usernameError}`}
                                    </div>
                                )}
                            </div>

                            <div className="auth-modal__row">
                                <div className="auth-modal__field">
                                    <label className="auth-modal__label" htmlFor="auth-firstname">First Name</label>
                                    <input
                                        id="auth-firstname"
                                        className="auth-modal__input"
                                        type="text"
                                        placeholder="First name"
                                        value={firstName}
                                        onChange={(e) => setFirstName(e.target.value)}
                                        required
                                    />
                                </div>
                                <div className="auth-modal__field">
                                    <label className="auth-modal__label" htmlFor="auth-lastname">Last Name</label>
                                    <input
                                        id="auth-lastname"
                                        className="auth-modal__input"
                                        type="text"
                                        placeholder="Last name"
                                        value={lastName}
                                        onChange={(e) => setLastName(e.target.value)}
                                    />
                                </div>
                            </div>
                        </>
                    )}

                    <div className="auth-modal__field">
                        <label className="auth-modal__label" htmlFor="auth-email">
                            {isLogin ? 'Email or Username' : 'Email'}
                        </label>
                        <input
                            id="auth-email"
                            className="auth-modal__input"
                            type={isLogin ? 'text' : 'email'}
                            placeholder={isLogin ? 'Email or username' : 'you@example.com'}
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div className="auth-modal__field">
                        <label className="auth-modal__label" htmlFor="auth-password">Password</label>
                        <input
                            id="auth-password"
                            className="auth-modal__input"
                            type={showPassword ? 'text' : 'password'}
                            placeholder="••••••••"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            minLength={8}
                        />
                    </div>

                    {!isLogin && (
                        <div className="auth-modal__field">
                            <label className="auth-modal__label" htmlFor="auth-confirm">Confirm Password</label>
                            <input
                                id="auth-confirm"
                                className={`auth-modal__input ${passwordsMatch === true
                                    ? 'auth-modal__input--match'
                                    : passwordsMatch === false
                                        ? 'auth-modal__input--mismatch'
                                        : ''
                                    }`}
                                type={showPassword ? 'text' : 'password'}
                                placeholder="••••••••"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                required
                            />
                            {passwordsMatch !== null && (
                                <div className={`auth-modal__match-indicator auth-modal__match-indicator--${passwordsMatch ? 'match' : 'mismatch'}`}>
                                    {passwordsMatch ? '✓ Passwords match' : '✗ Passwords do not match'}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Show password toggle */}
                    <div className="auth-modal__show-password">
                        <input
                            type="checkbox"
                            id="show-pass"
                            checked={showPassword}
                            onChange={(e) => setShowPassword(e.target.checked)}
                        />
                        <label htmlFor="show-pass">Show password</label>
                    </div>

                    {isLogin && (
                        <button
                            type="button"
                            className="auth-modal__forgot"
                            onClick={handleForgotPassword}
                        >
                            Forgot password?
                        </button>
                    )}

                    <button
                        type="submit"
                        className="auth-modal__submit"
                        disabled={!canSubmit || loading}
                    >
                        {loading ? 'Please wait...' : isLogin ? 'Sign In' : 'Create Account'}
                    </button>

                    <div className="auth-modal__divider">or</div>

                    <button type="button" className="auth-modal__google" onClick={handleGoogleLogin}>
                        <svg width="18" height="18" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                        </svg>
                        Continue with Google
                    </button>
                </form>

                {/* Toggle login/register */}
                <div className="auth-modal__toggle">
                    {isLogin ? "Don't have an account? " : 'Already have an account? '}
                    <button type="button" onClick={() => { setIsLogin(!isLogin); setError(''); setConfirmPassword(''); setUsernameStatus(null) }}>
                        {isLogin ? 'Register' : 'Sign In'}
                    </button>
                </div>
            </div>
        </div>
    )
}

export default AuthModal
