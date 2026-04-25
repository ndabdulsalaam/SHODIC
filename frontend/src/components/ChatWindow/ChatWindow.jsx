import { Fragment, useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { HiOutlineBars3, HiOutlineArrowRightOnRectangle, HiOutlineChevronDown } from 'react-icons/hi2'
import MessageBubble from '../MessageBubble/MessageBubble'
import ChatInput from '../ChatInput/ChatInput'
import DateSeparator from '../DateSeparator/DateSeparator'
import WelcomeScreen from '../WelcomeScreen/WelcomeScreen'
import TypingIndicator from '../TypingIndicator/TypingIndicator'
import './ChatWindow.css'

function getMessageDomId(message, index) {
    const rawId = message.id ?? index
    return `msg-${String(rawId).replace(/[^A-Za-z0-9_-]/g, '-')}`
}

function getMessageDateKey(message) {
    if (!message?.created_at) return ''
    const date = new Date(message.created_at)
    if (Number.isNaN(date.getTime())) return ''
    return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

function getMessagePreview(content) {
    const preview = String(content || '').replace(/\s+/g, ' ').trim()
    if (preview.length <= 50) return preview
    return `${preview.slice(0, 50)}...`
}

function ChatWindow({
    messages,
    onSendMessage,
    isLoading,
    isLoadingMessages,
    onToggleSidebar,
    onShowAuth,
    user,
    onLogout,
    onEditMessage,
    onResendMessage,
    onMessageVariantChange,
    onStopGeneration,
}) {
    const messagesEndRef = useRef(null)
    const messagesContainerRef = useRef(null)
    const isNearBottomRef = useRef(true)
    const prevMessagesLenRef = useRef(0)
    const [prefillText, setPrefillText] = useState('')
    const [prefillKey, setPrefillKey] = useState(0)
    const [showScrollButton, setShowScrollButton] = useState(false)

    const isWelcome = !isLoadingMessages && messages.length === 0

    const userMessageNavItems = useMemo(() => (
        messages
            .map((msg, index) => ({
                id: getMessageDomId(msg, index),
                preview: getMessagePreview(msg.content),
                role: msg.role,
            }))
            .filter((item) => item.role === 'user')
    ), [messages])

    const showMinimap = userMessageNavItems.length > 2 && !isWelcome && !isLoadingMessages

    // Suggestion chip click → pre-fill input for editing
    const handleSuggestionClick = useCallback((text) => {
        setPrefillKey((current) => current + 1)
        setPrefillText(text)
    }, [])

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
        const isNearBottom = checkIfNearBottom()
        isNearBottomRef.current = isNearBottom
        setShowScrollButton(!isNearBottom)
    }, [checkIfNearBottom])

    const scrollToBottom = useCallback((behavior = 'smooth') => {
        messagesEndRef.current?.scrollIntoView({ behavior, block: 'end' })
        isNearBottomRef.current = true
    }, [])

    const handleScrollToBottomClick = useCallback(() => {
        scrollToBottom('smooth')
        setShowScrollButton(false)
    }, [scrollToBottom])

    const scrollToMessage = useCallback((id) => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, [])

    const scrollSentMessageToTop = useCallback((message) => {
        if (!message) return
        const messageIndex = messages.findIndex((item) => item === message)
        if (messageIndex === -1) return
        const messageDomId = getMessageDomId(message, messageIndex)
        document.getElementById(messageDomId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        isNearBottomRef.current = false
    }, [messages])

    // New user messages move to the top of the pane; streamed assistant text does not auto-follow.
    useEffect(() => {
        const newLen = messages.length
        const prevLen = prevMessagesLenRef.current
        const lastMsg = messages[newLen - 1]

        // New user message just added -> place it at the top of the pane.
        if (newLen > prevLen && lastMsg?.role === 'user') {
            scrollSentMessageToTop(lastMsg)
        }

        prevMessagesLenRef.current = newLen
    }, [messages, scrollSentMessageToTop])

    const findResendMessageId = (messageIndex) => {
        for (let i = messageIndex - 1; i >= 0; i -= 1) {
            const candidate = messages[i]
            if (candidate.role === 'user' && candidate.id) {
                return candidate.id
            }
        }
        return null
    }

    // Determine what to render in the messages area
    const renderContent = () => {
        if (isLoadingMessages) {
            return (
                <div className="chat-window__loading-messages">
                    <div className="chat-window__loading-skeleton">
                        <div className="chat-window__skeleton-row chat-window__skeleton-row--right" />
                        <div className="chat-window__skeleton-row chat-window__skeleton-row--left chat-window__skeleton-row--wide" />
                        <div className="chat-window__skeleton-row chat-window__skeleton-row--left" />
                    </div>
                </div>
            )
        }

        if (isWelcome) {
            return (
                <WelcomeScreen
                    onSuggestionClick={handleSuggestionClick}
                    user={user}
                    inputSlot={
                        <ChatInput
                            key={prefillKey}
                            onSend={onSendMessage}
                            isLoading={isLoading}
                            onStop={onStopGeneration}
                            prefillText={prefillText}
                        />
                    }
                />
            )
        }

        return (
            <>
                {messages.map((msg, i) => {
                    const resendMessageId = msg.role === 'assistant' ? findResendMessageId(i) : null
                    const currentDateKey = getMessageDateKey(msg)
                    const previousDateKey = getMessageDateKey(messages[i - 1])
                    const shouldShowDateSeparator = currentDateKey && currentDateKey !== previousDateKey
                    const messageDomId = getMessageDomId(msg, i)

                    return (
                        <Fragment key={msg.id || i}>
                            {shouldShowDateSeparator && <DateSeparator date={msg.created_at} />}
                            <div id={messageDomId} className="chat-window__message-anchor">
                                <MessageBubble
                                    message={msg}
                                    index={i}
                                    onEdit={onEditMessage}
                                    onResend={onResendMessage}
                                    onVariantChange={onMessageVariantChange}
                                    resendMessageId={resendMessageId}
                                    isLoading={isLoading}
                                />
                            </div>
                        </Fragment>
                    )
                })}
                {isLoading && <TypingIndicator />}
            </>
        )
    }

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
            <div className="chat-window__messages-area">
                <div
                    className="chat-window__messages"
                    ref={messagesContainerRef}
                    onScroll={handleScroll}
                >
                    <div className="chat-window__messages-inner">
                        {renderContent()}
                        <div ref={messagesEndRef} />
                    </div>
                </div>

                {showMinimap && (
                    <nav className="chat-window__minimap" aria-label="User message navigation">
                        {userMessageNavItems.map((item, index) => (
                            <button
                                key={`${item.id}-${index}`}
                                className="chat-window__minimap-dot"
                                type="button"
                                onClick={() => scrollToMessage(item.id)}
                                aria-label={`Jump to message: ${item.preview}`}
                            >
                                <span className="chat-window__minimap-tooltip">{item.preview}</span>
                            </button>
                        ))}
                    </nav>
                )}

                {showScrollButton && !isWelcome && !isLoadingMessages && (
                    <button
                        className="chat-window__scroll-bottom"
                        type="button"
                        onClick={handleScrollToBottomClick}
                        aria-label="Scroll to bottom"
                    >
                        <HiOutlineChevronDown size={20} />
                    </button>
                )}
            </div>

            {/* Input – hidden on welcome screen since it's rendered inline */}
            {!isWelcome && (
                <div className="chat-window__input-area">
                    <div className="chat-window__input-wrapper">
                        <ChatInput
                            onSend={onSendMessage}
                            isLoading={isLoading}
                            onStop={onStopGeneration}
                        />
                    </div>
                </div>
            )}
        </div>
    )
}

export default ChatWindow
