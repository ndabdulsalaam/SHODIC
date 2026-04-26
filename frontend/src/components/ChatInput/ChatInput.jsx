import { useState, useRef, useEffect } from 'react'
import {
    HiOutlineCheck,
    HiOutlineMicrophone,
    HiOutlinePaperAirplane,
    HiOutlineStopCircle,
    HiOutlineXMark,
} from 'react-icons/hi2'
import useSpeechRecognition from '../../hooks/useSpeechRecognition'
import './ChatInput.css'

function appendTranscript(existingText, transcript) {
    const addition = transcript.trim()
    if (!addition) return existingText
    const base = existingText.trimEnd()
    return base ? `${base} ${addition}` : addition
}

function ChatInput({ onSend, isLoading, onStop, prefillText }) {
    const [text, setText] = useState(prefillText || '')
    const [error, setError] = useState('')
    const [isDictating, setIsDictating] = useState(false)
    const [dictationTranscript, setDictationTranscript] = useState('')
    const textareaRef = useRef(null)
    const dictationBaseRef = useRef('')
    const {
        isSupported: speechSupported,
        isListening,
        startListening,
        stopListening,
    } = useSpeechRecognition()

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
        if (!trimmed || isLoading || isDictating) return
        onSend({
            text: trimmed,
        })
        setText('')
        setError('')
        if (isListening) stopListening()
        setIsDictating(false)
        setDictationTranscript('')
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        }
    }

    const handleMicClick = () => {
        if (!speechSupported || isLoading) return
        if (isListening) {
            stopListening()
            return
        }
        dictationBaseRef.current = text
        setDictationTranscript('')
        setIsDictating(true)
        setError('')
        startListening((nextTranscript) => {
            setDictationTranscript(nextTranscript)
        })
    }

    const handleCancelDictation = () => {
        stopListening()
        setText(dictationBaseRef.current)
        setDictationTranscript('')
        setIsDictating(false)
        setTimeout(() => textareaRef.current?.focus(), 0)
    }

    const handleConfirmDictation = () => {
        stopListening()
        setText((current) => appendTranscript(current || dictationBaseRef.current, dictationTranscript))
        setDictationTranscript('')
        setIsDictating(false)
        setTimeout(() => textareaRef.current?.focus(), 0)
    }

    const canSend = text.trim().length > 0

    return (
        <div className="chat-input-shell">
            <div className="chat-input">
                {error && <div className="chat-input__error" role="alert">{error}</div>}

                {isDictating ? (
                    <div className="chat-input__dictation" role="group" aria-label="Voice dictation">
                        <button
                            type="button"
                            className="chat-input__dictation-action"
                            onClick={handleCancelDictation}
                            aria-label="Cancel dictation"
                            title="Cancel dictation"
                        >
                            <HiOutlineXMark size={20} />
                        </button>

                        <div className={`chat-input__waveform ${isListening ? 'chat-input__waveform--active' : ''}`} aria-hidden="true">
                            {Array.from({ length: 36 }, (_, index) => (
                                <span key={index} style={{ animationDelay: `${index * -45}ms` }} />
                            ))}
                        </div>

                        <button
                            type="button"
                            className="chat-input__dictation-action chat-input__dictation-action--confirm"
                            onClick={handleConfirmDictation}
                            aria-label="Use dictation"
                            title="Use dictation"
                        >
                            <HiOutlineCheck size={22} />
                        </button>
                    </div>
                ) : (
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

                        {speechSupported && (
                            <button
                                type="button"
                                className="chat-input__icon-btn"
                                onClick={handleMicClick}
                                disabled={isLoading}
                                aria-label="Start dictation"
                                title="Start dictation"
                            >
                                <HiOutlineMicrophone size={20} />
                            </button>
                        )}

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
                )}
            </div>
        </div>
    )
}

export default ChatInput
