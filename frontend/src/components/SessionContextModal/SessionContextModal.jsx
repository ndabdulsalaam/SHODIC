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

function SessionContextModal({
    isOpen,
    initialContext,
    canDismiss = false,
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
            <div className="session-modal__backdrop" onClick={canDismiss ? onClose : undefined} />
            <form className="session-modal__dialog" onSubmit={handleSubmit} role="dialog" aria-modal="true" aria-labelledby="session-modal-title">
                <div className="session-modal__header">
                    <div>
                        <p className="session-modal__eyebrow">Hospital session</p>
                        <h2 id="session-modal-title">New session context</h2>
                    </div>
                    {canDismiss && (
                        <button type="button" className="session-modal__close" onClick={onClose} aria-label="Close">
                            <HiOutlineXMark size={20} />
                        </button>
                    )}
                </div>

                <div className="session-modal__section">
                    <label className="session-modal__label">Role</label>
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
                    <label className="session-modal__label">Subject</label>
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
                    <label className="session-modal__label">Patient sex/gender</label>
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

                {error && <div className="session-modal__error" role="alert">{error}</div>}

                <div className="session-modal__footer">
                    {canDismiss && (
                        <button type="button" className="session-modal__secondary" onClick={onClose}>
                            Cancel
                        </button>
                    )}
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
