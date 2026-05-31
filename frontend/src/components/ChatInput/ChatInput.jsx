import { useState, useRef, useEffect } from 'react'
import {
    HiOutlinePaperAirplane,
    HiOutlineStopCircle,
} from 'react-icons/hi2'
import './ChatInput.css'

function ChatInput({ onSend, isLoading, onStop, prefillText }) {
    const [text, setText] = useState(prefillText || '')
    const [error, setError] = useState('')
    const textareaRef = useRef(null)

    useEffect(() => {
        if (prefillText) {
            setTimeout(() => textareaRef.current?.focus(), 0)
        }
    }, [prefillText])

    useEffect(() => {
        if (textareaRef.current) {
            const baseHeight = 44
            const maxHeight = 150
            textareaRef.current.style.height = 'auto'
            const nextHeight = Math.min(Math.max(textareaRef.current.scrollHeight, baseHeight), maxHeight)
            textareaRef.current.style.height = `${nextHeight}px`
            textareaRef.current.style.overflowY = textareaRef.current.scrollHeight > maxHeight ? 'auto' : 'hidden'
        }
    }, [text])

    const handleSubmit = () => {
        const trimmed = text.trim()
        if (!trimmed || isLoading) return
        onSend({
            text: trimmed,
        })
        setText('')
        setError('')
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        }
    }

    const canSend = text.trim().length > 0

    return (
        <div className="chat-input-shell">
            <div className="chat-input">
                {error && <div className="chat-input__error" role="alert">{error}</div>}

                <div className="chat-input__composer">
                    <textarea
                        ref={textareaRef}
                        className="chat-input__textarea"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask about medications..."
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
                            className={`chat-input__send ${canSend ? 'chat-input__send--active' : ''}`}
                            onClick={handleSubmit}
                            disabled={!canSend}
                            aria-label="Send message"
                            title="Send message"
                        >
                            <HiOutlinePaperAirplane size={18} />
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

export default ChatInput
