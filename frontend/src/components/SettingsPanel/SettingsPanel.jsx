import { useState, useEffect } from 'react'
import { HiOutlineXMark, HiOutlineArrowRightOnRectangle, HiOutlineEnvelope, HiOutlineShieldCheck } from 'react-icons/hi2'
import './SettingsPanel.css'

const API = import.meta.env.VITE_API_BASE_URL || '/api'

const ROLES = [
    { value: 'patient', label: 'Patient' },
    { value: 'pharmacist', label: 'Pharmacist' },
    { value: 'physician', label: 'Physician' },
    { value: 'nurse', label: 'Nurse' },
    { value: 'other_health_professional', label: 'Other Health Professional' },
]

const GENDERS = [
    { value: '', label: 'Select gender' },
    { value: 'male', label: 'Male' },
    { value: 'female', label: 'Female' },
]

const AGE_RANGES = [
    { value: '', label: 'Select age range' },
    { value: 'under_18', label: 'Under 18' },
    { value: '18_24', label: '18-24' },
    { value: '25_34', label: '25-34' },
    { value: '35_44', label: '35-44' },
    { value: '45_54', label: '45-54' },
    { value: '55_64', label: '55-64' },
    { value: '65_plus', label: '65+' },
]

function normalizeNigeriaPhone(value) {
    const digits = value.replace(/\D/g, '')
    const withoutCountryCode = digits.replace(/^234/, '').replace(/^0/, '')
    return withoutCountryCode ? `+234${withoutCountryCode}` : ''
}

function formatPhoneForInput(value) {
    return String(value || '').replace(/\D/g, '').replace(/^234/, '').replace(/^0/, '')
}

function SettingsPanel({ isOpen, onClose, user, onLogout, onUserUpdate }) {
    const [firstName, setFirstName] = useState('')
    const [lastName, setLastName] = useState('')
    const [preferredName, setPreferredName] = useState('')
    const [role, setRole] = useState('patient')
    const [gender, setGender] = useState('')
    const [ageRange, setAgeRange] = useState('')
    const [phoneNumber, setPhoneNumber] = useState('')
    const [saving, setSaving] = useState(false)
    const [saveMsg, setSaveMsg] = useState('')

    // Email change state
    const [showEmailChange, setShowEmailChange] = useState(false)
    const [newEmail, setNewEmail] = useState('')
    const [emailOtp, setEmailOtp] = useState('')
    const [emailStep, setEmailStep] = useState('input') // 'input' | 'verify'
    const [emailSaving, setEmailSaving] = useState(false)
    const [emailMsg, setEmailMsg] = useState('')

    // Populate fields when user changes
    useEffect(() => {
        if (user) {
            setFirstName(user.first_name || '')
            setLastName(user.last_name || '')
            setPreferredName(user.preferred_name || '')
            setRole(user.role || 'patient')
            setGender(user.gender || '')
            setAgeRange(user.age_range || '')
            setPhoneNumber(formatPhoneForInput(user.phone_number))
            setSaveMsg('')
        }
    }, [user])

    // Reset email change form when panel closes
    useEffect(() => {
        if (!isOpen) {
            setShowEmailChange(false)
            setNewEmail('')
            setEmailOtp('')
            setEmailStep('input')
            setEmailMsg('')
        }
    }, [isOpen])

    const hasChanges = user && (
        firstName !== (user.first_name || '') ||
        lastName !== (user.last_name || '') ||
        preferredName !== (user.preferred_name || '') ||
        role !== (user.role || 'patient') ||
        gender !== (user.gender || '') ||
        ageRange !== (user.age_range || '') ||
        normalizeNigeriaPhone(phoneNumber) !== (user.phone_number || '')
    )

    const handleSaveProfile = async () => {
        if (!hasChanges) return
        setSaving(true)
        setSaveMsg('')
        try {
            const resp = await fetch(`${API}/auth/profile/`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    first_name: firstName,
                    last_name: lastName,
                    preferred_name: preferredName,
                    role,
                    gender,
                    age_range: ageRange,
                    phone_number: normalizeNigeriaPhone(phoneNumber),
                }),
            })
            const data = await resp.json()
            if (resp.ok) {
                setSaveMsg('Changes saved')
                if (onUserUpdate) onUserUpdate(data)
                setTimeout(() => setSaveMsg(''), 3000)
            } else {
                setSaveMsg(data.error || 'Failed to update')
            }
        } catch {
            setSaveMsg('Network error')
        } finally {
            setSaving(false)
        }
    }

    const handleAddEmail = async () => {
        setEmailSaving(true)
        setEmailMsg('')
        try {
            const resp = await fetch(`${API}/auth/email/add/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email: newEmail }),
            })
            const data = await resp.json()
            if (resp.ok) {
                setEmailStep('verify')
                setEmailMsg('Code sent! Check your new email.')
            } else {
                setEmailMsg(data.error || 'Failed to send code')
            }
        } catch {
            setEmailMsg('Network error')
        } finally {
            setEmailSaving(false)
        }
    }

    const handleVerifyEmail = async () => {
        setEmailSaving(true)
        setEmailMsg('')
        try {
            const resp = await fetch(`${API}/auth/email/verify/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email: newEmail, otp: emailOtp }),
            })
            const data = await resp.json()
            if (resp.ok) {
                setEmailMsg('Email updated successfully!')
                setShowEmailChange(false)
                setNewEmail('')
                setEmailOtp('')
                setEmailStep('input')
                if (onUserUpdate) onUserUpdate(data)
            } else {
                setEmailMsg(data.error || 'Verification failed')
            }
        } catch {
            setEmailMsg('Network error')
        } finally {
            setEmailSaving(false)
        }
    }

    if (!isOpen) return null

    return (
        <>
            <div className="settings-panel__overlay" onClick={onClose} />
            <div className="settings-panel">
                <div className="settings-panel__header">
                    <h2 className="settings-panel__title">Settings</h2>
                    <button className="settings-panel__close" onClick={onClose} aria-label="Close settings">
                        <HiOutlineXMark size={20} />
                    </button>
                </div>

                <div className="settings-panel__content">
                    {/* Profile Section */}
                    <section className="settings-panel__section">
                        <h3 className="settings-panel__section-title">Profile</h3>

                        <div className="settings-panel__field">
                            <label className="settings-panel__label" htmlFor="sp-first-name">First Name</label>
                            <input
                                id="sp-first-name"
                                className="settings-panel__input"
                                type="text"
                                value={firstName}
                                onChange={(e) => setFirstName(e.target.value)}
                                placeholder="First name"
                            />
                        </div>

                        <div className="settings-panel__field">
                            <label className="settings-panel__label" htmlFor="sp-last-name">Last Name</label>
                            <input
                                id="sp-last-name"
                                className="settings-panel__input"
                                type="text"
                                value={lastName}
                                onChange={(e) => setLastName(e.target.value)}
                                placeholder="Last name"
                            />
                        </div>

                        <div className="settings-panel__field">
                            <label className="settings-panel__label" htmlFor="sp-preferred-name">
                                Preferred Name
                                <span className="settings-panel__label-hint">What should Rx call you?</span>
                            </label>
                            <input
                                id="sp-preferred-name"
                                className="settings-panel__input"
                                type="text"
                                value={preferredName}
                                onChange={(e) => setPreferredName(e.target.value)}
                                placeholder="e.g. Doc, Chief, ..."
                            />
                        </div>

                        <div className="settings-panel__field">
                            <label className="settings-panel__label" htmlFor="sp-role">Role</label>
                            <select
                                id="sp-role"
                                className="settings-panel__select"
                                value={role}
                                onChange={(e) => setRole(e.target.value)}
                            >
                                {ROLES.map((r) => (
                                    <option key={r.value} value={r.value}>{r.label}</option>
                                ))}
                            </select>
                        </div>

                        <div className="settings-panel__field-row">
                            <div className="settings-panel__field">
                                <label className="settings-panel__label" htmlFor="sp-gender">Gender</label>
                                <select
                                    id="sp-gender"
                                    className="settings-panel__select"
                                    value={gender}
                                    onChange={(e) => setGender(e.target.value)}
                                    required
                                >
                                    {GENDERS.map((item) => (
                                        <option key={item.value} value={item.value} disabled={!item.value}>
                                            {item.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div className="settings-panel__field">
                                <label className="settings-panel__label" htmlFor="sp-age-range">Age Range</label>
                                <select
                                    id="sp-age-range"
                                    className="settings-panel__select"
                                    value={ageRange}
                                    onChange={(e) => setAgeRange(e.target.value)}
                                    required
                                >
                                    {AGE_RANGES.map((item) => (
                                        <option key={item.value} value={item.value} disabled={!item.value}>
                                            {item.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </div>

                        <div className="settings-panel__field">
                            <label className="settings-panel__label" htmlFor="sp-phone-number">Phone Number</label>
                            <div className="settings-panel__phone-input">
                                <span className="settings-panel__country-prefix">+234</span>
                                <input
                                    id="sp-phone-number"
                                    className="settings-panel__input"
                                    type="tel"
                                    inputMode="tel"
                                    value={phoneNumber}
                                    onChange={(e) => setPhoneNumber(e.target.value.replace(/\D/g, ''))}
                                    placeholder="8012345678"
                                />
                            </div>
                        </div>

                        <button
                            className="settings-panel__save-btn"
                            onClick={handleSaveProfile}
                            disabled={saving || !hasChanges || !gender || !ageRange}
                        >
                            {saving ? 'Saving...' : 'Save Changes'}
                        </button>

                        {saveMsg && (
                            <p className={`settings-panel__msg ${saveMsg.toLowerCase().includes('saved') ? 'settings-panel__msg--success' : 'settings-panel__msg--error'}`}>
                                {saveMsg}
                            </p>
                        )}
                    </section>

                    {/* Email Section */}
                    <section className="settings-panel__section">
                        <h3 className="settings-panel__section-title">
                            <HiOutlineEnvelope size={16} />
                            Email
                        </h3>

                        <div className="settings-panel__email-current">
                            <span className="settings-panel__email-address">{user?.email}</span>
                            <span className="settings-panel__email-badge">
                                <HiOutlineShieldCheck size={14} />
                                Verified
                            </span>
                        </div>

                        {!showEmailChange ? (
                            <button
                                className="settings-panel__link-btn"
                                onClick={() => setShowEmailChange(true)}
                            >
                                Change email
                            </button>
                        ) : (
                            <div className="settings-panel__email-form">
                                {emailStep === 'input' && (
                                    <>
                                        <input
                                            className="settings-panel__input"
                                            type="email"
                                            value={newEmail}
                                            onChange={(e) => setNewEmail(e.target.value)}
                                            placeholder="New email address"
                                        />
                                        <div className="settings-panel__email-actions">
                                            <button
                                                className="settings-panel__save-btn settings-panel__save-btn--sm"
                                                onClick={handleAddEmail}
                                                disabled={emailSaving || !newEmail.trim()}
                                            >
                                                {emailSaving ? 'Sending...' : 'Send Code'}
                                            </button>
                                            <button
                                                className="settings-panel__link-btn"
                                                onClick={() => { setShowEmailChange(false); setEmailMsg('') }}
                                            >
                                                Cancel
                                            </button>
                                        </div>
                                    </>
                                )}
                                {emailStep === 'verify' && (
                                    <>
                                        <p className="settings-panel__email-hint">
                                            Enter the 6-digit code sent to <strong>{newEmail}</strong>
                                        </p>
                                        <input
                                            className="settings-panel__input settings-panel__input--otp"
                                            type="text"
                                            maxLength={6}
                                            value={emailOtp}
                                            onChange={(e) => setEmailOtp(e.target.value.replace(/\D/g, ''))}
                                            placeholder="000000"
                                        />
                                        <div className="settings-panel__email-actions">
                                            <button
                                                className="settings-panel__save-btn settings-panel__save-btn--sm"
                                                onClick={handleVerifyEmail}
                                                disabled={emailSaving || emailOtp.length !== 6}
                                            >
                                                {emailSaving ? 'Verifying...' : 'Verify & Update'}
                                            </button>
                                            <button
                                                className="settings-panel__link-btn"
                                                onClick={() => { setEmailStep('input'); setEmailOtp(''); setEmailMsg('') }}
                                            >
                                                Back
                                            </button>
                                        </div>
                                    </>
                                )}
                                {emailMsg && (
                                    <p className={`settings-panel__msg ${emailMsg.includes('success') || emailMsg.includes('sent') || emailMsg.includes('updated') ? 'settings-panel__msg--success' : 'settings-panel__msg--error'}`}>
                                        {emailMsg}
                                    </p>
                                )}
                            </div>
                        )}
                    </section>

                    {/* Plan Section */}
                    <section className="settings-panel__section">
                        <h3 className="settings-panel__section-title">Plan</h3>
                        <div className="settings-panel__plan-badge">
                            <span className="settings-panel__plan-name">Free</span>
                            <span className="settings-panel__plan-desc">50 messages/day · 10 conversations</span>
                        </div>
                    </section>
                </div>

                {/* Footer */}
                <div className="settings-panel__footer">
                    <button className="settings-panel__logout-btn" onClick={onLogout}>
                        <HiOutlineArrowRightOnRectangle size={18} />
                        Log out
                    </button>
                </div>
            </div>
        </>
    )
}

export default SettingsPanel
