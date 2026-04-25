import './DateSeparator.css'

const DAY_MS = 24 * 60 * 60 * 1000

function startOfDay(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function formatDateLabel(value) {
    if (!value) return ''

    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return ''

    const today = startOfDay(new Date())
    const messageDay = startOfDay(date)
    const diffDays = Math.round((today - messageDay) / DAY_MS)

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays > 1 && diffDays < 7) {
        return date.toLocaleDateString('en-GB', { weekday: 'long' })
    }

    return date.toLocaleDateString('en-GB', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
    })
}

function DateSeparator({ date }) {
    const label = formatDateLabel(date)
    if (!label) return null

    return (
        <div className="date-separator" role="separator" aria-label={label}>
            <span className="date-separator__label">{label}</span>
        </div>
    )
}

export default DateSeparator
