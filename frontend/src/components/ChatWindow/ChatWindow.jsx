import { Fragment, useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { HiOutlineBars3, HiOutlineChevronDown, HiOutlinePencilSquare } from 'react-icons/hi2'
import MessageBubble from '../MessageBubble/MessageBubble'
import ChatInput from '../ChatInput/ChatInput'
import DateSeparator from '../DateSeparator/DateSeparator'
import WelcomeScreen from '../WelcomeScreen/WelcomeScreen'
import { PRODUCT } from '../../config/product'
import { getSessionContextChips } from '../../utils/sessionContext'
import './ChatWindow.css'

function getMessageDomId(message, index) {
    const rawId = message._clientKey ?? message.id ?? index
    return `msg-${String(rawId).replace(/[^A-Za-z0-9_-]/g, '-')}`
}

function getMessageRenderKey(message, index) {
    return message._clientKey ?? message.id ?? index
}

function getMessageDateKey(message) {
    if (!message?.created_at) return ''
    const date = new Date(message.created_at)
    if (Number.isNaN(date.getTime())) return ''
    return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

function getMessagePreview(message) {
    const preview = String(message?.content || '').replace(/\s+/g, ' ').trim() || 'Message'
    if (preview.length <= 50) return preview
    return `${preview.slice(0, 50)}...`
}

function getSubmittedUserMessageToken(message) {
    if (message?.role !== 'user') return ''
    const id = String(message.id || '')
    if (message._pendingEdit) return `edit-${message._pendingEdit}`
    if (message._pending || id.startsWith('pending-user-')) {
        return String(message._clientKey || message.id || '')
    }
    return ''
}

function ChatWindow({
    conversationId,
    messages,
    onSendMessage,
    isLoading,
    isLoadingMessages,
    onToggleSidebar,
    onEditMessage,
    onResendMessage,
    onMessageVariantChange,
    onStopGeneration,
    sessionContext,
    onEditSessionContext,
}) {
    const messagesEndRef = useRef(null)
    const messagesContainerRef = useRef(null)
    const isNearBottomRef = useRef(true)
    const prevMessagesLenRef = useRef(0)
    const lastAutoScrolledUserIdRef = useRef(null)
    const pendingConversationScrollRef = useRef(null)
    const hasActiveStreamRef = useRef(false)
    const hasPendingUserMessageRef = useRef(false)
    const [prefillText, setPrefillText] = useState('')
    const [prefillKey, setPrefillKey] = useState(0)
    const [showScrollButton, setShowScrollButton] = useState(false)

    const isWelcome = !isLoadingMessages && messages.length === 0
    const contextChips = getSessionContextChips(sessionContext)
    const hasActiveStream = messages.some((msg) => msg.role === 'assistant' && msg._streaming)
    const hasPendingUserMessage = messages.some((msg) => Boolean(getSubmittedUserMessageToken(msg)))

    useEffect(() => {
        hasActiveStreamRef.current = hasActiveStream
        hasPendingUserMessageRef.current = hasPendingUserMessage
    }, [hasActiveStream, hasPendingUserMessage])

    const userMessageNavItems = useMemo(() => (
        messages
            .map((msg, index) => ({
                id: getMessageDomId(msg, index),
                preview: getMessagePreview(msg),
                role: msg.role,
            }))
            .filter((item) => item.role === 'user')
    ), [messages])

    const showMinimap = userMessageNavItems.length > 2 && !isWelcome && !isLoadingMessages

    const handleSuggestionClick = useCallback((text) => {
        setPrefillKey((current) => current + 1)
        setPrefillText(text)
    }, [])

    const checkIfNearBottom = useCallback(() => {
        const el = messagesContainerRef.current
        if (!el) return true
        const threshold = 150
        return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
    }, [])

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
        const messageIndex = messages.findIndex((item) => (
            item.id ? item.id === message.id : item === message
        ))
        if (messageIndex === -1) return
        const messageDomId = getMessageDomId(message, messageIndex)
        const scroll = (behavior = 'smooth') => {
            const container = messagesContainerRef.current
            const element = document.getElementById(messageDomId)
            if (!container || !element) return

            const containerRect = container.getBoundingClientRect()
            const elementRect = element.getBoundingClientRect()
            const targetTop = (
                container.scrollTop
                + elementRect.top
                - containerRect.top
                - (container.clientHeight * 0.22)
            )

            container.scrollTo({
                top: Math.max(0, targetTop),
                behavior,
            })
        }
        scroll()
        requestAnimationFrame(() => scroll())
        window.setTimeout(() => scroll('auto'), 160)
        isNearBottomRef.current = false
    }, [messages])

    useEffect(() => {
        const sentUserMessage = [...messages].reverse().find((msg) => getSubmittedUserMessageToken(msg))
        const sentToken = getSubmittedUserMessageToken(sentUserMessage)

        if (sentUserMessage && sentToken && sentToken !== lastAutoScrolledUserIdRef.current) {
            lastAutoScrolledUserIdRef.current = sentToken
            scrollSentMessageToTop(sentUserMessage)
        }

        prevMessagesLenRef.current = messages.length
    }, [messages, scrollSentMessageToTop])

    useEffect(() => {
        lastAutoScrolledUserIdRef.current = null
        prevMessagesLenRef.current = messages.length
        pendingConversationScrollRef.current = conversationId
            && !hasActiveStreamRef.current
            && !hasPendingUserMessageRef.current
            ? conversationId
            : null
    }, [conversationId, messages.length])

    useEffect(() => {
        if (!conversationId || pendingConversationScrollRef.current !== conversationId) return
        if (isLoadingMessages || !messages.length || hasActiveStream || hasPendingUserMessage) return

        const scroll = () => {
            scrollToBottom('auto')
            setShowScrollButton(false)
        }

        requestAnimationFrame(scroll)
        window.setTimeout(scroll, 80)
        pendingConversationScrollRef.current = null
        prevMessagesLenRef.current = messages.length
    }, [
        conversationId,
        hasActiveStream,
        hasPendingUserMessage,
        isLoadingMessages,
        messages.length,
        scrollToBottom,
    ])

    const findResendMessageId = (messageIndex) => {
        for (let i = messageIndex - 1; i >= 0; i -= 1) {
            const candidate = messages[i]
            if (candidate.role === 'user' && candidate.id) {
                return candidate.id
            }
        }
        return null
    }

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
                        <Fragment key={getMessageRenderKey(msg, i)}>
                            {shouldShowDateSeparator && <DateSeparator date={msg.created_at} />}
                            <div id={messageDomId} className="chat-window__message-anchor">
                                <MessageBubble
                                    message={msg}
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
            </>
        )
    }

    return (
        <div className="chat-window">
            <header className="chat-window__header">
                <div className="chat-window__header-left">
                    <button className="chat-window__menu-btn" onClick={onToggleSidebar} aria-label="Toggle sidebar">
                        <HiOutlineBars3 size={20} />
                    </button>
                    <div>
                        <div className="chat-window__title">{PRODUCT.name}</div>
                        <div className="chat-window__subtitle">Hospital medication assistant</div>
                    </div>
                </div>

                <div className="chat-window__context" aria-label="Session context">
                    <div className="chat-window__context-chips">
                        {contextChips.map((chip) => (
                            <span className="chat-window__context-chip" key={chip}>{chip}</span>
                        ))}
                    </div>
                    <button
                        type="button"
                        className="chat-window__context-edit"
                        onClick={onEditSessionContext}
                        aria-label="Edit session context"
                        title="Edit session context"
                    >
                        <HiOutlinePencilSquare size={18} />
                    </button>
                </div>
            </header>

            <div className="chat-window__messages-area">
                <div
                    className="chat-window__messages"
                    ref={messagesContainerRef}
                    onScroll={handleScroll}
                >
                    <div className={`chat-window__messages-inner ${hasActiveStream ? 'chat-window__messages-inner--active-stream' : ''}`}>
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
