import { HiOutlineBeaker, HiOutlineShieldExclamation, HiOutlineQuestionMarkCircle, HiOutlineClipboardDocumentList } from 'react-icons/hi2'
import './WelcomeScreen.css'

const suggestions = [
    {
        icon: <HiOutlineBeaker size={20} />,
        title: 'Medication Info',
        text: 'What are the side effects of metformin?',
    },
    {
        icon: <HiOutlineShieldExclamation size={20} />,
        title: 'Drug Interactions',
        text: 'Can I take ibuprofen with blood thinners?',
    },
    {
        icon: <HiOutlineQuestionMarkCircle size={20} />,
        title: 'OTC Suggestions',
        text: 'What can I take for seasonal allergies?',
    },
    {
        icon: <HiOutlineClipboardDocumentList size={20} />,
        title: 'Dosage Guide',
        text: "What's the recommended dose of amoxicillin for adults?",
    },
]

function WelcomeScreen({ onSuggestionClick }) {
    return (
        <div className="welcome">
            <div className="welcome__icon">Rx</div>
            <h1 className="welcome__title">How can I help you today?</h1>
            <p className="welcome__subtitle">
                I can answer questions about medications, check drug interactions, and suggest over-the-counter alternatives.
            </p>
            <div className="welcome__suggestions">
                {suggestions.map((s, i) => (
                    <button
                        key={i}
                        className="welcome__suggestion"
                        onClick={() => onSuggestionClick(s.text)}
                    >
                        <div className="welcome__suggestion-icon">{s.icon}</div>
                        <div className="welcome__suggestion-text">
                            <strong>{s.title}</strong>
                            {s.text}
                        </div>
                    </button>
                ))}
            </div>
        </div>
    )
}

export default WelcomeScreen
