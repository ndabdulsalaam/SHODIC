import { useState, useRef, useEffect } from 'react'
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
    const inputRefs = useRef([])

    // Resend cooldown timer
    useEffect(() => {
        if (resendCooldown <= 0) return
        const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000)
        return () => clearTimeout(timer)
    }, [resendCooldown])

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
            const endpoint = purpose === 'registration'
                ? '/auth/verify-otp/'
                : '/auth/verify-device/'

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

    const handleResend = async () => {
        setResendCooldown(60)
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

    return (
        <div className="auth-page">
            <div className="auth-page__card">
                <div className="auth-page__logo">
                    <div className="auth-page__logo-icon">Rx</div>
                </div>

                <h1 className="auth-page__title">Verify your email</h1>
                <p className="auth-page__subtitle">
                    We sent a 6-digit code to <strong>{email}</strong>
                </p>

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
