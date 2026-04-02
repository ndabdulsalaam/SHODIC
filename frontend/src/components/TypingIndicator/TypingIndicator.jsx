import './TypingIndicator.css'

function TypingIndicator() {
    return (
        <div className="typing">
            <div className="typing__avatar">Rx</div>
            <div className="typing__bubble">
                <span className="typing__dot" />
                <span className="typing__dot" />
                <span className="typing__dot" />
            </div>
        </div>
    )
}

export default TypingIndicator
