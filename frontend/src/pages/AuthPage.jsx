import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { HiOutlineArrowLeft } from 'react-icons/hi2'
import './AuthPage.css'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

function AuthPage() {
    const [searchParams] = useSearchParams()
    const email = searchParams.get('email') || ''
    const purpose = searchParams.get('purpose') || 'registration'
    const step = searchParams.get('step') || 'otp'
    const navigate = useNavigate()

    const [otp, setOtp] = useState(['', '', '', '', '', ''])
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')
    const [loading, setLoading] = useState(false)
    const [resendCooldown, setResendCooldown] = useState(0)
    const [expiryCountdown, setExpiryCountdown] = useState(15 * 60) // 15 minutes
    const inputRefs = useRef([])

    // Password reset flow — after OTP is verified
    const [resetStep, setResetStep] = useState('otp') // 'otp' | 'new_password'
    const [newPassword, setNewPassword] = useState('')
    const [confirmNewPassword, setConfirmNewPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)

    // Google setup state
    const [googleUsername, setGoogleUsername] = useState('')
    const [googlePassword, setGooglePassword] = useState('')
    const [googleConfirmPassword, setGoogleConfirmPassword] = useState('')
    const [usernameStatus, setUsernameStatus] = useState(null)
    const [usernameError, setUsernameError] = useState('')

    const googlePasswordsMatch = useMemo(() => {
        if (!googleConfirmPassword) return null
        return googlePassword === googleConfirmPassword
    }, [googlePassword, googleConfirmPassword])

    // Debounced username check for Google setup
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
        if (step !== 'google_setup') return
        const timer = setTimeout(() => checkUsername(googleUsername), 400)
        return () => clearTimeout(timer)
    }, [googleUsername, step, checkUsername])

    const passwordsMatch = useMemo(() => {
        if (!confirmNewPassword) return null
        return newPassword === confirmNewPassword
    }, [newPassword, confirmNewPassword])

    // Resend cooldown timer
    useEffect(() => {
        if (resendCooldown <= 0) return
        const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000)
        return () => clearTimeout(timer)
    }, [resendCooldown])

    // OTP expiry countdown (15 min)
    useEffect(() => {
        if (expiryCountdown <= 0) return
        const timer = setInterval(() => setExpiryCountdown((prev) => prev - 1), 1000)
        return () => clearInterval(timer)
    }, [expiryCountdown])

    const formatCountdown = (seconds) => {
        const m = Math.floor(seconds / 60)
        const s = seconds % 60
        return `${m}:${s.toString().padStart(2, '0')}`
    }

    // If no email and not google setup, redirect back
    useEffect(() => {
        if (!email && step !== 'google_setup') navigate('/')
    }, [email, step, navigate])

    const handleChange = (index, value) => {
        if (!/^\d*$/.test(value)) return // Only digits
        const newOtp = [...otp]
        newOtp[index] = value.slice(-1)
        setOtp(newOtp)
        setError('')

        // Auto-focus next input
        if (value && index < 5) {
            inputRefs.current[index + 1]?.focus()
        }
    }

    const handleKeyDown = (index, e) => {
        if (e.key === 'Backspace' && !otp[index] && index > 0) {
            inputRefs.current[index - 1]?.focus()
        }
    }

    const handlePaste = (e) => {
        e.preventDefault()
        const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6)
        if (pasted.length === 6) {
            setOtp(pasted.split(''))
            inputRefs.current[5]?.focus()
        }
    }

    const handleVerify = async (e) => {
        e.preventDefault()
        const code = otp.join('')
        if (code.length !== 6) {
            setError('Please enter the 6-digit code')
            return
        }

        setLoading(true)
        setError('')

        try {
            let endpoint
            if (purpose === 'registration') {
                endpoint = '/auth/verify-otp/'
            } else if (purpose === 'password_reset') {
                endpoint = '/auth/verify-reset-otp/'
            } else {
                endpoint = '/auth/verify-device/'
            }

            const res = await fetch(`${API}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, otp: code }),
            })

            const data = await res.json()

            if (!res.ok) {
                setError(data.error || 'Verification failed')
                return
            }

            if (purpose === 'password_reset') {
                // Show new password form
                setResetStep('new_password')
                setSuccess('OTP verified! Set your new password.')
                return
            }

            setSuccess(purpose === 'registration'
                ? 'Account created! Redirecting...'
                : 'Device verified! Redirecting...'
            )

            setTimeout(() => navigate('/'), 1500)
        } catch {
            setError('Network error. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleResetPassword = async (e) => {
        e.preventDefault()
        if (newPassword.length < 8) {
            setError('Password must be at least 8 characters')
            return
        }
        if (newPassword !== confirmNewPassword) {
            setError('Passwords do not match')
            return
        }

        setLoading(true)
        setError('')

        try {
            const res = await fetch(`${API}/auth/reset-password/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password: newPassword }),
            })

            const data = await res.json()

            if (!res.ok) {
                setError(data.error || 'Failed to reset password')
                return
            }

            setSuccess('Password updated! Redirecting to login...')
            setTimeout(() => navigate('/'), 2000)
        } catch {
            setError('Network error. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleResend = async () => {
        setResendCooldown(60)
        setExpiryCountdown(15 * 60) // Reset to 15 minutes
        setError('')

        try {
            const res = await fetch(`${API}/auth/resend-otp/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, purpose }),
            })

            const data = await res.json()

            if (!res.ok) {
                setError(data.error || 'Failed to resend')
                return
            }

            setSuccess('New code sent! Check your email.')
            setTimeout(() => setSuccess(''), 3000)
        } catch {
            setError('Network error. Please try again.')
        }
    }

    const handleGoogleSetup = async (e) => {
        e.preventDefault()
        setError('')
        setSuccess('')

        if (!googleUsername || googleUsername.length < 3) {
            setError('Username must be at least 3 characters')
            return
        }
        if (usernameStatus !== 'available') {
            setError('Please choose an available username')
            return
        }
        if (googlePassword.length < 8) {
            setError('Password must be at least 8 characters')
            return
        }
        if (googlePassword !== googleConfirmPassword) {
            setError('Passwords do not match')
            return
        }

        setLoading(true)
        try {
            const res = await fetch(`${API}/auth/google/complete-setup/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    username: googleUsername,
                    password: googlePassword,
                }),
            })

            const data = await res.json()

            if (!res.ok) {
                setError(data.error || 'Failed to create account')
                return
            }

            setSuccess('Account created! Redirecting...')
            setTimeout(() => navigate('/'), 1500)
        } catch {
            setError('Network error. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    // Google setup form (new Google users pick username + password)
    if (step === 'google_setup') {
        return (
            <div className="auth-page">
                <div className="auth-page__card">
                    <div className="auth-page__logo">
                        <div className="auth-page__logo-icon">Rx</div>
                    </div>

                    <h1 className="auth-page__title">Complete Your Profile</h1>
                    <p className="auth-page__subtitle">
                        You're signing in with Google. Choose a username and set a password for your RxChat account.
                    </p>

                    <form className="auth-page__form" onSubmit={handleGoogleSetup}>
                        <div className="auth-page__input-group">
                            <label htmlFor="google-username">Username</label>
                            <div className="auth-page__input-with-status">
                                <input
                                    id="google-username"
                                    type="text"
                                    value={googleUsername}
                                    onChange={(e) => setGoogleUsername(e.target.value)}
                                    placeholder="Choose a username"
                                    autoFocus
                                />
                                {usernameStatus === 'checking' && (
                                    <span className="auth-page__status auth-page__status--checking">⏳</span>
                                )}
                                {usernameStatus === 'available' && (
                                    <span className="auth-page__status auth-page__status--available">✓</span>
                                )}
                                {(usernameStatus === 'taken' || usernameStatus === 'error') && (
                                    <span className="auth-page__status auth-page__status--taken">✗</span>
                                )}
                            </div>
                            {usernameError && <span className="auth-page__field-error">{usernameError}</span>}
                        </div>

                        <div className="auth-page__input-group">
                            <label htmlFor="google-password">Password</label>
                            <input
                                id="google-password"
                                type={showPassword ? 'text' : 'password'}
                                value={googlePassword}
                                onChange={(e) => setGooglePassword(e.target.value)}
                                placeholder="At least 8 characters"
                                autoComplete="new-password"
                            />
                        </div>

                        <div className="auth-page__input-group">
                            <label htmlFor="google-confirm-password">
                                Confirm Password
                                {googlePasswordsMatch === true && <span className="auth-page__match auth-page__match--yes"> ✓ Match</span>}
                                {googlePasswordsMatch === false && <span className="auth-page__match auth-page__match--no"> ✗ Mismatch</span>}
                            </label>
                            <input
                                id="google-confirm-password"
                                type={showPassword ? 'text' : 'password'}
                                value={googleConfirmPassword}
                                onChange={(e) => setGoogleConfirmPassword(e.target.value)}
                                placeholder="Re-enter password"
                                autoComplete="new-password"
                            />
                        </div>

                        {/* Show password toggle */}
                        <div className="auth-page__show-password">
                            <input
                                type="checkbox"
                                id="google-show-pass"
                                checked={showPassword}
                                onChange={(e) => setShowPassword(e.target.checked)}
                            />
                            <label htmlFor="google-show-pass">Show password</label>
                        </div>

                        {error && <div className="auth-page__error">{error}</div>}
                        {success && <div className="auth-page__success">{success}</div>}

                        <button
                            type="submit"
                            className="auth-page__submit"
                            disabled={loading || usernameStatus !== 'available'}
                        >
                            {loading ? 'Creating account...' : 'Create Account'}
                        </button>
                    </form>
                </div>
            </div>
        )
    }

    // New password form (after OTP verified for password reset)
    if (purpose === 'password_reset' && resetStep === 'new_password') {
        return (
            <div className="auth-page">
                <div className="auth-page__card">
                    <div className="auth-page__logo">
                        <div className="auth-page__logo-icon">Rx</div>
                    </div>

                    <h1 className="auth-page__title">Set New Password</h1>
                    <p className="auth-page__subtitle">
                        Create a new password for <strong>{email}</strong>
                    </p>

                    {error && <div className="auth-page__error">{error}</div>}
                    {success && <div className="auth-page__success">{success}</div>}

                    <form onSubmit={handleResetPassword} className="auth-page__reset-form">
                        <div className="auth-page__field">
                            <label className="auth-page__label" htmlFor="new-pass">New Password</label>
                            <input
                                id="new-pass"
                                className="auth-page__input"
                                type={showPassword ? 'text' : 'password'}
                                placeholder="••••••••"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                required
                                minLength={8}
                                autoFocus
                            />
                        </div>

                        <div className="auth-page__field">
                            <label className="auth-page__label" htmlFor="confirm-new-pass">Confirm Password</label>
                            <input
                                id="confirm-new-pass"
                                className={`auth-page__input ${passwordsMatch === true ? 'auth-page__input--match'
                                    : passwordsMatch === false ? 'auth-page__input--mismatch'
                                        : ''
                                    }`}
                                type={showPassword ? 'text' : 'password'}
                                placeholder="••••••••"
                                value={confirmNewPassword}
                                onChange={(e) => setConfirmNewPassword(e.target.value)}
                                required
                            />
                            {passwordsMatch !== null && (
                                <div className={`auth-page__match ${passwordsMatch ? 'auth-page__match--ok' : 'auth-page__match--no'}`}>
                                    {passwordsMatch ? '✓ Passwords match' : '✗ Passwords do not match'}
                                </div>
                            )}
                        </div>

                        <div className="auth-page__show-password">
                            <input
                                type="checkbox"
                                id="show-reset-pass"
                                checked={showPassword}
                                onChange={(e) => setShowPassword(e.target.checked)}
                            />
                            <label htmlFor="show-reset-pass">Show password</label>
                        </div>

                        <button
                            type="submit"
                            className="auth-page__submit"
                            disabled={loading || !passwordsMatch}
                        >
                            {loading ? 'Updating...' : 'Update Password'}
                        </button>
                    </form>

                    <button className="auth-page__back" onClick={() => navigate('/')}>
                        <HiOutlineArrowLeft size={14} />
                        Back to chat
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="auth-page">
            <div className="auth-page__card">
                <div className="auth-page__logo">
                    <div className="auth-page__logo-icon">Rx</div>
                </div>

                <h1 className="auth-page__title">
                    {purpose === 'password_reset' ? 'Reset your password' : 'Verify your email'}
                </h1>
                <p className="auth-page__subtitle">
                    We sent a 6-digit code to <strong>{email}</strong>
                </p>

                {expiryCountdown > 0 ? (
                    <div className={`auth-page__countdown ${expiryCountdown < 120 ? 'auth-page__countdown--urgent' : ''}`}>
                        Code expires in <strong>{formatCountdown(expiryCountdown)}</strong>
                    </div>
                ) : (
                    <div className="auth-page__countdown auth-page__countdown--expired">
                        Code has expired — please resend
                    </div>
                )}

                {error && <div className="auth-page__error">{error}</div>}
                {success && <div className="auth-page__success">{success}</div>}

                <form onSubmit={handleVerify}>
                    <div className="auth-page__otp-inputs" onPaste={handlePaste}>
                        {otp.map((digit, i) => (
                            <input
                                key={i}
                                ref={(el) => (inputRefs.current[i] = el)}
                                className={`auth-page__otp-input ${digit ? 'auth-page__otp-input--filled' : ''}`}
                                type="text"
                                inputMode="numeric"
                                maxLength={1}
                                value={digit}
                                onChange={(e) => handleChange(i, e.target.value)}
                                onKeyDown={(e) => handleKeyDown(i, e)}
                                autoFocus={i === 0}
                            />
                        ))}
                    </div>

                    <button
                        type="submit"
                        className="auth-page__submit"
                        disabled={loading || otp.join('').length !== 6}
                    >
                        {loading ? 'Verifying...' : 'Verify Code'}
                    </button>
                </form>

                <div className="auth-page__resend">
                    Didn&apos;t receive the code?{' '}
                    <button onClick={handleResend} disabled={resendCooldown > 0}>
                        {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend Code'}
                    </button>
                </div>

                <button className="auth-page__back" onClick={() => navigate('/')}>
                    <HiOutlineArrowLeft size={14} />
                    Back to chat
                </button>
            </div>
        </div>
    )
}

export default AuthPage
