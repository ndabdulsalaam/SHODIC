import { useState, useMemo, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { HiOutlineXMark } from 'react-icons/hi2'
import './AuthModal.css'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

function AuthModal({ onClose, onLogin, initialMode = 'login' }) {
    const [isLogin, setIsLogin] = useState(initialMode === 'login')
    const [forgotMode, setForgotMode] = useState(false)
    const [forgotEmail, setForgotEmail] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [username, setUsername] = useState('')
    const [firstName, setFirstName] = useState('')
    const [lastName, setLastName] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const [usernameStatus, setUsernameStatus] = useState(null)
    const [usernameError, setUsernameError] = useState('')
    const navigate = useNavigate()

    // Track which fields have been focused (for deferred autoComplete)
    const [focused, setFocused] = useState({})
    const onFieldFocus = (name) => setFocused((prev) => ({ ...prev, [name]: true }))

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

    // Clear ALL fields when switching between login/register
    const handleModeSwitch = () => {
        setIsLogin(!isLogin)
        setEmail('')
        setPassword('')
        setConfirmPassword('')
        setUsername('')
        setFirstName('')
        setLastName('')
        setError('')
        setUsernameStatus(null)
        setUsernameError('')
        setShowPassword(false)
        setFocused({})
    }

    const handleForgotSubmit = async (e) => {
        e.preventDefault()
        if (!forgotEmail) {
            setError('Please enter your email address')
            return
        }
        setLoading(true)
        setError('')
        try {
            const res = await fetch(`${API}/auth/forgot-password/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email: forgotEmail }),
            })
            const data = await res.json()
            if (!res.ok) {
                setError(data.error || 'Something went wrong')
                return
            }
            if (data.otp_required) {
                navigate(`/auth?step=otp&email=${encodeURIComponent(data.email)}&purpose=password_reset`)
                onClose()
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

    // ─── Forgot Password View ───
    if (forgotMode) {
        return (
            <div className="auth-overlay" onClick={onClose}>
                <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
                    <button className="auth-modal__close" onClick={onClose} aria-label="Close">
                        <HiOutlineXMark size={20} />
                    </button>

                    <div className="auth-modal__logo">
                        <span className="auth-modal__logo-text">
                            <span className="auth-modal__logo-r">R</span>
                            <span className="auth-modal__logo-x">x</span>
                            <span className="auth-modal__logo-chat">Chat</span>
                        </span>
                    </div>

                    <h1 className="auth-modal__title">Reset your password</h1>
                    <p className="auth-modal__subtitle">Enter your email and we&apos;ll send you a code to reset your password.</p>

                    {error && <div className="auth-modal__error">{error}</div>}

                    <form className="auth-modal__form" onSubmit={handleForgotSubmit}>
                        <div className="auth-modal__field">
                            <label className="auth-modal__label" htmlFor="forgot-email">Email</label>
                            <input
                                id="forgot-email"
                                className="auth-modal__input"
                                type="email"
                                placeholder="you@example.com"
                                value={forgotEmail}
                                onChange={(e) => setForgotEmail(e.target.value)}
                                autoComplete="email"
                                required
                                autoFocus
                            />
                        </div>

                        <button
                            type="submit"
                            className="auth-modal__submit"
                            disabled={!forgotEmail || loading}
                        >
                            {loading ? 'Sending...' : 'Send Reset Code'}
                        </button>
                    </form>

                    <div className="auth-modal__toggle">
                        <button type="button" onClick={() => { setForgotMode(false); setError('') }}>
                            ← Back to Sign In
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    // ─── Login / Register View ───
    return (
        <div className="auth-overlay" onClick={onClose}>
            <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
                {/* Close button */}
                <button className="auth-modal__close" onClick={onClose} aria-label="Close">
                    <HiOutlineXMark size={20} />
                </button>

                {/* Logo */}
                <div className="auth-modal__logo">
                    <span className="auth-modal__logo-text">
                        <span className="auth-modal__logo-r">R</span>
                        <span className="auth-modal__logo-x">x</span>
                        <span className="auth-modal__logo-chat">Chat</span>
                    </span>
                </div>

                <h1 className="auth-modal__title">
                    {isLogin ? 'Welcome back' : 'Create a free account'}
                </h1>

                {error && <div className="auth-modal__error">{error}</div>}

                {/* Form — autoComplete off prevents eager auto-fill */}
                <form className="auth-modal__form" onSubmit={handleSubmit} autoComplete="off">
                    {!isLogin && (
                        <>
                            <div className="auth-modal__field">
                                <label className="auth-modal__label" htmlFor="auth-username">
                                    Username
                                    {usernameStatus === 'checking' && <span className="auth-modal__match-inline" style={{ opacity: 0.6 }}> ⏳</span>}
                                    {usernameStatus === 'taken' && <span className="auth-modal__match-inline auth-modal__match-inline--no"> ✗ Username taken</span>}
                                    {usernameStatus === 'error' && <span className="auth-modal__match-inline auth-modal__match-inline--no"> ✗ {usernameError}</span>}
                                </label>
                                <div className="auth-modal__input-wrap">
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
                                        autoComplete="off"
                                        required
                                        minLength={3}
                                    />
                                    {usernameStatus === 'available' && (
                                        <span className="auth-modal__input-tick">✓</span>
                                    )}
                                </div>
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
                                        autoComplete={focused.firstName ? 'given-name' : 'off'}
                                        onFocus={() => onFieldFocus('firstName')}
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
                                        autoComplete={focused.lastName ? 'family-name' : 'off'}
                                        onFocus={() => onFieldFocus('lastName')}
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
                            autoComplete={focused.email ? (isLogin ? 'username' : 'email') : 'off'}
                            onFocus={() => onFieldFocus('email')}
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
                            autoComplete={focused.password ? (isLogin ? 'current-password' : 'new-password') : 'off'}
                            onFocus={() => onFieldFocus('password')}
                            required
                            minLength={8}
                        />
                    </div>

                    {!isLogin && (
                        <div className="auth-modal__field">
                            <label className="auth-modal__label" htmlFor="auth-confirm">
                                Confirm Password
                                {passwordsMatch === true && <span className="auth-modal__match-inline auth-modal__match-inline--yes"> ✓ Match</span>}
                                {passwordsMatch === false && <span className="auth-modal__match-inline auth-modal__match-inline--no"> ✗ Mismatch</span>}
                            </label>
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
                                autoComplete="off"
                                required
                            />
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
                            onClick={() => { setForgotMode(true); setError('') }}
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
                    <button type="button" onClick={handleModeSwitch}>
                        {isLogin ? 'Register' : 'Sign In'}
                    </button>
                </div>
            </div>
        </div>
    )
}

export default AuthModal
