import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { apiRequest, apiUrl, readApiResponse } from '../utils/api'
import { readSseStream } from '../utils/sse'
import { productApiPath } from '../config/product'
import {
    DEFAULT_SESSION_CONTEXT,
    isSessionContextComplete,
    loadLastSessionContext,
    normalizeSessionContext,
    prepareSessionContextPayload,
    saveLastSessionContext,
} from '../utils/sessionContext'

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
        role: conversation.role ?? fallback.role ?? DEFAULT_SESSION_CONTEXT.role,
        subject: conversation.subject ?? fallback.subject ?? DEFAULT_SESSION_CONTEXT.subject,
        patient_sex: conversation.patient_sex ?? fallback.patient_sex ?? DEFAULT_SESSION_CONTEXT.patient_sex,
        pregnancy_status: conversation.pregnancy_status ?? fallback.pregnancy_status ?? DEFAULT_SESSION_CONTEXT.pregnancy_status,
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

function createAssistantErrorMessage(content = 'Sorry, I encountered an error processing your request. Please try again.') {
    const id = `error-assistant-${Date.now()}`
    return {
        id,
        _clientKey: id,
        role: 'assistant',
        content,
        created_at: new Date().toISOString(),
        _error: true,
    }
}

async function assertStreamingResponse(response) {
    if (response.ok) return

    const payload = await readApiResponse(response)
    throw new Error(payload?.error || payload?.message || `API error: ${response.status}`)
}

function useStreamingResponse({ createStreamingFrameFlusher, finishInterruptedStream, updateStreamingMessage }) {
    return useCallback(async ({
        response,
        aiMsg,
        getConversationId,
        onMetadata,
        onStatus,
        onFlush,
        onAbort,
    }) => {
        await assertStreamingResponse(response)

        let streamingFlusher = null
        let aiContent = ''
        let aiMessageId = null
        let hasReceivedText = false
        const snapshot = () => ({ aiContent, aiMessageId, hasReceivedText })

        streamingFlusher = createStreamingFrameFlusher((markComplete) => {
            updateStreamingMessage(
                getConversationId(),
                aiMsg,
                aiContent,
                aiMessageId,
                markComplete,
                aiContent ? null : undefined,
            )
            onFlush?.({ ...snapshot(), markComplete })
        })

        const handleStreamMetadata = (parsed) => {
            if (parsed.message_id) {
                aiMessageId = parsed.message_id
            }
            onMetadata?.(parsed, snapshot())
        }

        try {
            await readSseStream(response, {
                onMeta: handleStreamMetadata,
                onDone: handleStreamMetadata,
                onStatus: (status) => {
                    if (!hasReceivedText) {
                        updateStreamingMessage(getConversationId(), aiMsg, aiContent, aiMessageId, false, status.label)
                        onStatus?.(status, snapshot())
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
            return { ...snapshot(), aborted: false }
        } catch (err) {
            if (isAbortError(err)) {
                finishInterruptedStream(getConversationId(), aiMsg, streamingFlusher, aiContent)
                onAbort?.(snapshot())
                return { ...snapshot(), aborted: true }
            }

            streamingFlusher?.cancel()
            throw err
        }
    }, [createStreamingFrameFlusher, finishInterruptedStream, updateStreamingMessage])
}

export default function useChatController() {
    const [conversations, setConversations] = useState([])
    const [activeConversationId, setActiveConversationId] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
    const [loadingConversationId, setLoadingConversationId] = useState(null)
    const [newConversationContext, setNewConversationContext] = useState(null)
    const [sessionContextDraft, setSessionContextDraft] = useState(() => loadLastSessionContext())
    const [sessionContextModalOpen, setSessionContextModalOpen] = useState(true)
    const [sessionContextError, setSessionContextError] = useState('')
    const [isSavingSessionContext, setIsSavingSessionContext] = useState(false)
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
                role: metadata.role ?? conversation.role,
                subject: metadata.subject ?? conversation.subject,
                patient_sex: metadata.patient_sex ?? conversation.patient_sex,
                pregnancy_status: metadata.pregnancy_status ?? conversation.pregnancy_status,
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

    const streamAssistantResponse = useStreamingResponse({
        createStreamingFrameFlusher,
        finishInterruptedStream,
        updateStreamingMessage,
    })

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
        const loadConversations = async () => {
            try {
                const data = await apiRequest(productApiPath('/conversations/'))
                setConversations(sortConversationsByUpdated(data.map((conversation) => (
                    preserveConversationFields(conversation)
                ))))
            } catch (err) {
                console.warn('Could not load conversations:', err)
            }
        }
        loadConversations()
    }, [])

    const activeConversation = useMemo(() => (
        conversations.find((conversation) => conversation.id === activeConversationId)
    ), [activeConversationId, conversations])
    const messages = activeConversation?.messages || []
    const sessionContext = normalizeSessionContext(activeConversation || newConversationContext || sessionContextDraft)
    const sessionContextModalKey = [
        sessionContextModalOpen ? 'open' : 'closed',
        sessionContextDraft.role,
        sessionContextDraft.subject,
        sessionContextDraft.patient_sex,
        sessionContextDraft.pregnancy_status,
        activeConversationId || 'new',
    ].join(':')
    const canDismissSessionContextModal = Boolean(activeConversationId || newConversationContext)

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
        } catch (err) {
            console.warn('Could not load conversation messages:', err)
        } finally {
            setLoadingConversationId(null)
        }
    }, [])

    const handleOpenSessionContextModal = useCallback(() => {
        setSessionContextDraft(normalizeSessionContext(activeConversation || newConversationContext || sessionContextDraft))
        setSessionContextError('')
        setSessionContextModalOpen(true)
    }, [activeConversation, newConversationContext, sessionContextDraft])

    const handleCloseSessionContextModal = useCallback(() => {
        if (!activeConversationId && !newConversationContext) return
        setSessionContextModalOpen(false)
        setSessionContextError('')
    }, [activeConversationId, newConversationContext])

    const handleSaveSessionContext = useCallback(async (context) => {
        const normalizedContext = normalizeSessionContext(context)
        if (!isSessionContextComplete(normalizedContext)) return

        setSessionContextError('')
        setSessionContextDraft(normalizedContext)
        saveLastSessionContext(normalizedContext)

        if (!activeConversationId) {
            setNewConversationContext(normalizedContext)
            setSessionContextModalOpen(false)
            return
        }

        setIsSavingSessionContext(true)
        try {
            const data = await apiRequest(productApiPath(`/conversations/${activeConversationId}/context/`), {
                method: 'PATCH',
                body: JSON.stringify(prepareSessionContextPayload(normalizedContext)),
            })

            setConversations((prev) => prev.map((conversation) => (
                conversation.id === activeConversationId
                    ? preserveConversationFields({ ...conversation, ...data }, conversation)
                    : conversation
            )))
            setSessionContextModalOpen(false)
        } catch (err) {
            console.warn('Could not update session context:', err)
            setSessionContextError('Could not save session context. Please try again.')
        } finally {
            setIsSavingSessionContext(false)
        }
    }, [activeConversationId])

    const handleSendMessage = useCallback(async (payload) => {
        const { text } = normalizeSendPayload(payload)
        const trimmedText = text.trim()
        if (!trimmedText) return
        const localTitleSource = trimmedText || 'New Conversation'

        const requestConversationId = activeConversationId
        const contextForNewConversation = normalizeSessionContext(newConversationContext)
        if (!requestConversationId && !isSessionContextComplete(contextForNewConversation)) {
            setSessionContextDraft(normalizeSessionContext(newConversationContext || sessionContextDraft))
            setSessionContextModalOpen(true)
            return
        }
        let actualConvId = requestConversationId || `pending-conversation-${Date.now()}`
        const messageCreatedAt = new Date().toISOString()
        const tempUserMessageId = `pending-user-${Date.now()}`
        const tempAssistantMessageId = `pending-assistant-${Date.now()}`

        const userMsg = {
            id: tempUserMessageId,
            _clientKey: tempUserMessageId,
            role: 'user',
            content: trimmedText,
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
                    ...contextForNewConversation,
                    messages: [userMsg, aiMsg],
                    _loaded: true,
                }),
                ...prev,
            ]))
        }

        setIsLoading(true)
        const controller = new AbortController()
        abortControllerRef.current = controller

        try {
            const response = await fetch(apiUrl(productApiPath('/send/')), {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: trimmedText,
                    ...(requestConversationId ? { conversation_id: requestConversationId } : prepareSessionContextPayload(contextForNewConversation)),
                }),
                signal: controller.signal,
            })

            await streamAssistantResponse({
                response,
                aiMsg,
                getConversationId: () => actualConvId,
                onMetadata: (parsed) => {
                    const previousConvId = actualConvId
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
                                role: parsed.role ?? conversation.role,
                                subject: parsed.subject ?? conversation.subject,
                                patient_sex: parsed.patient_sex ?? conversation.patient_sex,
                                pregnancy_status: parsed.pregnancy_status ?? conversation.pregnancy_status,
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
                },
            })
        } catch (err) {
            if (isAbortError(err)) {
                removeStreamingMessage(actualConvId, aiMsg)
                return
            }

            console.error('Send message error:', err)
            const errorMsg = createAssistantErrorMessage()
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
    }, [activeConversationId, newConversationContext, removeStreamingMessage, sessionContextDraft, streamAssistantResponse])

    const handleNewChat = useCallback(() => {
        setActiveConversationId(null)
        setNewConversationContext(null)
        setSessionContextDraft(loadLastSessionContext())
        setSessionContextError('')
        setSessionContextModalOpen(true)
        setSidebarOpen(false)
    }, [])

    const handleSelectChat = useCallback((id) => {
        setActiveConversationId(id)
        setNewConversationContext(null)
        setSessionContextModalOpen(false)
        setSessionContextError('')
        setSidebarOpen(false)
        loadConversationMessages(id)
    }, [loadConversationMessages])

    const handleDeleteChat = useCallback(async (id) => {
        try {
            await apiRequest(productApiPath(`/conversations/${id}/delete/`), {
                method: 'DELETE',
            })
        } catch (err) {
            console.warn('Could not delete conversation:', err)
        }
        setConversations((prev) => prev.filter((conversation) => conversation.id !== id))
        if (activeConversationId === id) {
            setActiveConversationId(null)
            setNewConversationContext(null)
            setSessionContextDraft(loadLastSessionContext())
            setSessionContextModalOpen(true)
        }
    }, [activeConversationId])

    const handleRenameChat = useCallback(async (id, newTitle) => {
        try {
            await apiRequest(productApiPath(`/conversations/${id}/rename/`), {
                method: 'PATCH',
                body: JSON.stringify({ title: newTitle }),
            })
        } catch (err) {
            console.warn('Could not rename conversation:', err)
        }
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

            await streamAssistantResponse({
                response,
                aiMsg,
                getConversationId: () => activeConversationId,
                onMetadata: (parsed) => {
                    if (parsed.conversation_id && parsed.conversation_updated_at) {
                        applyConversationMetadata(parsed.conversation_id, {
                            updated_at: parsed.conversation_updated_at,
                            role: parsed.role,
                            subject: parsed.subject,
                            patient_sex: parsed.patient_sex,
                            pregnancy_status: parsed.pregnancy_status,
                        })
                    }
                    if (parsed.edited_message_id) clearEditedMessagePending()
                },
                onStatus: (status) => {
                    syncActiveVariantMessages(messageId, (messagesForVariant) => (
                        messagesForVariant.map((message) => (
                            message._streaming ? { ...message, _statusLabel: status.label } : message
                        ))
                    ))
                },
                onFlush: ({ aiContent, aiMessageId, markComplete }) => {
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
                },
                onAbort: ({ aiContent }) => {
                    if (!aiContent) {
                        const targetKey = aiMsg._clientKey || aiMsg.id
                        syncActiveVariantMessages(messageId, (messagesForVariant) => (
                            messagesForVariant.filter((message) => (message._clientKey || message.id) !== targetKey)
                        ))
                    }
                },
            })
        } catch (err) {
            const targetKey = aiMsg._clientKey || aiMsg.id
            if (isAbortError(err)) {
                removeStreamingMessage(activeConversationId, aiMsg)
                syncActiveVariantMessages(messageId, (messagesForVariant) => (
                    messagesForVariant.filter((message) => (message._clientKey || message.id) !== targetKey)
                ))
                return
            }

            const errorMsg = createAssistantErrorMessage('Sorry, I encountered an error regenerating this response. Please try again.')
            setConversations((prev) =>
                prev.map((conversation) => {
                    if (conversation.id !== activeConversationId) return conversation
                    return {
                        ...conversation,
                        messages: [
                            ...conversation.messages.filter((message) => (message._clientKey || message.id) !== targetKey),
                            errorMsg,
                        ],
                    }
                })
            )
            syncActiveVariantMessages(messageId, (messagesForVariant) => ([
                ...messagesForVariant.filter((message) => (message._clientKey || message.id) !== targetKey),
                errorMsg,
            ]))
            console.error('Edit message error:', err)
        } finally {
            clearEditedMessagePending()
            abortControllerRef.current = null
            setIsLoading(false)
        }
    }, [activeConversationId, applyConversationMetadata, decorateVariantMessages, removeStreamingMessage, streamAssistantResponse, syncActiveVariantMessages])

    const handleResendMessage = useCallback(async (messageId) => {
        if (!activeConversationId) return
        setIsLoading(true)
        const controller = new AbortController()
        abortControllerRef.current = controller
        const tempAssistantMessageId = `pending-assistant-${Date.now()}`
        const aiMsg = createAssistantPlaceholder(tempAssistantMessageId)
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

            await streamAssistantResponse({
                response,
                aiMsg,
                getConversationId: () => activeConversationId,
                onMetadata: (parsed) => {
                    if (parsed.conversation_id && parsed.conversation_updated_at) {
                        applyConversationMetadata(parsed.conversation_id, {
                            updated_at: parsed.conversation_updated_at,
                            role: parsed.role,
                            subject: parsed.subject,
                            patient_sex: parsed.patient_sex,
                            pregnancy_status: parsed.pregnancy_status,
                        })
                    }
                },
            })
        } catch (err) {
            if (isAbortError(err)) {
                removeStreamingMessage(activeConversationId, aiMsg)
                return
            }

            const targetKey = aiMsg._clientKey || aiMsg.id
            const errorMsg = createAssistantErrorMessage('Sorry, I encountered an error regenerating this response. Please try again.')
            setConversations((prev) =>
                prev.map((conversation) => {
                    if (conversation.id !== activeConversationId) return conversation
                    return {
                        ...conversation,
                        messages: [
                            ...conversation.messages.filter((message) => (message._clientKey || message.id) !== targetKey),
                            errorMsg,
                        ],
                    }
                })
            )
            console.error('Resend message error:', err)
        } finally {
            abortControllerRef.current = null
            setIsLoading(false)
        }
    }, [activeConversationId, applyConversationMetadata, removeStreamingMessage, streamAssistantResponse])

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
        conversations,
        handleDeleteChat,
        handleEditMessage,
        handleMessageVariantChange,
        handleNewChat,
        handleOpenSessionContextModal,
        handleRenameChat,
        handleSaveSessionContext,
        handleCloseSessionContextModal,
        handleResendMessage,
        handleSelectChat,
        handleSendMessage,
        handleStopGeneration,
        canDismissSessionContextModal,
        isLoading,
        isLoadingMessages: loadingConversationId === activeConversationId && loadingConversationId !== null,
        isSavingSessionContext,
        messages,
        sessionContext,
        sessionContextDraft,
        sessionContextError,
        sessionContextModalKey,
        sessionContextModalOpen,
        setSidebarCollapsed,
        setSidebarOpen,
        sidebarCollapsed,
        sidebarOpen,
    }
}
