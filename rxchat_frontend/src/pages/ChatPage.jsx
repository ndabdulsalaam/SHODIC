import { useState, useCallback, useEffect, useRef } from 'react'
import Sidebar from '../components/Sidebar/Sidebar'
import ChatWindow from '../components/ChatWindow/ChatWindow'
import AuthModal from '../components/AuthModal/AuthModal'
import SettingsPanel from '../components/SettingsPanel/SettingsPanel'
import { API_BASE_URL as API } from '../utils/api'
import { productApiPath } from '../config/product'
import './ChatPage.css'

const AUTH_USER_CACHE_KEY = 'rxchat_auth_user'
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

function parseJsonData(data) {
    try {
        return JSON.parse(data)
    } catch {
        return null
    }
}

function createSseParser({ onMeta, onStatus, onDone, onText }) {
    let buffer = ''
    let currentEvent = 'message'

    const handleParsedData = (eventName, data) => {
        if (eventName === 'status') {
            const parsed = parseJsonData(data)
            if (parsed) onStatus?.(parsed)
            return
        }

        if (eventName === 'meta') {
            const parsed = parseJsonData(data)
            if (parsed) onMeta?.(parsed)
            return
        }

        if (eventName === 'done') {
            const parsed = parseJsonData(data)
            if (parsed) onDone?.(parsed)
            return
        }

        const parsed = data.startsWith('{') ? parseJsonData(data) : null
        if (
            parsed
            && (parsed.conversation_id || parsed.user_message_id || parsed.edited_message_id || parsed.message_id)
        ) {
            onMeta?.(parsed)
            return
        }

        onText?.(data.replace(/\\n/g, '\n'))
    }

    const handleLine = (line) => {
        if (!line) {
            currentEvent = 'message'
            return
        }

        if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim() || 'message'
            return
        }

        if (!line.startsWith('data: ')) return

        const eventName = currentEvent
        currentEvent = 'message'
        handleParsedData(eventName, line.slice(6))
    }

    return {
        push(chunk) {
            buffer += chunk
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''
            lines.forEach(handleLine)
        },
        flush() {
            if (!buffer) return
            handleLine(buffer)
            buffer = ''
        },
    }
}

function readCachedAuthUser() {
    try {
        const cached = sessionStorage.getItem(AUTH_USER_CACHE_KEY)
        return cached ? JSON.parse(cached) : null
    } catch {
        return null
    }
}

function cacheAuthUser(user) {
    try {
        if (user?.id) {
            sessionStorage.setItem(AUTH_USER_CACHE_KEY, JSON.stringify(user))
        } else {
            sessionStorage.removeItem(AUTH_USER_CACHE_KEY)
        }
    } catch { /* storage may be unavailable */ }
}

function ChatPage() {
    const [conversations, setConversations] = useState([])
    const [activeConversationId, setActiveConversationId] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [generationStatus, setGenerationStatus] = useState(null)
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

    const updateStreamingMessage = useCallback((conversationId, aiMsg, content, messageId, markComplete = false) => {
        if (!conversationId) return

        const targetKey = aiMsg._clientKey || aiMsg.id
        setConversations((prev) =>
            prev.map((c) => {
                if (c.id !== conversationId) return c

                let foundStreamingMessage = false
                const msgs = c.messages.map((m) => {
                    if (!m._streaming) return m
                    const messageKey = m._clientKey || m.id
                    if (messageKey !== targetKey) return m

                    foundStreamingMessage = true
                    return {
                        ...m,
                        id: messageId || m.id,
                        content,
                        _streaming: markComplete ? false : m._streaming,
                    }
                })

                if (!foundStreamingMessage && (content || !markComplete)) {
                    msgs.push({
                        ...aiMsg,
                        id: messageId || aiMsg.id,
                        content,
                        _streaming: !markComplete,
                    })
                }

                return { ...c, messages: msgs }
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

    // Check if user is already logged in on mount
    useEffect(() => {
        const checkAuth = async () => {
            try {
                const res = await fetch(`${API}/auth/me/`, { credentials: 'include' })
                const data = await res.json()
                if (data.id) {
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

    // Load conversations from backend on mount and when user changes
    useEffect(() => {
        const loadConversations = async () => {
            try {
                const res = await fetch(`${API}${productApiPath('/conversations/')}`, { credentials: 'include' })
                if (res.ok) {
                    const data = await res.json()
                    setConversations(sortConversationsByUpdated(data.map((conversation) => (
                        preserveConversationFields(conversation)
                    ))))
                }
            } catch { /* offline or error */ }
        }
        loadConversations()
    }, [user])

    const handleShowAuth = (mode = 'login') => {
        setAuthMode(mode)
        setShowAuthModal(true)
    }

    const handleLogout = async () => {
        try {
            await fetch(`${API}/auth/logout/`, {
                method: 'POST',
                credentials: 'include',
            })
        } catch { /* ignore */ }
        setUser(null)
        cacheAuthUser(null)
        setConversations([])
        setActiveConversationId(null)
    }

    const handleLogin = useCallback((userData) => {
        setUser(userData)
        cacheAuthUser(userData)
    }, [])

    const activeConversation = conversations.find((c) => c.id === activeConversationId)
    const messages = activeConversation?.messages || []

    // Load messages when selecting a conversation that hasn't been loaded
    const loadConversationMessages = useCallback(async (convId) => {
        const conv = conversationsRef.current.find(c => c.id === convId)
        if (conv && conv._loaded) {
            setLoadingConversationId(null)
            return
        }

        setLoadingConversationId(convId)
        try {
            const res = await fetch(`${API}${productApiPath(`/conversations/${convId}/`)}`, { credentials: 'include' })
            if (res.ok) {
                const data = await res.json()
                setConversations(prev => prev.map(c =>
                    c.id === convId
                        ? preserveConversationFields({
                            ...c,
                            ...data,
                            messages: data.messages || [],
                            _loaded: true,
                        }, c)
                        : c
                ))
            }
        } catch { /* error */ }
        setLoadingConversationId(null)
    }, [])

    const handleSendMessage = useCallback(async (payload) => {
        const { text } = normalizeSendPayload(payload)
        const trimmedText = text.trim()
        if (!trimmedText) return
        const localTitleSource = trimmedText || 'New Conversation'

        let convId = activeConversationId
        const tempUserMessageId = `pending-user-${Date.now()}`

        const userMsg = {
            id: tempUserMessageId,
            _clientKey: tempUserMessageId,
            role: 'user',
            content: trimmedText,
            attachments: [],
            created_at: new Date().toISOString(),
            _pending: true,
        }

        // Optimistically add user message
        if (convId) {
            setConversations((prev) =>
                sortConversationsByUpdated(prev.map((c) =>
                    c.id === convId
                        ? {
                            ...c,
                            messages: [...c.messages, userMsg],
                            updated_at: userMsg.created_at,
                            message_count: (c.message_count ?? c.messages.length) + 1,
                        }
                        : c
                ))
            )
        }

        setIsLoading(true)
        setGenerationStatus(null)
        const controller = new AbortController()
        abortControllerRef.current = controller
        let streamingFlusher = null
        let aiContent = ''
        let actualConvId = convId
        let aiMessageId = null
        let aiMsg = null
        let hasReceivedText = false

        try {
            const res = await fetch(`${API}${productApiPath('/send/')}`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: trimmedText,
                    ...(convId ? { conversation_id: convId } : {}),
                }),
                signal: controller.signal,
            })

            if (!res.ok) {
                throw new Error(`API error: ${res.status}`)
            }

            const reader = res.body.getReader()
            const decoder = new TextDecoder()

            // Create a placeholder AI message
            const tempAssistantMessageId = `pending-assistant-${Date.now()}`
            aiMsg = {
                id: tempAssistantMessageId,
                _clientKey: tempAssistantMessageId,
                role: 'assistant',
                content: '',
                created_at: new Date().toISOString(),
                _streaming: true,
            }
            streamingFlusher = createStreamingFrameFlusher((markComplete) => {
                updateStreamingMessage(actualConvId, aiMsg, aiContent, aiMessageId, markComplete)
            })

            const handleStreamMetadata = (parsed) => {
                if (parsed.conversation_id) {
                    actualConvId = parsed.conversation_id
                    const conversationUpdatedAt = parsed.conversation_updated_at || new Date().toISOString()

                    // If this is a new conversation, add it
                    if (!convId) {
                        setConversations((prev) => {
                            const existing = prev.find((conversation) => conversation.id === actualConvId)
                            if (existing) {
                                return sortConversationsByUpdated(prev.map((conversation) => (
                                    conversation.id === actualConvId
                                        ? {
                                            ...conversation,
                                            title: parsed.conversation_title || conversation.title,
                                            updated_at: conversationUpdatedAt,
                                        }
                                        : conversation
                                )))
                            }

                            const newConv = preserveConversationFields({
                                id: actualConvId,
                                title: parsed.conversation_title || `${localTitleSource.slice(0, 35)}...`,
                                created_at: conversationUpdatedAt,
                                updated_at: conversationUpdatedAt,
                                message_count: 1,
                                messages: [userMsg, aiMsg],
                                _loaded: true,
                            })
                            return sortConversationsByUpdated([newConv, ...prev])
                        })
                        setActiveConversationId(actualConvId)
                    } else {
                        applyConversationMetadata(actualConvId, {
                            title: parsed.conversation_title,
                            updated_at: conversationUpdatedAt,
                        })
                    }
                }

                if (parsed.user_message_id) {
                    setConversations((prev) =>
                        sortConversationsByUpdated(prev.map((c) => {
                            if (c.id !== actualConvId) return c
                            const msgs = c.messages.map((m) =>
                                m.id === tempUserMessageId
                                    ? { ...m, id: parsed.user_message_id, _pending: false }
                                    : m
                            )
                            return { ...c, messages: msgs }
                        }))
                    )
                }

                if (parsed.message_id) {
                    aiMessageId = parsed.message_id
                }
            }

            const streamParser = createSseParser({
                onMeta: handleStreamMetadata,
                onDone: handleStreamMetadata,
                onStatus: (status) => {
                    if (!hasReceivedText) setGenerationStatus(status)
                },
                onText: (textChunk) => {
                    if (!textChunk) return
                    hasReceivedText = true
                    setGenerationStatus(null)
                    aiContent += textChunk
                    streamingFlusher.schedule()
                },
            })

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                streamParser.push(decoder.decode(value, { stream: true }))
            }

            streamParser.push(decoder.decode())
            streamParser.flush()
            // Final update: mark streaming complete
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
                prev.map((c) =>
                    c.id === (activeConversationId || convId)
                        ? { ...c, messages: [...c.messages.filter(m => !m._streaming), errorMsg] }
                        : c
                )
            )
        } finally {
            abortControllerRef.current = null
            setIsLoading(false)
            setGenerationStatus(null)
        }
    }, [activeConversationId, applyConversationMetadata, createStreamingFrameFlusher, finishInterruptedStream, updateStreamingMessage])

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
            await fetch(`${API}${productApiPath(`/conversations/${id}/delete/`)}`, {
                method: 'DELETE',
                credentials: 'include',
            })
        } catch { /* ignore */ }
        setConversations((prev) => prev.filter((c) => c.id !== id))
        if (activeConversationId === id) {
            setActiveConversationId(null)
        }
    }, [activeConversationId])

    const handleRenameChat = useCallback(async (id, newTitle) => {
        try {
            await fetch(`${API}${productApiPath(`/conversations/${id}/rename/`)}`, {
                method: 'PATCH',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle }),
            })
        } catch { /* ignore */ }
        setConversations((prev) =>
            prev.map((c) => c.id === id ? { ...c, title: newTitle } : c)
        )
    }, [])

    const handleEditMessage = useCallback(async (messageId, newContent) => {
        if (!activeConversationId) return
        const conversationSnapshot = conversationsRef.current.find((c) => c.id === activeConversationId)
        const messageIndex = conversationSnapshot?.messages.findIndex((m) => m.id === messageId) ?? -1
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
        }
        const tempAssistantMessageId = `pending-assistant-${Date.now()}`
        const aiMsg = {
            id: tempAssistantMessageId,
            _clientKey: tempAssistantMessageId,
            role: 'assistant',
            content: '',
            created_at: new Date().toISOString(),
            _streaming: true,
        }

        variantGroup.variants.push([editedUserMessage, aiMsg])
        variantGroup.activeIndex = newVariantIndex
        editVariantsRef.current[messageId] = variantGroup

        setIsLoading(true)
        setGenerationStatus(null)
        const controller = new AbortController()
        abortControllerRef.current = controller
        let streamingFlusher = null
        let aiContent = ''
        let aiMessageId = null
        let hasReceivedText = false

        // Optimistically switch to the new edit variant and stream the replacement response.
        setConversations((prev) =>
            sortConversationsByUpdated(prev.map((c) => {
                if (c.id !== activeConversationId) return c
                const idx = c.messages.findIndex((m) => m.id === messageId)
                if (idx === -1) return c
                const prefix = c.messages.slice(0, idx)
                const decoratedVariant = decorateVariantMessages(
                    variantGroup.variants[newVariantIndex],
                    messageId,
                    newVariantIndex,
                    variantGroup.variants.length,
                )
                return { ...c, messages: [...prefix, ...decoratedVariant], updated_at: editedUserMessage.updated_at }
            }))
        )

        try {
            const res = await fetch(`${API}${productApiPath(`/messages/${messageId}/`)}`, {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newContent }),
                signal: controller.signal,
            })

            if (!res.ok) throw new Error(`API error: ${res.status}`)

            const reader = res.body.getReader()
            const decoder = new TextDecoder()

            streamingFlusher = createStreamingFrameFlusher((markComplete) => {
                updateStreamingMessage(activeConversationId, aiMsg, aiContent, aiMessageId, markComplete)
                syncActiveVariantMessages(messageId, (messagesForVariant) => (
                    messagesForVariant.map((m) => (
                        m._streaming
                            ? { ...m, id: aiMessageId || m.id, content: aiContent, _streaming: markComplete ? false : m._streaming }
                            : m
                    ))
                ))
            })

            const handleStreamMetadata = (parsed) => {
                if (parsed.conversation_id && parsed.conversation_updated_at) {
                    applyConversationMetadata(parsed.conversation_id, {
                        updated_at: parsed.conversation_updated_at,
                    })
                }
                if (parsed.message_id) aiMessageId = parsed.message_id
            }

            const streamParser = createSseParser({
                onMeta: handleStreamMetadata,
                onDone: handleStreamMetadata,
                onStatus: (status) => {
                    if (!hasReceivedText) setGenerationStatus(status)
                },
                onText: (textChunk) => {
                    if (!textChunk) return
                    hasReceivedText = true
                    setGenerationStatus(null)
                    aiContent += textChunk
                    streamingFlusher.schedule()
                },
            })

            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                streamParser.push(decoder.decode(value, { stream: true }))
            }

            streamParser.push(decoder.decode())
            streamParser.flush()
            streamingFlusher.finalize()
        } catch (err) {
            if (isAbortError(err)) {
                finishInterruptedStream(activeConversationId, aiMsg, streamingFlusher, aiContent)
                if (!aiContent) {
                    const targetKey = aiMsg._clientKey || aiMsg.id
                    syncActiveVariantMessages(messageId, (messagesForVariant) => (
                        messagesForVariant.filter((m) => (m._clientKey || m.id) !== targetKey)
                    ))
                }
                return
            }

            streamingFlusher?.cancel()
            console.error('Edit message error:', err)
        } finally {
            abortControllerRef.current = null
            setIsLoading(false)
            setGenerationStatus(null)
        }
    }, [activeConversationId, applyConversationMetadata, createStreamingFrameFlusher, decorateVariantMessages, finishInterruptedStream, syncActiveVariantMessages, updateStreamingMessage])

    const handleResendMessage = useCallback(async (messageId) => {
        if (!activeConversationId) return
        setIsLoading(true)
        setGenerationStatus(null)
        const controller = new AbortController()
        abortControllerRef.current = controller
        let streamingFlusher = null
        let aiContent = ''
        let aiMessageId = null
        let aiMsg = null
        let hasReceivedText = false
        const resendUpdatedAt = new Date().toISOString()

        // Remove messages after the target message
        setConversations((prev) =>
            sortConversationsByUpdated(prev.map((c) => {
                if (c.id !== activeConversationId) return c
                const idx = c.messages.findIndex(m => m.id === messageId)
                if (idx === -1) return c
                return { ...c, messages: c.messages.slice(0, idx + 1), updated_at: resendUpdatedAt }
            }))
        )

        try {
            const res = await fetch(`${API}${productApiPath(`/messages/${messageId}/resend/`)}`, {
                method: 'POST',
                credentials: 'include',
                signal: controller.signal,
            })

            if (!res.ok) throw new Error(`API error: ${res.status}`)

            const reader = res.body.getReader()
            const decoder = new TextDecoder()

            const tempAssistantMessageId = `pending-assistant-${Date.now()}`
            aiMsg = {
                id: tempAssistantMessageId,
                _clientKey: tempAssistantMessageId,
                role: 'assistant',
                content: '',
                created_at: new Date().toISOString(),
                _streaming: true,
            }
            streamingFlusher = createStreamingFrameFlusher((markComplete) => {
                updateStreamingMessage(activeConversationId, aiMsg, aiContent, aiMessageId, markComplete)
            })

            const handleStreamMetadata = (parsed) => {
                if (parsed.conversation_id && parsed.conversation_updated_at) {
                    applyConversationMetadata(parsed.conversation_id, {
                        updated_at: parsed.conversation_updated_at,
                    })
                }
                if (parsed.message_id) aiMessageId = parsed.message_id
            }

            const streamParser = createSseParser({
                onMeta: handleStreamMetadata,
                onDone: handleStreamMetadata,
                onStatus: (status) => {
                    if (!hasReceivedText) setGenerationStatus(status)
                },
                onText: (textChunk) => {
                    if (!textChunk) return
                    hasReceivedText = true
                    setGenerationStatus(null)
                    aiContent += textChunk
                    streamingFlusher.schedule()
                },
            })

            setConversations((prev) =>
                prev.map((c) => c.id === activeConversationId ? { ...c, messages: [...c.messages, aiMsg] } : c)
            )

            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                streamParser.push(decoder.decode(value, { stream: true }))
            }

            streamParser.push(decoder.decode())
            streamParser.flush()
            streamingFlusher.finalize()
        } catch (err) {
            if (isAbortError(err)) {
                finishInterruptedStream(activeConversationId, aiMsg, streamingFlusher, aiContent)
                return
            }

            streamingFlusher?.cancel()
            console.error('Resend message error:', err)
        } finally {
            abortControllerRef.current = null
            setIsLoading(false)
            setGenerationStatus(null)
        }
    }, [activeConversationId, applyConversationMetadata, createStreamingFrameFlusher, finishInterruptedStream, updateStreamingMessage])

    const handleMessageVariantChange = useCallback((groupId, nextIndex) => {
        const group = editVariantsRef.current[groupId]
        if (!group || nextIndex < 0 || nextIndex >= group.variants.length) return

        group.activeIndex = nextIndex
        setConversations((prev) =>
            prev.map((c) => {
                if (c.id !== group.conversationId) return c
                const messageIndex = c.messages.findIndex((m) => m.id === groupId)
                if (messageIndex === -1) return c

                const prefix = c.messages.slice(0, messageIndex)
                const decoratedVariant = decorateVariantMessages(
                    group.variants[nextIndex],
                    groupId,
                    nextIndex,
                    group.variants.length,
                )

                return { ...c, messages: [...prefix, ...decoratedVariant] }
            })
        )
    }, [decorateVariantMessages])

    const handleStopGeneration = useCallback(() => {
        setGenerationStatus(null)
        if (abortControllerRef.current) {
            abortControllerRef.current.abort()
            abortControllerRef.current = null
        }
    }, [])

    return (
        <div className={`chat-layout ${sidebarCollapsed ? 'chat-layout--collapsed' : ''}`}>
            <Sidebar
                conversations={conversations}
                activeId={activeConversationId}
                onNewChat={handleNewChat}
                onSelectChat={handleSelectChat}
                onDeleteChat={handleDeleteChat}
                onRenameChat={handleRenameChat}
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
                collapsed={sidebarCollapsed}
                onCollapse={() => setSidebarCollapsed((prev) => !prev)}
                user={user}
                onShowAuth={() => handleShowAuth('login')}
                onLogout={handleLogout}
                onOpenSettings={() => setSettingsOpen(true)}
            />
            <ChatWindow
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                generationStatus={generationStatus}
                isLoadingMessages={loadingConversationId === activeConversationId && loadingConversationId !== null}
                onToggleSidebar={() => sidebarCollapsed ? setSidebarCollapsed(false) : setSidebarOpen((prev) => !prev)}
                onShowAuth={handleShowAuth}
                user={user}
                onLogout={handleLogout}
                onEditMessage={handleEditMessage}
                onResendMessage={handleResendMessage}
                onMessageVariantChange={handleMessageVariantChange}
                onStopGeneration={handleStopGeneration}
            />
            {showAuthModal && (
                <AuthModal
                    onClose={() => setShowAuthModal(false)}
                    onLogin={handleLogin}
                    initialMode={authMode}
                />
            )}
            <SettingsPanel
                isOpen={settingsOpen}
                onClose={() => setSettingsOpen(false)}
                user={user}
                onLogout={() => { setSettingsOpen(false); handleLogout() }}
                onUserUpdate={handleLogin}
            />
        </div>
    )
}

export default ChatPage
