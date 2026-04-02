import { useState, useRef, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { HiOutlineArrowLeft } from 'react-icons/hi2'
import './AuthPage.css'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

function AuthPage() {
    const [searchParams] = useSearchParams()
    const email = searchParams.get('email') || ''
    const purpose = searchParams.get('purpose') || 'registration'
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

    // If no email, redirect back
    useEffect(() => {
        if (!email) navigate('/')
    }, [email, navigate])

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
