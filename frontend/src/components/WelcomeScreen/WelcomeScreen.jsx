import { HiOutlineBeaker, HiOutlineShieldExclamation, HiOutlineQuestionMarkCircle, HiOutlineClipboardDocumentList } from 'react-icons/hi2'
import { PRODUCT } from '../../config/product'
import './WelcomeScreen.css'

const suggestions = [
    {
        icon: <HiOutlineBeaker size={16} />,
        label: 'Medication Info',
        text: 'What are the side effects of metformin?',
    },
    {
        icon: <HiOutlineShieldExclamation size={16} />,
        label: 'Drug Interactions',
        text: 'Can I take ibuprofen with blood thinners?',
    },
    {
        icon: <HiOutlineQuestionMarkCircle size={16} />,
        label: 'OTC Suggestions',
        text: 'What can I take for seasonal allergies?',
    },
    {
        icon: <HiOutlineClipboardDocumentList size={16} />,
        label: 'Dosage Guide',
        text: "What's the recommended dose of amoxicillin for adults?",
    },
]

function getGreeting() {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 17) return 'Good afternoon'
    return 'Good evening'
}

function WelcomeScreen({ onSuggestionClick, inputSlot }) {
    const greeting = getGreeting()

    return (
        <div className="welcome">
            <div className="welcome__hero">
                <h1 className="welcome__greeting">{greeting}.</h1>
                <p className="welcome__tagline">How can I help you today?</p>
            </div>

            {/* Chat input rendered inline between greeting and chips */}
            {inputSlot && (
                <div className="welcome__input-slot">
                    {inputSlot}
                </div>
            )}

            <div className="welcome__chips">
                {suggestions.map((s, i) => (
                    <button
                        key={i}
                        className="welcome__chip"
                        onClick={() => onSuggestionClick(s.text)}
                    >
                        <span className="welcome__chip-icon">{s.icon}</span>
                        {s.label}
                    </button>
                ))}
            </div>

            <div className="welcome__disclaimer">
                <strong>Disclaimer:</strong> {PRODUCT.name} provides general health information only. Always consult a qualified healthcare professional for medical advice.
            </div>
        </div>
    )
}

export default WelcomeScreen
