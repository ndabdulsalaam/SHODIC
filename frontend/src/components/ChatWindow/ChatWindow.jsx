import { useRef, useEffect } from 'react'
import { HiOutlineBars3 } from 'react-icons/hi2'
import MessageBubble from '../MessageBubble/MessageBubble'
import ChatInput from '../ChatInput/ChatInput'
import WelcomeScreen from '../WelcomeScreen/WelcomeScreen'
import TypingIndicator from '../TypingIndicator/TypingIndicator'
import './ChatWindow.css'

function ChatWindow({ messages, onSendMessage, isLoading, onToggleSidebar, onShowAuth, user }) {
    const messagesEndRef = useRef(null)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, isLoading])

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
                        <div className="chat-window__subtitle">AI Pharmacy Assistant</div>
                    </div>
                </div>
                {!user && (
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
            <div className="chat-window__messages">
                <div className="chat-window__messages-inner">
                    {messages.length === 0 ? (
                        <WelcomeScreen onSuggestionClick={onSendMessage} />
                    ) : (
                        <>
                            {messages.map((msg, i) => (
                                <MessageBubble key={i} message={msg} index={i} />
                            ))}
                            {isLoading && <TypingIndicator />}
                        </>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Disclaimer */}
            <div className="chat-window__disclaimer">
                <strong>⚠️ Disclaimer:</strong> RxChat provides general health information only. Always consult a qualified healthcare professional for medical advice.
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
