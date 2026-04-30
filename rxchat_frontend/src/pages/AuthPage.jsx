import { useState, useRef, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { HiOutlineArrowLeft } from 'react-icons/hi2'
import { apiRequest } from '../utils/api'
import { cacheAuthUser } from '../utils/authCache'
import './AuthPage.css'

const ROLE_OPTIONS = [
    { value: '', label: 'Select your role' },
    { value: 'patient', label: 'Patient' },
    { value: 'pharmacist', label: 'Pharmacist' },
    { value: 'physician', label: 'Physician' },
    { value: 'nurse', label: 'Nurse' },
    { value: 'other_health_professional', label: 'Other Health Professional' },
]

const GENDER_OPTIONS = [
    { value: '', label: 'Select gender' },
    { value: 'male', label: 'Male' },
    { value: 'female', label: 'Female' },
]

const AGE_RANGE_OPTIONS = [
    { value: '', label: 'Select age range' },
    { value: 'under_18', label: 'Under 18' },
    { value: '18_24', label: '18-24' },
    { value: '25_34', label: '25-34' },
    { value: '35_44', label: '35-44' },
    { value: '45_54', label: '45-54' },
    { value: '55_64', label: '55-64' },
    { value: '65_plus', label: '65+' },
]

const SETUP_STEPS = [1, 2, 3]

const SETUP_STEP_TITLES = {
    1: 'Tell us about yourself',
    2: 'Your professional role',
    3: 'Secure your account',
}

const EMPTY_OTP = ['', '', '', '', '', '']

function normalizeNigeriaPhone(value) {
    const digits = value.replace(/\D/g, '')
    const withoutCountryCode = digits.replace(/^234/, '').replace(/^0/, '')
    return withoutCountryCode ? `+234${withoutCountryCode}` : ''
}

function nameFromEmail(value = '') {
    const localPart = value.split('@')[0] || ''
    const firstToken = localPart.split(/[._-]/).find(Boolean) || localPart
    return firstToken ? firstToken.charAt(0).toUpperCase() + firstToken.slice(1) : 'User'
}

function suggestPreferredName(role, firstName, lastName, gender, profession = '') {
    const first = firstName.trim()
    const last = lastName.trim()
    const professionalTitle = profession.trim().replace(/\s+/g, ' ')
    const professionalName = last || first

    if (!role) return ''

    if (role === 'pharmacist') return professionalName ? `Pharm. ${professionalName}` : ''
    if (role === 'physician') return professionalName ? `Dr. ${professionalName}` : ''
    if (role === 'nurse') return professionalName ? `Nr. ${professionalName}` : ''
    if (role === 'other_health_professional') {
        if (professionalTitle && professionalName) return `${professionalTitle} ${professionalName}`
        return professionalName
    }
    if (role === 'patient') {
        if (!first) return ''
        if (gender === 'male') return `Mr. ${first}`
        if (gender === 'female') return `Ms. ${first}`
        return first
    }

    return first
}

function SetupProgress({ step }) {
    return (
        <div className="auth-page__step-indicator" aria-label={`Step ${step} of 3`}>
            {SETUP_STEPS.map((item, index) => (
                <div
                    key={item}
                    className={`auth-page__step-item ${item < step ? 'auth-page__step-item--done' : ''} ${item === step ? 'auth-page__step-item--active' : ''}`}
                >
                    {index > 0 && <span className="auth-page__step-line" />}
                    <span className="auth-page__step-circle">{item}</span>
                </div>
            ))}
        </div>
    )
}

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
    const [expiryCountdown, setExpiryCountdown] = useState(5 * 60) // 5 minutes
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
    const [setupStep, setSetupStep] = useState(1)
    const [gender, setGender] = useState('')
    const [ageRange, setAgeRange] = useState('')
    const [phoneNumber, setPhoneNumber] = useState('')
    const [setupRole, setSetupRole] = useState('')
    const [setupProfession, setSetupProfession] = useState('')
    const [setupPassword, setSetupPassword] = useState('')
    const [setupConfirmPassword, setSetupConfirmPassword] = useState('')

    // Google setup state
    const [googlePreferredName, setGooglePreferredName] = useState('')
    const [googleFirstName, setGoogleFirstName] = useState('')
    const [googleLastName, setGoogleLastName] = useState('')
    const [googlePendingEmail, setGooglePendingEmail] = useState('')
    const [googleSetupStep, setGoogleSetupStep] = useState(1)
    const [googleGender, setGoogleGender] = useState('')
    const [googleAgeRange, setGoogleAgeRange] = useState('')
    const [googlePhoneNumber, setGooglePhoneNumber] = useState('')
    const [googlePassword, setGooglePassword] = useState('')
    const [googleConfirmPassword, setGoogleConfirmPassword] = useState('')
    const [googleRole, setGoogleRole] = useState('')
    const [googleProfession, setGoogleProfession] = useState('')

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

    // OTP expiry countdown (5 min)
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

    const otpTitle = purpose === 'password_reset'
        ? 'Reset your password'
        : purpose === 'login'
            ? 'Login verification'
            : 'Verify your email'
    const otpIntro = purpose === 'login'
        ? 'We sent a 6-digit login code to'
        : 'We sent a 6-digit code to'

    const resetOtpInputs = () => {
        setOtp([...EMPTY_OTP])
        setTimeout(() => inputRefs.current[0]?.focus(), 0)
    }

    // If no email and not google/profile setup, redirect back
    useEffect(() => {
        if (!email && step !== 'google_setup' && step !== 'profile_setup') navigate('/')
    }, [email, step, navigate])

    useEffect(() => {
        if (step !== 'google_setup') return

        let isCurrent = true
        const loadPendingGoogleProfile = async () => {
            try {
                const data = await apiRequest('/auth/google/pending-profile/')
                if (!isCurrent) return

                const nextEmail = data.email || ''
                const nextFirst = (data.first_name || '').trim() || nameFromEmail(nextEmail)
                const nextLast = (data.last_name || '').trim()
                setGooglePendingEmail(nextEmail)
                setGoogleFirstName((current) => current || nextFirst)
                setGoogleLastName((current) => current || nextLast)
                setGooglePreferredName((current) => current || nextFirst)
            } catch (error) {
                if (isCurrent) setError(error.message || 'Unable to load your Google profile. Please try again.')
            }
        }

        loadPendingGoogleProfile()
        return () => {
            isCurrent = false
        }
    }, [step])

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

            const data = await apiRequest(endpoint, {
                method: 'POST',
                body: JSON.stringify({ email, otp: code }),
            })

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

            cacheAuthUser(data)
            navigate('/', { replace: true })
        } catch (error) {
            setError(error.message || 'Unable to reach the server. Please try again.')
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
            await apiRequest('/auth/reset-password/', {
                method: 'POST',
                body: JSON.stringify({ email, password: newPassword }),
            })

            setSuccess('Password updated! Redirecting to login...')
            setTimeout(() => navigate('/'), 2000)
        } catch (error) {
            setError(error.message || 'Network error. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const handleResend = async () => {
        setError('')

        try {
            const data = await apiRequest('/auth/resend-otp/', {
                method: 'POST',
                body: JSON.stringify({ email, purpose }),
            })

            resetOtpInputs()
            setResendCooldown(60)
            setExpiryCountdown(5 * 60) // Reset to 5 minutes
            setSuccess(data.message || 'New code sent! Check your email.')
            setTimeout(() => setSuccess(''), 6000)
        } catch (error) {
            setError(error.message || 'Unable to reach the server. Please try again.')
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
        if (setupRole === 'other_health_professional' && !setupProfession.trim()) {
            setError('Please enter your profession')
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
            const data = await apiRequest('/auth/complete-setup/', {
                method: 'POST',
                body: JSON.stringify({
                    preferred_name: preferredName,
                    first_name: firstName,
                    last_name: lastName,
                    gender,
                    age_range: ageRange,
                    phone_number: normalizeNigeriaPhone(phoneNumber),
                    role: setupRole,
                    password: setupPassword,
                }),
            })

            setSuccess('Account created! Redirecting...')
            cacheAuthUser(data)
            navigate('/', { replace: true })
        } catch (error) {
            setError(error.message || 'Network error. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    // ─── Google Setup ───
    const handleGoogleSetup = async (e) => {
        e.preventDefault()
        setError('')
        setSuccess('')

        const effectiveFirstName = googleFirstName.trim() || nameFromEmail(googlePendingEmail)
        const effectiveLastName = googleLastName.trim()
        const effectivePreferredName = googlePreferredName.trim() || effectiveFirstName

        if (!effectivePreferredName) {
            setError('Please tell us what Rx should call you')
            return
        }
        if (!effectiveFirstName) {
            setError('First name is required')
            return
        }
        if (!googleRole) {
            setError('Please select your role')
            return
        }
        if (googleRole === 'other_health_professional' && !googleProfession.trim()) {
            setError('Please enter your profession')
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
            const data = await apiRequest('/auth/google/complete-setup/', {
                method: 'POST',
                body: JSON.stringify({
                    preferred_name: effectivePreferredName,
                    first_name: effectiveFirstName,
                    last_name: effectiveLastName,
                    gender: googleGender,
                    age_range: googleAgeRange,
                    phone_number: normalizeNigeriaPhone(googlePhoneNumber),
                    role: googleRole,
                    password: googlePassword,
                }),
            })

            setSuccess('Account created! Redirecting...')
            cacheAuthUser(data)
            navigate('/', { replace: true })
        } catch (error) {
            setError(error.message || 'Network error. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const moveSetupStep = (setStep, nextStep) => {
        setError('')
        setSuccess('')
        setStep(nextStep)
    }

    const renderSetupWizard = ({
        variant,
        subtitle,
        currentStep,
        setCurrentStep,
        first,
        setFirst,
        last,
        setLast,
        selectedGender,
        setSelectedGender,
        selectedAgeRange,
        setSelectedAgeRange,
        phone,
        setPhone,
        role,
        setRole,
        profession,
        setProfession,
        preferred,
        setPreferred,
        password,
        setPassword,
        confirmPassword,
        setConfirmPassword,
        passwordMatch,
        onSubmit,
        showPasswordId,
        compactIdentity = false,
    }) => {
        const canContinueStep1 = Boolean((compactIdentity || first.trim()) && selectedGender && selectedAgeRange)
        const needsProfession = role === 'other_health_professional'
        const canContinueStep2 = Boolean(role && preferred.trim() && (!needsProfession || profession.trim()))
        const preferredNameHint = role === 'patient'
            ? 'Suggestion based on your role and gender. You can use anything you prefer.'
            : needsProfession
                ? 'Suggestion based on your profession and name. You can use anything you prefer.'
                : 'Suggestion based on your role. You can use anything you prefer.'

        const handleRoleChange = (value) => {
            setRole(value)
            if (value !== 'other_health_professional') setProfession('')
            setPreferred(suggestPreferredName(value, first, last, selectedGender, profession))
        }

        const handleProfessionChange = (value) => {
            setProfession(value)
            setPreferred(suggestPreferredName(role, first, last, selectedGender, value))
        }

        const handleWizardSubmit = (e) => {
            if (currentStep === 1) {
                e.preventDefault()
                if (canContinueStep1) moveSetupStep(setCurrentStep, 2)
                return
            }

            if (currentStep === 2) {
                e.preventDefault()
                if (canContinueStep2) moveSetupStep(setCurrentStep, 3)
                return
            }

            onSubmit(e)
        }

        const statusMessages = (
            <>
                {error && <div className="auth-page__error">{error}</div>}
                {success && <div className="auth-page__success">{success}</div>}
            </>
        )

        return (
            <div className="auth-page">
                <div className="auth-page__card auth-page__card--wizard">
                    <div className="auth-page__logo">
                        <span className="auth-page__logo-text">
                            <span className="auth-page__logo-r">R</span>
                            <span className="auth-page__logo-x">x</span>
                            <span className="auth-page__logo-chat">Chat</span>
                        </span>
                    </div>

                    <SetupProgress step={currentStep} />

                    <h1 className="auth-page__title">{SETUP_STEP_TITLES[currentStep]}</h1>
                    {subtitle && <p className="auth-page__subtitle">{subtitle}</p>}

                    <form className="auth-page__form auth-page__form--wizard" onSubmit={handleWizardSubmit}>
                        <div key={`${variant}-${currentStep}`} className="auth-page__wizard-step">
                            {currentStep === 1 && (
                                <>
                                    {!compactIdentity && (
                                        <div className="auth-page__row">
                                            <div className="auth-page__input-group">
                                                <label htmlFor={`${variant}-first-name`}>First Name</label>
                                                <input
                                                    id={`${variant}-first-name`}
                                                    type="text"
                                                    value={first}
                                                    onChange={(e) => setFirst(e.target.value)}
                                                    placeholder="First name"
                                                    autoFocus
                                                    required
                                                />
                                            </div>
                                            <div className="auth-page__input-group">
                                                <label htmlFor={`${variant}-last-name`}>Last Name</label>
                                                <input
                                                    id={`${variant}-last-name`}
                                                    type="text"
                                                    value={last}
                                                    onChange={(e) => setLast(e.target.value)}
                                                    placeholder="Last name"
                                                />
                                            </div>
                                        </div>
                                    )}

                                    <div className="auth-page__row">
                                        <div className="auth-page__input-group">
                                            <label htmlFor={`${variant}-gender`}>Gender</label>
                                            <select
                                                id={`${variant}-gender`}
                                                className="auth-page__select"
                                                value={selectedGender}
                                                onChange={(e) => setSelectedGender(e.target.value)}
                                                autoFocus={compactIdentity}
                                                required
                                            >
                                                {GENDER_OPTIONS.map((opt) => (
                                                    <option key={opt.value} value={opt.value} disabled={!opt.value}>
                                                        {opt.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="auth-page__input-group">
                                            <label htmlFor={`${variant}-age-range`}>Age Range</label>
                                            <select
                                                id={`${variant}-age-range`}
                                                className="auth-page__select"
                                                value={selectedAgeRange}
                                                onChange={(e) => setSelectedAgeRange(e.target.value)}
                                                required
                                            >
                                                {AGE_RANGE_OPTIONS.map((opt) => (
                                                    <option key={opt.value} value={opt.value} disabled={!opt.value}>
                                                        {opt.label}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    </div>

                                    <div className="auth-page__input-group">
                                        <label htmlFor={`${variant}-phone`}>Phone Number (optional)</label>
                                        <div className="auth-page__phone-input">
                                            <span className="auth-page__country-prefix">+234</span>
                                            <input
                                                id={`${variant}-phone`}
                                                type="tel"
                                                inputMode="tel"
                                                value={phone}
                                                onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
                                                placeholder="8012345678"
                                            />
                                        </div>
                                    </div>

                                    {statusMessages}

                                    <div className="auth-page__wizard-actions auth-page__wizard-actions--single">
                                        <button
                                            type="button"
                                            className="auth-page__submit"
                                            disabled={!canContinueStep1}
                                            onClick={() => moveSetupStep(setCurrentStep, 2)}
                                        >
                                            Continue
                                        </button>
                                    </div>
                                </>
                            )}

                            {currentStep === 2 && (
                                <>
                                    <div className="auth-page__input-group">
                                        <label htmlFor={`${variant}-role`}>Role/Profession</label>
                                        <select
                                            id={`${variant}-role`}
                                            className="auth-page__select"
                                            value={role}
                                            onChange={(e) => handleRoleChange(e.target.value)}
                                            autoFocus
                                            required
                                        >
                                            {ROLE_OPTIONS.map((opt) => (
                                                <option key={opt.value} value={opt.value} disabled={!opt.value}>
                                                    {opt.label}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    {needsProfession && (
                                        <div className="auth-page__input-group">
                                            <label htmlFor={`${variant}-profession`}>Profession</label>
                                            <input
                                                id={`${variant}-profession`}
                                                type="text"
                                                value={profession}
                                                onChange={(e) => handleProfessionChange(e.target.value)}
                                                placeholder="e.g. Dietitian, Laboratory Scientist"
                                                required
                                            />
                                        </div>
                                    )}

                                    <div className="auth-page__input-group">
                                        <label htmlFor={`${variant}-preferred-name`}>What should Rx call you?</label>
                                        <input
                                            id={`${variant}-preferred-name`}
                                            type="text"
                                            value={preferred}
                                            onChange={(e) => setPreferred(e.target.value)}
                                            placeholder="Preferred name"
                                            required
                                        />
                                        {role && <p className="auth-page__hint">{preferredNameHint}</p>}
                                    </div>

                                    {statusMessages}

                                    <div className="auth-page__wizard-actions">
                                        <button
                                            type="button"
                                            className="auth-page__secondary-action"
                                            onClick={() => moveSetupStep(setCurrentStep, 1)}
                                        >
                                            Back
                                        </button>
                                        <button
                                            type="button"
                                            className="auth-page__submit"
                                            disabled={!canContinueStep2}
                                            onClick={() => moveSetupStep(setCurrentStep, 3)}
                                        >
                                            Continue
                                        </button>
                                    </div>
                                </>
                            )}

                            {currentStep === 3 && (
                                <>
                                    <div className="auth-page__input-group">
                                        <label htmlFor={`${variant}-password`}>Password</label>
                                        <input
                                            id={`${variant}-password`}
                                            type={showPassword ? 'text' : 'password'}
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            placeholder="At least 8 characters"
                                            autoComplete="new-password"
                                            autoFocus
                                            required
                                        />
                                    </div>

                                    <div className="auth-page__input-group">
                                        <label htmlFor={`${variant}-confirm-password`}>
                                            Confirm Password
                                            {passwordMatch === true && <span className="auth-page__match auth-page__match--yes"> ✓ Match</span>}
                                            {passwordMatch === false && <span className="auth-page__match auth-page__match--no"> ✗ Mismatch</span>}
                                        </label>
                                        <input
                                            id={`${variant}-confirm-password`}
                                            type={showPassword ? 'text' : 'password'}
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            placeholder="Re-enter password"
                                            autoComplete="new-password"
                                            required
                                        />
                                    </div>

                                    <div className="auth-page__show-password">
                                        <input
                                            type="checkbox"
                                            id={showPasswordId}
                                            checked={showPassword}
                                            onChange={(e) => setShowPassword(e.target.checked)}
                                        />
                                        <label htmlFor={showPasswordId}>Show password</label>
                                    </div>

                                    {statusMessages}

                                    <div className="auth-page__wizard-actions">
                                        <button
                                            type="button"
                                            className="auth-page__secondary-action"
                                            onClick={() => moveSetupStep(setCurrentStep, 2)}
                                        >
                                            Back
                                        </button>
                                        <button
                                            type="submit"
                                            className="auth-page__submit"
                                            disabled={loading || password.length < 8 || !passwordMatch}
                                        >
                                            {loading ? 'Creating account...' : 'Create Account'}
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    </form>
                </div>
            </div>
        )
    }

    // ─── Profile Setup Form (registration step 3) ───
    if (step === 'profile_setup') {
        return renderSetupWizard({
            variant: 'setup',
            subtitle: null,
            currentStep: setupStep,
            setCurrentStep: setSetupStep,
            first: firstName,
            setFirst: setFirstName,
            last: lastName,
            setLast: setLastName,
            selectedGender: gender,
            setSelectedGender: setGender,
            selectedAgeRange: ageRange,
            setSelectedAgeRange: setAgeRange,
            phone: phoneNumber,
            setPhone: setPhoneNumber,
            role: setupRole,
            setRole: setSetupRole,
            profession: setupProfession,
            setProfession: setSetupProfession,
            preferred: preferredName,
            setPreferred: setPreferredName,
            password: setupPassword,
            setPassword: setSetupPassword,
            confirmPassword: setupConfirmPassword,
            setConfirmPassword: setSetupConfirmPassword,
            passwordMatch: setupPasswordsMatch,
            onSubmit: handleProfileSetup,
            showPasswordId: 'setup-show-pass',
        })
    }

    // ─── Google Setup Form ───
    if (step === 'google_setup') {
        return renderSetupWizard({
            variant: 'google',
            subtitle: null,
            currentStep: googleSetupStep,
            setCurrentStep: setGoogleSetupStep,
            first: googleFirstName,
            setFirst: setGoogleFirstName,
            last: googleLastName,
            setLast: setGoogleLastName,
            selectedGender: googleGender,
            setSelectedGender: setGoogleGender,
            selectedAgeRange: googleAgeRange,
            setSelectedAgeRange: setGoogleAgeRange,
            phone: googlePhoneNumber,
            setPhone: setGooglePhoneNumber,
            role: googleRole,
            setRole: setGoogleRole,
            profession: googleProfession,
            setProfession: setGoogleProfession,
            preferred: googlePreferredName,
            setPreferred: setGooglePreferredName,
            password: googlePassword,
            setPassword: setGooglePassword,
            confirmPassword: googleConfirmPassword,
            setConfirmPassword: setGoogleConfirmPassword,
            passwordMatch: googlePasswordsMatch,
            onSubmit: handleGoogleSetup,
            showPasswordId: 'google-show-pass',
            compactIdentity: true,
        })
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
                    {otpTitle}
                </h1>
                <p className="auth-page__subtitle">
                    {otpIntro} <strong>{email}</strong>
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
