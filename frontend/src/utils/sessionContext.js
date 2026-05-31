export const ROLE_OPTIONS = [
    { value: 'patient', label: 'Patient' },
    { value: 'pharmacist', label: 'Pharmacist' },
    { value: 'physician', label: 'Physician' },
    { value: 'nurse', label: 'Nurse' },
    { value: 'other', label: 'Other health professional' },
]

export const SUBJECT_OPTIONS = [
    { value: 'self', label: 'Myself' },
    { value: 'other_patient', label: 'Another patient' },
    { value: 'general', label: 'General information' },
]

export const PATIENT_SEX_OPTIONS = [
    { value: 'male', label: 'Male' },
    { value: 'female', label: 'Female' },
]

export const PREGNANCY_OPTIONS = [
    { value: 'not_pregnant_or_breastfeeding', label: 'Not pregnant or breastfeeding' },
    { value: 'pregnant', label: 'Pregnant' },
    { value: 'breastfeeding', label: 'Breastfeeding' },
    { value: 'unsure', label: 'Unsure' },
]

const STORAGE_KEY = 'shodic:last-session-context'

export const DEFAULT_SESSION_CONTEXT = Object.freeze({
    role: 'patient',
    subject: 'self',
    patient_sex: '',
    pregnancy_status: '',
})

function optionValues(options) {
    return options.map((option) => option.value)
}

const ROLE_VALUES = optionValues(ROLE_OPTIONS)
const SUBJECT_VALUES = optionValues(SUBJECT_OPTIONS)
const PATIENT_SEX_VALUES = optionValues(PATIENT_SEX_OPTIONS)
const PREGNANCY_VALUES = optionValues(PREGNANCY_OPTIONS)

function getLabel(options, value) {
    return options.find((option) => option.value === value)?.label || ''
}

export function normalizeSessionContext(context = {}) {
    const role = ROLE_VALUES.includes(context.role) ? context.role : DEFAULT_SESSION_CONTEXT.role
    const subject = SUBJECT_VALUES.includes(context.subject) ? context.subject : DEFAULT_SESSION_CONTEXT.subject
    const patientSex = PATIENT_SEX_VALUES.includes(context.patient_sex) ? context.patient_sex : ''
    let pregnancyStatus = PREGNANCY_VALUES.includes(context.pregnancy_status) ? context.pregnancy_status : ''

    if (patientSex === 'male') {
        pregnancyStatus = 'not_applicable'
    }

    if (!patientSex) {
        pregnancyStatus = ''
    }

    return {
        role,
        subject,
        patient_sex: patientSex,
        pregnancy_status: pregnancyStatus,
    }
}

export function isSessionContextComplete(context = {}) {
    const normalized = normalizeSessionContext(context)
    if (!normalized.role || !normalized.subject || !normalized.patient_sex) return false
    if (normalized.patient_sex === 'female') {
        return PREGNANCY_VALUES.includes(normalized.pregnancy_status)
    }
    return normalized.patient_sex === 'male'
}

export function loadLastSessionContext() {
    if (typeof window === 'undefined') return { ...DEFAULT_SESSION_CONTEXT }

    try {
        const stored = window.localStorage.getItem(STORAGE_KEY)
        return stored ? normalizeSessionContext(JSON.parse(stored)) : { ...DEFAULT_SESSION_CONTEXT }
    } catch {
        return { ...DEFAULT_SESSION_CONTEXT }
    }
}

export function saveLastSessionContext(context) {
    if (typeof window === 'undefined') return

    try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(normalizeSessionContext(context)))
    } catch {
        // localStorage can be unavailable in private or locked-down browsers.
    }
}

export function getSessionContextChips(context = {}) {
    const roleLabel = getLabel(ROLE_OPTIONS, normalizeSessionContext(context).role)
    return roleLabel ? [roleLabel] : []
}

export function prepareSessionContextPayload(context = {}) {
    const normalized = normalizeSessionContext(context)
    return {
        role: normalized.role,
        subject: normalized.subject,
        patient_sex: normalized.patient_sex,
        pregnancy_status: normalized.pregnancy_status,
    }
}
