import { useMemo, useState } from 'react'
import { HiOutlineCheckCircle, HiOutlineHeart, HiOutlineUser, HiOutlineUserGroup, HiOutlineXMark } from 'react-icons/hi2'
import {
    isSessionContextComplete,
    normalizeSessionContext,
    PATIENT_SEX_OPTIONS,
    PREGNANCY_OPTIONS,
    ROLE_OPTIONS,
    SUBJECT_OPTIONS,
} from '../../utils/sessionContext'
import './SessionContextModal.css'

const subjectIcons = {
    self: <HiOutlineUser size={18} />,
    other_patient: <HiOutlineUserGroup size={18} />,
    general: <HiOutlineHeart size={18} />,
}

function OptionButton({ active, children, className = '', ...props }) {
    return (
        <button
            type="button"
            className={`session-modal__option ${active ? 'session-modal__option--active' : ''} ${className}`}
            {...props}
        >
            {children}
        </button>
    )
}

function SelectField({ label, value, placeholder, options, onChange }) {
    return (
        <label className="session-modal__field">
            <span className="session-modal__label">{label}</span>
            <span className="session-modal__select-shell">
                <select className="session-modal__select" value={value} onChange={onChange}>
                    {placeholder && <option value="" disabled>{placeholder}</option>}
                    {options.map((option) => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                </select>
            </span>
        </label>
    )
}

function SessionContextModal({
    isOpen,
    initialContext,
    isSaving = false,
    error = '',
    onClose,
    onSubmit,
}) {
    const [draft, setDraft] = useState(() => normalizeSessionContext(initialContext))

    const isComplete = useMemo(() => isSessionContextComplete(draft), [draft])

    if (!isOpen) return null

    const updateDraft = (nextValues) => {
        setDraft((current) => normalizeSessionContext({ ...current, ...nextValues }))
    }

    const handleSexChange = (patientSex) => {
        updateDraft({
            patient_sex: patientSex,
            pregnancy_status: patientSex === 'male' ? 'not_applicable' : '',
        })
    }

    const handleSubmit = (event) => {
        event.preventDefault()
        if (!isComplete || isSaving) return
        onSubmit?.(normalizeSessionContext(draft))
    }

    return (
        <div className="session-modal" role="presentation">
            <div className="session-modal__backdrop" onClick={onClose} />
            <form className="session-modal__dialog" onSubmit={handleSubmit} role="dialog" aria-modal="true" aria-labelledby="session-modal-title">
                <div className="session-modal__header">
                    <div>
                        <p className="session-modal__eyebrow">Hospital session</p>
                        <h2 id="session-modal-title">New session context</h2>
                    </div>
                    <button type="button" className="session-modal__close" onClick={onClose} aria-label="Close">
                        <HiOutlineXMark size={20} />
                    </button>
                </div>

                <div className="session-modal__desktop-fields">
                    <div className="session-modal__section">
                        <label className="session-modal__label">Who are you?</label>
                        <div className="session-modal__grid session-modal__grid--roles">
                            {ROLE_OPTIONS.map((option) => (
                                <OptionButton
                                    key={option.value}
                                    active={draft.role === option.value}
                                    onClick={() => updateDraft({ role: option.value })}
                                >
                                    {option.label}
                                </OptionButton>
                            ))}
                        </div>
                    </div>

                    <div className="session-modal__section">
                        <label className="session-modal__label">Who are you asking for?</label>
                        <div className="session-modal__grid">
                            {SUBJECT_OPTIONS.map((option) => (
                                <OptionButton
                                    key={option.value}
                                    active={draft.subject === option.value}
                                    onClick={() => updateDraft({ subject: option.value })}
                                >
                                    <span className="session-modal__option-icon">{subjectIcons[option.value]}</span>
                                    {option.label}
                                </OptionButton>
                            ))}
                        </div>
                    </div>

                    <div className="session-modal__section">
                        <label className="session-modal__label">Gender of the subject</label>
                        <div className="session-modal__segmented">
                            {PATIENT_SEX_OPTIONS.map((option) => (
                                <OptionButton
                                    key={option.value}
                                    active={draft.patient_sex === option.value}
                                    className="session-modal__segment"
                                    onClick={() => handleSexChange(option.value)}
                                >
                                    {option.label}
                                </OptionButton>
                            ))}
                        </div>
                    </div>

                    {draft.patient_sex === 'female' && (
                        <div className="session-modal__section">
                            <label className="session-modal__label">Pregnancy/breastfeeding</label>
                            <div className="session-modal__grid">
                                {PREGNANCY_OPTIONS.map((option) => (
                                    <OptionButton
                                        key={option.value}
                                        active={draft.pregnancy_status === option.value}
                                        onClick={() => updateDraft({ pregnancy_status: option.value })}
                                    >
                                        {option.label}
                                    </OptionButton>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <div className="session-modal__mobile-fields">
                    <SelectField
                        label="Who are you?"
                        value={draft.role}
                        options={ROLE_OPTIONS}
                        onChange={(event) => updateDraft({ role: event.target.value })}
                    />
                    <SelectField
                        label="Who are you asking for?"
                        value={draft.subject}
                        options={SUBJECT_OPTIONS}
                        onChange={(event) => updateDraft({ subject: event.target.value })}
                    />
                    <SelectField
                        label="Gender of the subject"
                        value={draft.patient_sex}
                        placeholder="Select gender"
                        options={PATIENT_SEX_OPTIONS}
                        onChange={(event) => handleSexChange(event.target.value)}
                    />
                    {draft.patient_sex === 'female' && (
                        <SelectField
                            label="Pregnancy/breastfeeding"
                            value={draft.pregnancy_status}
                            placeholder="Select status"
                            options={PREGNANCY_OPTIONS}
                            onChange={(event) => updateDraft({ pregnancy_status: event.target.value })}
                        />
                    )}
                </div>

                {error && <div className="session-modal__error" role="alert">{error}</div>}

                <div className="session-modal__footer">
                    <button type="button" className="session-modal__secondary" onClick={onClose}>
                        Cancel
                    </button>
                    <button type="submit" className="session-modal__primary" disabled={!isComplete || isSaving}>
                        <HiOutlineCheckCircle size={18} />
                        {isSaving ? 'Saving...' : 'Start session'}
                    </button>
                </div>
            </form>
        </div>
    )
}

export default SessionContextModal
