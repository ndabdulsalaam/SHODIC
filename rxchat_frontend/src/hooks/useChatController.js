import { useCallback, useEffect, useRef, useState } from 'react'
import { apiRequest, apiUrl, readApiResponse } from '../utils/api'
import { cacheAuthUser, readCachedAuthUser } from '../utils/authCache'
import { readSseStream } from '../utils/sse'
import { productApiPath } from '../config/product'

const DEFAULT_STREAM_STATUS_LABEL = 'Checking sources'

function normalizeSendPayload(payload) {
    if (typeof payload === 'string') {
        return { text: payload }
    }
    return {
        text: payload?.text || '',
    }
}

function getConversationTimestamp(conversation) {
    const rawDate = conversation?.updated_at || conversation?.created_at || ''
    const timestamp = Date.parse(rawDate)
    return Number.isNaN(timestamp) ? 0 : timestamp
}

function sortConversationsByUpdated(conversationsToSort) {
    return [...conversationsToSort].sort((a, b) => getConversationTimestamp(b) - getConversationTimestamp(a))
}

function preserveConversationFields(conversation, fallback = {}) {
    return {
        id: conversation.id,
        title: conversation.title,
        created_at: conversation.created_at ?? fallback.created_at ?? null,
        updated_at: conversation.updated_at ?? fallback.updated_at ?? conversation.created_at ?? fallback.created_at ?? null,
        message_count: conversation.message_count ?? fallback.message_count ?? 0,
        messages: conversation.messages ?? fallback.messages ?? [],
        _loaded: conversation._loaded ?? fallback._loaded ?? false,
    }
}

function isAbortError(error) {
    return error?.name === 'AbortError'
}

function createAssistantPlaceholder(id) {
    return {
        id,
        _clientKey: id,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString(),
        _streaming: true,
        _statusLabel: DEFAULT_STREAM_STATUS_LABEL,
    }
}

async function assertStreamingResponse(response) {
    if (response.ok) return

    const payload = await readApiResponse(response)
    throw new Error(payload?.error || payload?.message || `API error: ${response.status}`)
}

export default function useChatController() {
    const [conversations, setConversations] = useState([])
    const [activeConversationId, setActiveConversationId] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
    const [showAuthModal, setShowAuthModal] = useState(false)
    const [authMode, setAuthMode] = useState('login')
    const [user, setUser] = useState(() => readCachedAuthUser())
    const [settingsOpen, setSettingsOpen] = useState(false)
    const [loadingConversationId, setLoadingConversationId] = useState(null)
    const abortControllerRef = useRef(null)
    const conversationsRef = useRef([])
    const editVariantsRef = useRef({})

    useEffect(() => {
        conversationsRef.current = conversations
    }, [conversations])

    const applyConversationMetadata = useCallback((conversationId, metadata = {}) => {
        if (!conversationId) return
        setConversations((prev) => sortConversationsByUpdated(prev.map((conversation) => {
            if (conversation.id !== conversationId) return conversation
            return {
                ...conversation,
                title: metadata.title ?? conversation.title,
                created_at: metadata.created_at ?? conversation.created_at,
                updated_at: metadata.updated_at ?? conversation.updated_at,
                message_count: metadata.message_count ?? conversation.message_count,
            }
        })))
    }, [])

    const updateStreamingMessage = useCallback((conversationId, aiMsg, content, messageId, markComplete = false, statusLabel) => {
        if (!conversationId) return

        const targetKey = aiMsg._clientKey || aiMsg.id
        setConversations((prev) =>
            prev.map((conversation) => {
                if (conversation.id !== conversationId) return conversation

                let foundStreamingMessage = false
                const messages = conversation.messages.map((message) => {
                    if (!message._streaming) return message
                    const messageKey = message._clientKey || message.id
                    if (messageKey !== targetKey) return message

                    foundStreamingMessage = true
                    return {
                        ...message,
                        id: messageId || message.id,
                        content,
                        ...(statusLabel !== undefined ? { _statusLabel: statusLabel } : {}),
                        _streaming: markComplete ? false : message._streaming,
                    }
                })

                if (!foundStreamingMessage && (content || !markComplete)) {
                    messages.push({
                        ...aiMsg,
                        id: messageId || aiMsg.id,
                        content,
                        ...(statusLabel !== undefined ? { _statusLabel: statusLabel } : {}),
                        _streaming: !markComplete,
                    })
                }

                return { ...conversation, messages }
            })
        )
    }, [])

    const removeStreamingMessage = useCallback((conversationId, aiMsg) => {
        if (!conversationId || !aiMsg) return

        const targetKey = aiMsg._clientKey || aiMsg.id
        setConversations((prev) =>
            prev.map((conversation) => {
                if (conversation.id !== conversationId) return conversation
                return {
                    ...conversation,
                    messages: conversation.messages.filter((message) => (
                        (message._clientKey || message.id) !== targetKey
                    )),
                }
            })
        )
    }, [])

    const finishInterruptedStream = useCallback((conversationId, aiMsg, streamingFlusher, aiContent) => {
        if (aiContent) {
            streamingFlusher?.finalize()
            return
        }

        streamingFlusher?.cancel()
        removeStreamingMessage(conversationId, aiMsg)
    }, [removeStreamingMessage])

    const createStreamingFrameFlusher = useCallback((flush) => {
        let frameId = null
        const requestFrame = typeof requestAnimationFrame === 'function'
            ? requestAnimationFrame
            : (callback) => setTimeout(callback, 16)
        const cancelFrame = typeof cancelAnimationFrame === 'function'
            ? cancelAnimationFrame
            : clearTimeout

        return {
            schedule() {
                if (frameId !== null) return
                frameId = requestFrame(() => {
                    frameId = null
                    flush(false)
                })
            },
            finalize() {
                if (frameId !== null) {
                    cancelFrame(frameId)
                    frameId = null
                }
                flush(true)
            },
            cancel() {
                if (frameId !== null) {
                    cancelFrame(frameId)
                    frameId = null
                }
            },
        }
    }, [])

    const decorateVariantMessages = useCallback((messagesToDecorate, groupId, index, total) => (
        messagesToDecorate.map((message, messageIndex) => {
            if (messageIndex !== 0 || message.role !== 'user') return message
            return {
                ...message,
                _variantNavigation: {
                    groupId,
                    index,
                    total,
                },
            }
        })
    ), [])

    const syncActiveVariantMessages = useCallback((groupId, updater) => {
        const group = editVariantsRef.current[groupId]
        if (!group) return
        group.variants[group.activeIndex] = updater(group.variants[group.activeIndex] || [])
    }, [])

    useEffect(() => {
        const checkAuth = async () => {
            try {
                const data = await apiRequest('/auth/me/')
                if (data?.id) {
                    setUser(data)
                    cacheAuthUser(data)
                } else {
                    setUser(null)
                    cacheAuthUser(null)
                }
            } catch { /* not logged in */ }
        }
        checkAuth()
    }, [])

    useEffect(() => {
        const loadConversations = async () => {
            try {
                const data = await apiRequest(productApiPath('/conversations/'))
                setConversations(sortConversationsByUpdated(data.map((conversation) => (
                    preserveConversationFields(conversation)
                ))))
            } catch { /* offline or error */ }
        }
        loadConversations()
    }, [user])

    const handleShowAuth = useCallback((mode = 'login') => {
        setAuthMode(mode)
        setShowAuthModal(true)
    }, [])

    const handleLogout = useCallback(async () => {
        try {
            await apiRequest('/auth/logout/', { method: 'POST' })
        } catch { /* ignore */ }
        setUser(null)
        cacheAuthUser(null)
        setConversations([])
        setActiveConversationId(null)
    }, [])

    const handleLogin = useCallback((userData) => {
        setUser(userData)
        cacheAuthUser(userData)
    }, [])

    const activeConversation = conversations.find((conversation) => conversation.id === activeConversationId)
    const messages = activeConversation?.messages || []

    const loadConversationMessages = useCallback(async (conversationId) => {
        const conversation = conversationsRef.current.find((item) => item.id === conversationId)
        if (conversation && conversation._loaded) {
            setLoadingConversationId(null)
            return
        }

        setLoadingConversationId(conversationId)
        try {
            const data = await apiRequest(productApiPath(`/conversations/${conversationId}/`))
            setConversations((prev) => prev.map((item) =>
                item.id === conversationId
                    ? preserveConversationFields({
                        ...item,
                        ...data,
                        messages: data.messages || [],
                        _loaded: true,
                    }, item)
                    : item
            ))
        } catch { /* error */ }
        setLoadingConversationId(null)
    }, [])

    const handleSendMessage = useCallback(async (payload) => {
        const { text } = normalizeSendPayload(payload)
        const trimmedText = text.trim()
        if (!trimmedText) return
        const localTitleSource = trimmedText || 'New Conversation'

        const requestConversationId = activeConversationId
        let actualConvId = requestConversationId || `pending-conversation-${Date.now()}`
        const messageCreatedAt = new Date().toISOString()
        const tempUserMessageId = `pending-user-${Date.now()}`
        const tempAssistantMessageId = `pending-assistant-${Date.now()}`

        const userMsg = {
            id: tempUserMessageId,
            _clientKey: tempUserMessageId,
            role: 'user',
            content: trimmedText,
            attachments: [],
            created_at: messageCreatedAt,
            _pending: true,
        }
        const aiMsg = createAssistantPlaceholder(tempAssistantMessageId)

        if (requestConversationId) {
            setConversations((prev) =>
                sortConversationsByUpdated(prev.map((conversation) =>
                    conversation.id === requestConversationId
                        ? {
                            ...conversation,
                            messages: [...conversation.messages, userMsg, aiMsg],
                            updated_at: userMsg.created_at,
                            message_count: (conversation.message_count ?? conversation.messages.length) + 1,
                        }
                        : conversation
                ))
            )
        } else {
            const optimisticTitle = localTitleSource.length > 35
                ? `${localTitleSource.slice(0, 35)}...`
                : localTitleSource
            setActiveConversationId(actualConvId)
            setConversations((prev) => sortConversationsByUpdated([
                preserveConversationFields({
                    id: actualConvId,
                    title: optimisticTitle,
                    created_at: messageCreatedAt,
                    updated_at: messageCreatedAt,
                    message_count: 1,
                    messages: [userMsg, aiMsg],
                    _loaded: true,
                }),
                ...prev,
            ]))
        }

        setIsLoading(true)
        const controller = new AbortController()
        abortControllerRef.current = controller
        let streamingFlusher = null
        let aiContent = ''
        let aiMessageId = null
        let hasReceivedText = false

        try {
            const response = await fetch(apiUrl(productApiPath('/send/')), {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: trimmedText,
                    ...(requestConversationId ? { conversation_id: requestConversationId } : {}),
                }),
                signal: controller.signal,
            })

            await assertStreamingResponse(response)

            streamingFlusher = createStreamingFrameFlusher((markComplete) => {
                updateStreamingMessage(
                    actualConvId,
                    aiMsg,
                    aiContent,
                    aiMessageId,
                    markComplete,
                    aiContent ? null : undefined,
                )
            })

            const handleStreamMetadata = (parsed) => {
                const previousConvId = actualConvId
                if (parsed.message_id) {
                    aiMessageId = parsed.message_id
                }
                if (parsed.conversation_id) {
                    actualConvId = parsed.conversation_id
                }

                const nextConvId = actualConvId
                const conversationUpdatedAt = parsed.conversation_updated_at || new Date().toISOString()
                const assistantKey = aiMsg._clientKey || aiMsg.id

                setConversations((prev) =>
                    sortConversationsByUpdated(prev.map((conversation) => {
                        if (conversation.id !== previousConvId && conversation.id !== nextConvId) {
                            return conversation
                        }

                        const nextMessages = conversation.messages.map((message) => {
                            const messageKey = message._clientKey || message.id
                            if (messageKey === tempUserMessageId) {
                                return {
                                    ...message,
                                    id: parsed.user_message_id || message.id,
                                    _pending: parsed.user_message_id ? false : message._pending,
                                }
                            }

                            if (messageKey === assistantKey && parsed.message_id) {
                                return { ...message, id: parsed.message_id }
                            }

                            return message
                        })

                        return {
                            ...conversation,
                            id: nextConvId,
                            title: parsed.conversation_title ?? conversation.title,
                            created_at: parsed.conversation_created_at ?? conversation.created_at,
                            updated_at: conversationUpdatedAt,
                            messages: nextMessages,
                            _loaded: true,
                        }
                    }))
                )

                if (previousConvId !== nextConvId) {
                    setActiveConversationId((current) => (
                        current === previousConvId ? nextConvId : current
                    ))
                }
            }

            await readSseStream(response, {
                onMeta: handleStreamMetadata,
                onDone: handleStreamMetadata,
                onStatus: (status) => {
                    if (!hasReceivedText) {
                        updateStreamingMessage(actualConvId, aiMsg, aiContent, aiMessageId, false, status.label)
                    }
                },
                onText: (textChunk) => {
                    if (!textChunk) return
                    hasReceivedText = true
                    aiContent += textChunk
                    streamingFlusher.schedule()
                },
            })

            streamingFlusher.finalize()
        } catch (err) {
            if (isAbortError(err)) {
                finishInterruptedStream(actualConvId, aiMsg, streamingFlusher, aiContent)
                return
            }

            streamingFlusher?.cancel()
            console.error('Send message error:', err)
            const errorMsg = {
                role: 'assistant',
                content: 'Sorry, I encountered an error processing your request. Please try again.',
                created_at: new Date().toISOString(),
                _error: true,
            }
            setConversations((prev) =>
                prev.map((conversation) =>
                    conversation.id === actualConvId
                        ? { ...conversation, messages: [...conversation.messages.filter((message) => !message._streaming), errorMsg] }
                        : conversation
                )
            )
        } finally {
            abortControllerRef.current = null
            setIsLoading(false)
        }
    }, [activeConversationId, createStreamingFrameFlusher, finishInterruptedStream, updateStreamingMessage])

    const handleNewChat = useCallback(() => {
        setActiveConversationId(null)
        setSidebarOpen(false)
    }, [])

    const handleSelectChat = useCallback((id) => {
        setActiveConversationId(id)
        setSidebarOpen(false)
        loadConversationMessages(id)
    }, [loadConversationMessages])

    const handleDeleteChat = useCallback(async (id) => {
        try {
            await apiRequest(productApiPath(`/conversations/${id}/delete/`), {
                method: 'DELETE',
            })
        } catch { /* ignore */ }
        setConversations((prev) => prev.filter((conversation) => conversation.id !== id))
        if (activeConversationId === id) {
            setActiveConversationId(null)
        }
    }, [activeConversationId])

    const handleRenameChat = useCallback(async (id, newTitle) => {
        try {
            await apiRequest(productApiPath(`/conversations/${id}/rename/`), {
                method: 'PATCH',
                body: JSON.stringify({ title: newTitle }),
            })
        } catch { /* ignore */ }
        setConversations((prev) =>
            prev.map((conversation) => (conversation.id === id ? { ...conversation, title: newTitle } : conversation))
        )
    }, [])

    const handleEditMessage = useCallback(async (messageId, newContent) => {
        if (!activeConversationId) return
        const conversationSnapshot = conversationsRef.current.find((conversation) => conversation.id === activeConversationId)
        const messageIndex = conversationSnapshot?.messages.findIndex((message) => message.id === messageId) ?? -1
        if (!conversationSnapshot || messageIndex === -1) return

        const existingTail = conversationSnapshot.messages.slice(messageIndex)
        const existingGroup = editVariantsRef.current[messageId]
        const variantGroup = existingGroup || {
            conversationId: activeConversationId,
            variants: [existingTail],
            activeIndex: 0,
        }

        if (existingGroup) {
            variantGroup.variants[variantGroup.activeIndex] = existingTail
        }

        const newVariantIndex = variantGroup.variants.length
        const editedUserMessage = {
            ...existingTail[0],
            content: newContent,
            updated_at: new Date().toISOString(),
            _pendingEdit: `pending-edit-${Date.now()}`,
        }
        const tempAssistantMessageId = `pending-assistant-${Date.now()}`
        const aiMsg = createAssistantPlaceholder(tempAssistantMessageId)

        variantGroup.variants.push([editedUserMessage, aiMsg])
        variantGroup.activeIndex = newVariantIndex
        editVariantsRef.current[messageId] = variantGroup

        setIsLoading(true)
        const controller = new AbortController()
        abortControllerRef.current = controller
        let streamingFlusher = null
        let aiContent = ''
        let aiMessageId = null
        let hasReceivedText = false

        const clearEditedMessagePending = () => {
            setConversations((prev) =>
                prev.map((conversation) => {
                    if (conversation.id !== activeConversationId) return conversation
                    return {
                        ...conversation,
                        messages: conversation.messages.map((message) => (
                            message.id === messageId
                                ? { ...message, _pendingEdit: false }
                                : message
                        )),
                    }
                })
            )
            syncActiveVariantMessages(messageId, (messagesForVariant) => (
                messagesForVariant.map((message) => (
                    message.id === messageId
                        ? { ...message, _pendingEdit: false }
                        : message
                ))
            ))
        }

        setConversations((prev) =>
            sortConversationsByUpdated(prev.map((conversation) => {
                if (conversation.id !== activeConversationId) return conversation
                const index = conversation.messages.findIndex((message) => message.id === messageId)
                if (index === -1) return conversation
                const prefix = conversation.messages.slice(0, index)
                const decoratedVariant = decorateVariantMessages(
                    variantGroup.variants[newVariantIndex],
                    messageId,
                    newVariantIndex,
                    variantGroup.variants.length,
                )
                return { ...conversation, messages: [...prefix, ...decoratedVariant], updated_at: editedUserMessage.updated_at }
            }))
        )

        try {
            const response = await fetch(apiUrl(productApiPath(`/messages/${messageId}/`)), {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newContent }),
                signal: controller.signal,
            })

            await assertStreamingResponse(response)

            streamingFlusher = createStreamingFrameFlusher((markComplete) => {
                updateStreamingMessage(
                    activeConversationId,
                    aiMsg,
                    aiContent,
                    aiMessageId,
                    markComplete,
                    aiContent ? null : undefined,
                )
                syncActiveVariantMessages(messageId, (messagesForVariant) => (
                    messagesForVariant.map((message) => (
                        message._streaming
                            ? {
                                ...message,
                                id: aiMessageId || message.id,
                                content: aiContent,
                                _statusLabel: aiContent ? null : message._statusLabel,
                                _streaming: markComplete ? false : message._streaming,
                            }
                            : message
                    ))
                ))
            })

            const handleStreamMetadata = (parsed) => {
                if (parsed.conversation_id && parsed.conversation_updated_at) {
                    applyConversationMetadata(parsed.conversation_id, {
                        updated_at: parsed.conversation_updated_at,
                    })
                }
                if (parsed.edited_message_id) clearEditedMessagePending()
                if (parsed.message_id) aiMessageId = parsed.message_id
            }

            await readSseStream(response, {
                onMeta: handleStreamMetadata,
                onDone: handleStreamMetadata,
                onStatus: (status) => {
                    if (!hasReceivedText) {
                        updateStreamingMessage(activeConversationId, aiMsg, aiContent, aiMessageId, false, status.label)
                        syncActiveVariantMessages(messageId, (messagesForVariant) => (
                            messagesForVariant.map((message) => (
                                message._streaming ? { ...message, _statusLabel: status.label } : message
                            ))
                        ))
                    }
                },
                onText: (textChunk) => {
                    if (!textChunk) return
                    hasReceivedText = true
                    aiContent += textChunk
                    streamingFlusher.schedule()
                },
            })
            streamingFlusher.finalize()
        } catch (err) {
            if (isAbortError(err)) {
                finishInterruptedStream(activeConversationId, aiMsg, streamingFlusher, aiContent)
                if (!aiContent) {
                    const targetKey = aiMsg._clientKey || aiMsg.id
                    syncActiveVariantMessages(messageId, (messagesForVariant) => (
                        messagesForVariant.filter((message) => (message._clientKey || message.id) !== targetKey)
                    ))
                }
                return
            }

            streamingFlusher?.cancel()
            removeStreamingMessage(activeConversationId, aiMsg)
            const targetKey = aiMsg._clientKey || aiMsg.id
            syncActiveVariantMessages(messageId, (messagesForVariant) => (
                messagesForVariant.filter((message) => (message._clientKey || message.id) !== targetKey)
            ))
            console.error('Edit message error:', err)
        } finally {
            clearEditedMessagePending()
            abortControllerRef.current = null
            setIsLoading(false)
        }
    }, [activeConversationId, applyConversationMetadata, createStreamingFrameFlusher, decorateVariantMessages, finishInterruptedStream, removeStreamingMessage, syncActiveVariantMessages, updateStreamingMessage])

    const handleResendMessage = useCallback(async (messageId) => {
        if (!activeConversationId) return
        setIsLoading(true)
        const controller = new AbortController()
        abortControllerRef.current = controller
        let streamingFlusher = null
        let aiContent = ''
        let aiMessageId = null
        const tempAssistantMessageId = `pending-assistant-${Date.now()}`
        const aiMsg = createAssistantPlaceholder(tempAssistantMessageId)
        let hasReceivedText = false
        const resendUpdatedAt = new Date().toISOString()

        setConversations((prev) =>
            sortConversationsByUpdated(prev.map((conversation) => {
                if (conversation.id !== activeConversationId) return conversation
                const index = conversation.messages.findIndex((message) => message.id === messageId)
                if (index === -1) return conversation
                return { ...conversation, messages: [...conversation.messages.slice(0, index + 1), aiMsg], updated_at: resendUpdatedAt }
            }))
        )

        try {
            const response = await fetch(apiUrl(productApiPath(`/messages/${messageId}/resend/`)), {
                method: 'POST',
                credentials: 'include',
                signal: controller.signal,
            })

            await assertStreamingResponse(response)

            streamingFlusher = createStreamingFrameFlusher((markComplete) => {
                updateStreamingMessage(
                    activeConversationId,
                    aiMsg,
                    aiContent,
                    aiMessageId,
                    markComplete,
                    aiContent ? null : undefined,
                )
            })

            const handleStreamMetadata = (parsed) => {
                if (parsed.conversation_id && parsed.conversation_updated_at) {
                    applyConversationMetadata(parsed.conversation_id, {
                        updated_at: parsed.conversation_updated_at,
                    })
                }
                if (parsed.message_id) aiMessageId = parsed.message_id
            }

            await readSseStream(response, {
                onMeta: handleStreamMetadata,
                onDone: handleStreamMetadata,
                onStatus: (status) => {
                    if (!hasReceivedText) {
                        updateStreamingMessage(activeConversationId, aiMsg, aiContent, aiMessageId, false, status.label)
                    }
                },
                onText: (textChunk) => {
                    if (!textChunk) return
                    hasReceivedText = true
                    aiContent += textChunk
                    streamingFlusher.schedule()
                },
            })
            streamingFlusher.finalize()
        } catch (err) {
            if (isAbortError(err)) {
                finishInterruptedStream(activeConversationId, aiMsg, streamingFlusher, aiContent)
                return
            }

            streamingFlusher?.cancel()
            removeStreamingMessage(activeConversationId, aiMsg)
            console.error('Resend message error:', err)
        } finally {
            abortControllerRef.current = null
            setIsLoading(false)
        }
    }, [activeConversationId, applyConversationMetadata, createStreamingFrameFlusher, finishInterruptedStream, removeStreamingMessage, updateStreamingMessage])

    const handleMessageVariantChange = useCallback((groupId, nextIndex) => {
        const group = editVariantsRef.current[groupId]
        if (!group || nextIndex < 0 || nextIndex >= group.variants.length) return

        group.activeIndex = nextIndex
        setConversations((prev) =>
            prev.map((conversation) => {
                if (conversation.id !== group.conversationId) return conversation
                const messageIndex = conversation.messages.findIndex((message) => message.id === groupId)
                if (messageIndex === -1) return conversation

                const prefix = conversation.messages.slice(0, messageIndex)
                const decoratedVariant = decorateVariantMessages(
                    group.variants[nextIndex],
                    groupId,
                    nextIndex,
                    group.variants.length,
                )

                return { ...conversation, messages: [...prefix, ...decoratedVariant] }
            })
        )
    }, [decorateVariantMessages])

    const handleStopGeneration = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort()
            abortControllerRef.current = null
        }
    }, [])

    return {
        activeConversationId,
        authMode,
        conversations,
        handleDeleteChat,
        handleEditMessage,
        handleLogin,
        handleLogout,
        handleMessageVariantChange,
        handleNewChat,
        handleRenameChat,
        handleResendMessage,
        handleSelectChat,
        handleSendMessage,
        handleShowAuth,
        handleStopGeneration,
        isLoading,
        isLoadingMessages: loadingConversationId === activeConversationId && loadingConversationId !== null,
        messages,
        setSettingsOpen,
        setShowAuthModal,
        setSidebarCollapsed,
        setSidebarOpen,
        settingsOpen,
        showAuthModal,
        sidebarCollapsed,
        sidebarOpen,
        user,
    }
}
