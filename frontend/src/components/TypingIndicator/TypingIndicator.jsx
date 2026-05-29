import './TypingIndicator.css'

function TypingIndicator({ label = 'Thinking' }) {
    return (
        <div className="typing">
            <div className="typing__bubble">
                <span className="typing__label">{label}</span>
            </div>
        </div>
    )
}

export default TypingIndicator
