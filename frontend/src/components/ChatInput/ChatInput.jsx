import { useState, useRef, useEffect } from 'react'
import { HiOutlinePaperAirplane } from 'react-icons/hi2'
import './ChatInput.css'

function ChatInput({ onSend, isLoading }) {
    const [text, setText] = useState('')
    const textareaRef = useRef(null)

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
        }
    }, [text])

    const handleSubmit = () => {
        const trimmed = text.trim()
        if (!trimmed || isLoading) return
        onSend(trimmed)
        setText('')
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        }
    }

    const hasText = text.trim().length > 0

    return (
        <div className="chat-input">
            <textarea
                ref={textareaRef}
                className="chat-input__textarea"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about medications, interactions, side effects..."
                rows={1}
                disabled={isLoading}
                aria-label="Type your message"
            />
            <button
                className={`chat-input__send ${hasText ? 'chat-input__send--active' : ''}`}
                onClick={handleSubmit}
                disabled={!hasText || isLoading}
                aria-label="Send message"
            >
                <HiOutlinePaperAirplane size={18} />
            </button>
        </div>
    )
}

export default ChatInput
