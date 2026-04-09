import { useState, useRef, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { HiOutlineArrowLeft } from 'react-icons/hi2'
import './AuthPage.css'

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

const ROLE_OPTIONS = [
    { value: '', label: 'Select your role' },
    { value: 'patient', label: 'Patient' },
    { value: 'pharmacist', label: 'Pharmacist' },
    { value: 'physician', label: 'Physician' },
    { value: 'nurse', label: 'Nurse' },
    { value: 'other_health_professional', label: 'Other Health Professional' },
]

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

    // Profile setup state (after OTP verified for registration)
    const [preferredName, setPreferredName] = useState('')
    const [firstName, setFirstName] = useState('')
    const [lastName, setLastName] = useState('')
    const [setupRole, setSetupRole] = useState('')
    const [setupPassword, setSetupPassword] = useState('')
    const [setupConfirmPassword, setSetupConfirmPassword] = useState('')

    // Google setup state
    const [googlePreferredName, setGooglePreferredName] = useState('')
    const [googleFirstName, setGoogleFirstName] = useState('')
    const [googleLastName, setGoogleLastName] = useState('')
    const [googlePassword, setGooglePassword] = useState('')
    const [googleConfirmPassword, setGoogleConfirmPassword] = useState('')
    const [googleRole, setGoogleRole] = useState('')

    const googlePasswordsMatch = useMemo(() => {
        if (!googleConfirmPassword) return null
        return googlePassword === googleConfirmPassword
    }, [googlePassword, googleConfirmPassword])

    const setupPasswordsMatch = useMemo(() => {
        if (!setupConfirmPassword) return null
        return setupPassword === setupConfirmPassword
    }, [setupPassword, setupConfirmPassword])

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

    // If no email and not google/profile setup, redirect back
    useEffect(() => {
        if (!email && step !== 'google_setup' && step !== 'profile_setup') navigate('/')
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

            if (purpose === 'registration' && data.setup_required) {
                // Redirect to profile setup
                navigate(`/auth?step=profile_setup&email=${encodeURIComponent(email)}`)
                return
            }

            setSuccess('Device verified! Redirecting...')
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

    // ─── Profile Setup (after OTP verified for registration) ───
    const handleProfileSetup = async (e) => {
        e.preventDefault()
        setError('')
        setSuccess('')

        if (!preferredName) {
            setError('Please tell us what Rx should call you')
            return
        }
        if (!firstName) {
            setError('First name is required')
            return
        }
        if (!setupRole) {
            setError('Please select your role')
            return
        }
        if (setupPassword.length < 8) {
            setError('Password must be at least 8 characters')
            return
        }
        if (setupPassword !== setupConfirmPassword) {
            setError('Passwords do not match')
            return
        }

        setLoading(true)
        try {
            const res = await fetch(`${API}/auth/complete-setup/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    preferred_name: preferredName,
                    first_name: firstName,
                    last_name: lastName,
                    role: setupRole,
                    password: setupPassword,
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

    // ─── Google Setup ───
    const handleGoogleSetup = async (e) => {
        e.preventDefault()
        setError('')
        setSuccess('')

        if (!googlePreferredName) {
            setError('Please tell us what Rx should call you')
            return
        }
        if (!googleFirstName) {
            setError('First name is required')
            return
        }
        if (!googleRole) {
            setError('Please select your role')
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
                    preferred_name: googlePreferredName,
                    first_name: googleFirstName,
                    last_name: googleLastName,
                    role: googleRole,
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

    // ─── Profile Setup Form (registration step 3) ───
    if (step === 'profile_setup') {
        return (
            <div className="auth-page">
                <div className="auth-page__card">
                    <div className="auth-page__logo">
                        <span className="auth-page__logo-text">
                            <span className="auth-page__logo-r">R</span>
                            <span className="auth-page__logo-x">x</span>
                            <span className="auth-page__logo-chat">Chat</span>
                        </span>
                    </div>

                    <h1 className="auth-page__title">Complete Your Profile</h1>
                    <p className="auth-page__subtitle">
                        Email verified! Set up your profile for <strong>{email}</strong>
                    </p>

                    <form className="auth-page__form" onSubmit={handleProfileSetup}>
                        <div className="auth-page__input-group">
                            <label htmlFor="setup-preferred-name">What should Rx call you?</label>
                            <input
                                id="setup-preferred-name"
                                type="text"
                                value={preferredName}
                                onChange={(e) => setPreferredName(e.target.value)}
                                placeholder="e.g. Nurudeen"
                                autoFocus
                                required
                            />
                        </div>

                        <div className="auth-page__row">
                            <div className="auth-page__input-group">
                                <label htmlFor="setup-first-name">First Name</label>
                                <input
                                    id="setup-first-name"
                                    type="text"
                                    value={firstName}
                                    onChange={(e) => setFirstName(e.target.value)}
                                    placeholder="First name"
                                    required
                                />
                            </div>
                            <div className="auth-page__input-group">
                                <label htmlFor="setup-last-name">Last Name</label>
                                <input
                                    id="setup-last-name"
                                    type="text"
                                    value={lastName}
                                    onChange={(e) => setLastName(e.target.value)}
                                    placeholder="Last name"
                                />
                            </div>
                        </div>

                        <div className="auth-page__input-group">
                            <label htmlFor="setup-role">Role</label>
                            <select
                                id="setup-role"
                                className="auth-page__select"
                                value={setupRole}
                                onChange={(e) => setSetupRole(e.target.value)}
                                required
                            >
                                {ROLE_OPTIONS.map((opt) => (
                                    <option key={opt.value} value={opt.value} disabled={!opt.value}>
                                        {opt.label}
                                    </option>
                                ))}
                            </select>
                        </div>

                        <div className="auth-page__input-group">
                            <label htmlFor="setup-password">Password</label>
                            <input
                                id="setup-password"
                                type={showPassword ? 'text' : 'password'}
                                value={setupPassword}
                                onChange={(e) => setSetupPassword(e.target.value)}
                                placeholder="At least 8 characters"
                                autoComplete="new-password"
                                required
                            />
                        </div>

                        <div className="auth-page__input-group">
                            <label htmlFor="setup-confirm-password">
                                Confirm Password
                                {setupPasswordsMatch === true && <span className="auth-page__match auth-page__match--yes"> ✓ Match</span>}
                                {setupPasswordsMatch === false && <span className="auth-page__match auth-page__match--no"> ✗ Mismatch</span>}
                            </label>
                            <input
                                id="setup-confirm-password"
                                type={showPassword ? 'text' : 'password'}
                                value={setupConfirmPassword}
                                onChange={(e) => setSetupConfirmPassword(e.target.value)}
                                placeholder="Re-enter password"
                                autoComplete="new-password"
                                required
                            />
                        </div>

                        {/* Show password toggle */}
                        <div className="auth-page__show-password">
                            <input
                                type="checkbox"
                                id="setup-show-pass"
                                checked={showPassword}
                                onChange={(e) => setShowPassword(e.target.checked)}
                            />
                            <label htmlFor="setup-show-pass">Show password</label>
                        </div>

                        {error && <div className="auth-page__error">{error}</div>}
                        {success && <div className="auth-page__success">{success}</div>}

                        <button
                            type="submit"
                            className="auth-page__submit"
                            disabled={loading || !setupRole || !preferredName || !firstName}
                        >
                            {loading ? 'Creating account...' : 'Create Account'}
                        </button>
                    </form>
                </div>
            </div>
        )
    }

    // ─── Google Setup Form ───
    if (step === 'google_setup') {
        return (
            <div className="auth-page">
                <div className="auth-page__card">
                    <div className="auth-page__logo">
                        <span className="auth-page__logo-text">
                            <span className="auth-page__logo-r">R</span>
                            <span className="auth-page__logo-x">x</span>
                            <span className="auth-page__logo-chat">Chat</span>
                        </span>
                    </div>

                    <h1 className="auth-page__title">Complete Your Profile</h1>
                    <p className="auth-page__subtitle">
                        You&apos;re signing in with Google. Set up your RxChat profile.
                    </p>

                    <form className="auth-page__form" onSubmit={handleGoogleSetup}>
                        <div className="auth-page__input-group">
                            <label htmlFor="google-preferred-name">What should Rx call you?</label>
                            <input
                                id="google-preferred-name"
                                type="text"
                                value={googlePreferredName}
                                onChange={(e) => setGooglePreferredName(e.target.value)}
                                placeholder="e.g. Nurudeen"
                                autoFocus
                                required
                            />
                        </div>

                        <div className="auth-page__row">
                            <div className="auth-page__input-group">
                                <label htmlFor="google-first-name">First Name</label>
                                <input
                                    id="google-first-name"
                                    type="text"
                                    value={googleFirstName}
                                    onChange={(e) => setGoogleFirstName(e.target.value)}
                                    placeholder="First name"
                                    required
                                />
                            </div>
                            <div className="auth-page__input-group">
                                <label htmlFor="google-last-name">Last Name</label>
                                <input
                                    id="google-last-name"
                                    type="text"
                                    value={googleLastName}
                                    onChange={(e) => setGoogleLastName(e.target.value)}
                                    placeholder="Last name"
                                />
                            </div>
                        </div>

                        <div className="auth-page__input-group">
                            <label htmlFor="google-role">Role</label>
                            <select
                                id="google-role"
                                className="auth-page__select"
                                value={googleRole}
                                onChange={(e) => setGoogleRole(e.target.value)}
                                required
                            >
                                {ROLE_OPTIONS.map((opt) => (
                                    <option key={opt.value} value={opt.value} disabled={!opt.value}>
                                        {opt.label}
                                    </option>
                                ))}
                            </select>
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
                            disabled={loading || !googleRole || !googlePreferredName || !googleFirstName}
                        >
                            {loading ? 'Creating account...' : 'Create Account'}
                        </button>
                    </form>
                </div>
            </div>
        )
    }

    // ─── New Password Form (after OTP verified for password reset) ───
    if (purpose === 'password_reset' && resetStep === 'new_password') {
        return (
            <div className="auth-page">
                <div className="auth-page__card">
                    <div className="auth-page__logo">
                        <span className="auth-page__logo-text">
                            <span className="auth-page__logo-r">R</span>
                            <span className="auth-page__logo-x">x</span>
                            <span className="auth-page__logo-chat">Chat</span>
                        </span>
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

    // ─── OTP Verification ───
    return (
        <div className="auth-page">
            <div className="auth-page__card">
                <div className="auth-page__logo">
                    <span className="auth-page__logo-text">
                        <span className="auth-page__logo-r">R</span>
                        <span className="auth-page__logo-x">x</span>
                        <span className="auth-page__logo-chat">Chat</span>
                    </span>
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
