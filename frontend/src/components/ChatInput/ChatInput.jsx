import { useState, useRef, useEffect } from 'react'
import { HiOutlinePaperAirplane, HiOutlineStopCircle } from 'react-icons/hi2'
import './ChatInput.css'

function ChatInput({ onSend, isLoading, onStop, prefillText }) {
    const [text, setText] = useState(prefillText || '')
    const textareaRef = useRef(null)

    useEffect(() => {
        if (prefillText) {
            setTimeout(() => textareaRef.current?.focus(), 0)
        }
    }, [prefillText])

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
                aria-label="Type your message"
            />
            {isLoading ? (
                <button
                    className="chat-input__stop"
                    onClick={onStop}
                    aria-label="Stop generating"
                    title="Stop generating"
                >
                    <HiOutlineStopCircle size={20} />
                </button>
            ) : (
                <button
                    className={`chat-input__send ${hasText ? 'chat-input__send--active' : ''}`}
                    onClick={handleSubmit}
                    disabled={!hasText}
                    aria-label="Send message"
                    title="Send message"
                >
                    <HiOutlinePaperAirplane size={18} />
                </button>
            )}
        </div>
    )
}

export default ChatInput
