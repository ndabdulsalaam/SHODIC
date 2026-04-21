import { useState, useRef, useEffect } from 'react'
import { HiOutlineBars3, HiOutlineArrowRightOnRectangle, HiOutlineChevronDown } from 'react-icons/hi2'
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
    providerDisplay,
    providers,
    activeProvider,
    onProviderChange,
}) {
    const messagesEndRef = useRef(null)
    const [showProviderMenu, setShowProviderMenu] = useState(false)
    const providerMenuRef = useRef(null)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages, isLoading])

    // Close provider menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (providerMenuRef.current && !providerMenuRef.current.contains(e.target)) {
                setShowProviderMenu(false)
            }
        }
        if (showProviderMenu) {
            document.addEventListener('mousedown', handleClickOutside)
        }
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [showProviderMenu])

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
            <div className="chat-window__messages">
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
                    {/* Model selector badge */}
                    {providers && providers.length > 0 && (
                        <div className="chat-window__model-bar" ref={providerMenuRef}>
                            <button
                                className="chat-window__model-badge"
                                onClick={() => setShowProviderMenu((p) => !p)}
                                aria-label="Select AI model"
                                id="model-selector-badge"
                            >
                                <span className="chat-window__model-dot" />
                                <span className="chat-window__model-label">
                                    {providerDisplay || 'Select Model'}
                                </span>
                                <HiOutlineChevronDown size={12} className={`chat-window__model-chevron ${showProviderMenu ? 'chat-window__model-chevron--open' : ''}`} />
                            </button>

                            {showProviderMenu && (
                                <div className="chat-window__model-menu">
                                    {providers.map((p) => (
                                        <button
                                            key={p.slug}
                                            className={`chat-window__model-option ${activeProvider === p.slug ? 'chat-window__model-option--active' : ''}`}
                                            onClick={() => {
                                                onProviderChange(p.slug)
                                                setShowProviderMenu(false)
                                            }}
                                            id={`model-option-${p.slug}`}
                                        >
                                            <span className="chat-window__model-option-name">{p.name}</span>
                                            <span className="chat-window__model-option-desc">{p.model_display}</span>
                                            {activeProvider === p.slug && <span className="chat-window__model-option-check">✓</span>}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export default ChatWindow
