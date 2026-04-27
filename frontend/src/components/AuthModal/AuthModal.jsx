import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { HiOutlineXMark } from 'react-icons/hi2'
import './AuthModal.css'

const API = import.meta.env.VITE_API_BASE_URL || '/api'

function AuthModal({ onClose, onLogin, initialMode = 'login' }) {
    const [isLogin, setIsLogin] = useState(initialMode === 'login')
    const [forgotMode, setForgotMode] = useState(false)
    const [forgotEmail, setForgotEmail] = useState('')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    // Track which fields have been focused (for deferred autoComplete)
    const [focused, setFocused] = useState({})
    const onFieldFocus = (name) => setFocused((prev) => ({ ...prev, [name]: true }))

    const canSubmit = useMemo(() => {
        if (isLogin) return email && password
        return email // Registration = email only
    }, [isLogin, email, password])

    // Clear ALL fields when switching between login/register
    const handleModeSwitch = () => {
        setIsLogin(!isLogin)
        setEmail('')
        setPassword('')
        setError('')
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
                ? { email, password }
                : { email }

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

                {!isLogin && (
                    <p className="auth-modal__subtitle">
                        Enter your email to get started. You&apos;ll verify it with a code.
                    </p>
                )}

                {error && <div className="auth-modal__error">{error}</div>}

                {/* Form */}
                <form className="auth-modal__form" onSubmit={handleSubmit} autoComplete="off">
                    <div className="auth-modal__field">
                        <label className="auth-modal__label" htmlFor="auth-email">Email</label>
                        <input
                            id="auth-email"
                            className="auth-modal__input"
                            type="email"
                            placeholder="you@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            autoComplete={focused.email ? 'email' : 'off'}
                            onFocus={() => onFieldFocus('email')}
                            required
                            autoFocus
                        />
                    </div>

                    {isLogin && (
                        <>
                            <div className="auth-modal__field">
                                <label className="auth-modal__label" htmlFor="auth-password">Password</label>
                                <input
                                    id="auth-password"
                                    className="auth-modal__input"
                                    type={showPassword ? 'text' : 'password'}
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    autoComplete={focused.password ? 'current-password' : 'off'}
                                    onFocus={() => onFieldFocus('password')}
                                    required
                                    minLength={8}
                                />
                            </div>

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

                            <button
                                type="button"
                                className="auth-modal__forgot"
                                onClick={() => { setForgotMode(true); setError('') }}
                            >
                                Forgot password?
                            </button>
                        </>
                    )}

                    <button
                        type="submit"
                        className="auth-modal__submit"
                        disabled={!canSubmit || loading}
                    >
                        {loading ? 'Please wait...' : isLogin ? 'Sign In' : 'Continue with Email'}
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
