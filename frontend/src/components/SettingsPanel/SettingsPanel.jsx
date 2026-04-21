import { useState, useEffect } from 'react'
import { HiOutlineXMark, HiOutlineArrowRightOnRectangle, HiOutlineEnvelope, HiOutlineShieldCheck, HiOutlineCpuChip } from 'react-icons/hi2'
import './SettingsPanel.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const ROLES = [
    { value: 'patient', label: 'Patient' },
    { value: 'pharmacist', label: 'Pharmacist' },
    { value: 'physician', label: 'Physician' },
    { value: 'nurse', label: 'Nurse' },
    { value: 'other_health_professional', label: 'Other Health Professional' },
]

function SettingsPanel({ isOpen, onClose, user, onLogout, onUserUpdate, providers, activeProvider, onProviderChange }) {
    const [firstName, setFirstName] = useState('')
    const [lastName, setLastName] = useState('')
    const [preferredName, setPreferredName] = useState('')
    const [role, setRole] = useState('patient')
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

    const handleSaveProfile = async () => {
        setSaving(true)
        setSaveMsg('')
        try {
            const resp = await fetch(`${API}/api/auth/profile/`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ first_name: firstName, last_name: lastName, preferred_name: preferredName, role }),
            })
            const data = await resp.json()
            if (resp.ok) {
                setSaveMsg('Profile updated!')
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
            const resp = await fetch(`${API}/api/auth/email/add/`, {
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
            const resp = await fetch(`${API}/api/auth/email/verify/`, {
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
                    {/* AI Model Section */}
                    <section className="settings-panel__section">
                        <h3 className="settings-panel__section-title">
                            <HiOutlineCpuChip size={16} />
                            AI Model
                        </h3>

                        {providers && providers.length > 0 ? (
                            <div className="settings-panel__provider-grid">
                                {providers.map((p) => (
                                    <button
                                        key={p.slug}
                                        className={`settings-panel__provider-card ${activeProvider === p.slug ? 'settings-panel__provider-card--active' : ''}`}
                                        onClick={() => onProviderChange(p.slug)}
                                        id={`provider-${p.slug}`}
                                    >
                                        <span className="settings-panel__provider-name">{p.name}</span>
                                        <span className="settings-panel__provider-model">{p.model_display}</span>
                                        {activeProvider === p.slug && (
                                            <span className="settings-panel__provider-check">✓</span>
                                        )}
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <p className="settings-panel__provider-empty">No providers available</p>
                        )}
                    </section>

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

                        <button
                            className="settings-panel__save-btn"
                            onClick={handleSaveProfile}
                            disabled={saving}
                        >
                            {saving ? 'Saving...' : 'Save Changes'}
                        </button>

                        {saveMsg && (
                            <p className={`settings-panel__msg ${saveMsg.includes('updated') ? 'settings-panel__msg--success' : 'settings-panel__msg--error'}`}>
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
