import { useRef, useEffect, useCallback } from 'react'
import { HiOutlineBars3, HiOutlineArrowRightOnRectangle } from 'react-icons/hi2'
import MessageBubble from '../MessageBubble/MessageBubble'
import ChatInput from '../ChatInput/ChatInput'
import WelcomeScreen from '../WelcomeScreen/WelcomeScreen'
import TypingIndicator from '../TypingIndicator/TypingIndicator'
import './ChatWindow.css'

function ChatWindow({
    messages,
    onSendMessage,
    isLoading,
    onToggleSidebar,
    onShowAuth,
    user,
    onLogout,
    onEditMessage,
    onResendMessage,
}) {
    const messagesEndRef = useRef(null)
    const messagesContainerRef = useRef(null)
    const isNearBottomRef = useRef(true)
    const prevMessagesLenRef = useRef(0)

    // Determine if the user is near the bottom of the scroll area
    const checkIfNearBottom = useCallback(() => {
        const el = messagesContainerRef.current
        if (!el) return true
        // "Near bottom" = within 150px of the bottom edge
        const threshold = 150
        return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
    }, [])

    // Track scroll position to know if user has scrolled up
    const handleScroll = useCallback(() => {
        isNearBottomRef.current = checkIfNearBottom()
    }, [checkIfNearBottom])

    // Auto-scroll only when:
    // 1. A new user message was just sent (messages length increased and last msg is user)
    // 2. User is already near the bottom while AI is streaming
    useEffect(() => {
        const newLen = messages.length
        const prevLen = prevMessagesLenRef.current
        const lastMsg = messages[newLen - 1]

        // New user message just added → always scroll to bottom
        if (newLen > prevLen && lastMsg?.role === 'user') {
            isNearBottomRef.current = true
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
        }
        // Streaming AI content or new AI message → scroll only if near bottom
        else if (isNearBottomRef.current) {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
        }

        prevMessagesLenRef.current = newLen
    }, [messages])

    // Also scroll when loading state starts (typing indicator appears)
    // but only if near bottom
    useEffect(() => {
        if (isLoading && isNearBottomRef.current) {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
        }
    }, [isLoading])

    return (
        <div className="chat-window">
            {/* Header */}
            <header className="chat-window__header">
                <div className="chat-window__header-left">
                    <button className="chat-window__menu-btn" onClick={onToggleSidebar} aria-label="Toggle sidebar">
                        <HiOutlineBars3 size={20} />
                    </button>
                    <div>
                        <div className="chat-window__title">RxChat</div>
                        <div className="chat-window__subtitle">AI Pharmacist</div>
                    </div>
                </div>
                {user ? (
                    <button className="chat-window__header-logout" onClick={onLogout}>
                        <HiOutlineArrowRightOnRectangle size={16} />
                        Logout
                    </button>
                ) : (
                    <div className="chat-window__header-actions">
                        <button className="chat-window__header-signin" onClick={() => onShowAuth('login')}>
                            Sign in
                        </button>
                        <button className="chat-window__header-badge" onClick={() => onShowAuth('register')}>
                            Sign up for free
                        </button>
                    </div>
                )}
            </header>

            {/* Messages */}
            <div
                className="chat-window__messages"
                ref={messagesContainerRef}
                onScroll={handleScroll}
            >
                <div className="chat-window__messages-inner">
                    {messages.length === 0 ? (
                        <WelcomeScreen onSuggestionClick={onSendMessage} />
                    ) : (
                        <>
                            {messages.map((msg, i) => (
                                <MessageBubble
                                    key={msg.id || i}
                                    message={msg}
                                    index={i}
                                    onEdit={onEditMessage}
                                    onResend={onResendMessage}
                                    isLoading={isLoading}
                                />
                            ))}
                            {isLoading && <TypingIndicator />}
                        </>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input */}
            <div className="chat-window__input-area">
                <div className="chat-window__input-wrapper">
                    <ChatInput onSend={onSendMessage} isLoading={isLoading} />
                </div>
            </div>
        </div>
    )
}

export default ChatWindow
