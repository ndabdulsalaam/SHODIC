import { useState, useCallback, useEffect } from 'react'
import Sidebar from '../components/Sidebar/Sidebar'
import ChatWindow from '../components/ChatWindow/ChatWindow'
import AuthModal from '../components/AuthModal/AuthModal'
import SettingsPanel from '../components/SettingsPanel/SettingsPanel'
import './ChatPage.css'

function ChatPage() {
    const [conversations, setConversations] = useState([])
    const [activeConversationId, setActiveConversationId] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
    const [showAuthModal, setShowAuthModal] = useState(false)
    const [authMode, setAuthMode] = useState('login')
    const [user, setUser] = useState(null)
    const [settingsOpen, setSettingsOpen] = useState(false)

    const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

    // Check if user is already logged in on mount
    useEffect(() => {
        const checkAuth = async () => {
            try {
                const res = await fetch(`${API}/auth/me/`, { credentials: 'include' })
                const data = await res.json()
                if (data.id) setUser(data)
            } catch { /* not logged in */ }
        }
        checkAuth()
    }, [API])

    // Load conversations from backend on mount and when user changes
    useEffect(() => {
        const loadConversations = async () => {
            try {
                const res = await fetch(`${API}/chat/conversations/`, { credentials: 'include' })
                if (res.ok) {
                    const data = await res.json()
                    setConversations(data.map(c => ({
                        id: c.id,
                        title: c.title,
                        messages: [],
                        _loaded: false,
                    })))
                }
            } catch { /* offline or error */ }
        }
        loadConversations()
    }, [API, user])

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
        setConversations([])
        setActiveConversationId(null)
    }

    const activeConversation = conversations.find((c) => c.id === activeConversationId)
    const messages = activeConversation?.messages || []

    // Load messages when selecting a conversation that hasn't been loaded
    const loadConversationMessages = useCallback(async (convId) => {
        const conv = conversations.find(c => c.id === convId)
        if (conv && conv._loaded) return

        try {
            const res = await fetch(`${API}/chat/conversations/${convId}/`, { credentials: 'include' })
            if (res.ok) {
                const data = await res.json()
                setConversations(prev => prev.map(c =>
                    c.id === convId
                        ? { ...c, messages: data.messages || [], _loaded: true }
                        : c
                ))
            }
        } catch { /* error */ }
    }, [API, conversations])

    const handleSendMessage = useCallback(async (text) => {
        let convId = activeConversationId

        const userMsg = {
            role: 'user',
            content: text,
            created_at: new Date().toISOString(),
        }

        // Optimistically add user message
        if (convId) {
            setConversations((prev) =>
                prev.map((c) =>
                    c.id === convId ? { ...c, messages: [...c.messages, userMsg] } : c
                )
            )
        }

        setIsLoading(true)

        try {
            const res = await fetch(`${API}/chat/send/`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    ...(convId ? { conversation_id: convId } : {}),
                }),
            })

            if (!res.ok) {
                throw new Error(`API error: ${res.status}`)
            }

            const reader = res.body.getReader()
            const decoder = new TextDecoder()
            let aiContent = ''
            let actualConvId = convId
            let buffer = ''

            // Create a placeholder AI message
            const aiMsg = {
                role: 'assistant',
                content: '',
                created_at: new Date().toISOString(),
                _streaming: true,
            }

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })

                // Parse SSE events from buffer
                const lines = buffer.split('\n')
                buffer = lines.pop() || '' // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('event: meta')) {
                        // Next data line will contain metadata
                        continue
                    }

                    if (line.startsWith('data: ')) {
                        const data = line.slice(6)

                        // Check if this is a JSON meta/done event
                        if (data.startsWith('{')) {
                            try {
                                const parsed = JSON.parse(data)
                                if (parsed.conversation_id) {
                                    actualConvId = parsed.conversation_id

                                    // If this is a new conversation, add it
                                    if (!convId) {
                                        const newConv = {
                                            id: actualConvId,
                                            title: parsed.conversation_title || text.slice(0, 35) + '...',
                                            messages: [userMsg, aiMsg],
                                            _loaded: true,
                                        }
                                        setConversations((prev) => [newConv, ...prev])
                                        setActiveConversationId(actualConvId)
                                    }
                                }
                                if (parsed.message_id) {
                                    // Done event — mark streaming complete
                                    aiMsg._streaming = false
                                    aiMsg.id = parsed.message_id
                                }
                                continue
                            } catch { /* not JSON, treat as text chunk */ }
                        }

                        // Text chunk — unescape newlines
                        const textChunk = data.replace(/\\n/g, '\n')
                        aiContent += textChunk

                        // Update the AI message in state
                        setConversations((prev) =>
                            prev.map((c) => {
                                if (c.id !== actualConvId) return c
                                const msgs = [...c.messages]
                                const lastMsg = msgs[msgs.length - 1]
                                if (lastMsg?.role === 'assistant' && lastMsg?._streaming) {
                                    msgs[msgs.length - 1] = { ...lastMsg, content: aiContent }
                                } else {
                                    msgs.push({ ...aiMsg, content: aiContent })
                                }
                                return { ...c, messages: msgs }
                            })
                        )
                    }

                    if (line.startsWith('event: done')) {
                        continue
                    }
                }
            }

            // Final update: mark streaming complete
            setConversations((prev) =>
                prev.map((c) => {
                    if (c.id !== actualConvId) return c
                    const msgs = c.messages.map((m) =>
                        m._streaming ? { ...m, content: aiContent, _streaming: false } : m
                    )
                    return { ...c, messages: msgs }
                })
            )
        } catch (err) {
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
            setIsLoading(false)
        }
    }, [activeConversationId, API])

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
            await fetch(`${API}/chat/conversations/${id}/delete/`, {
                method: 'DELETE',
                credentials: 'include',
            })
        } catch { /* ignore */ }
        setConversations((prev) => prev.filter((c) => c.id !== id))
        if (activeConversationId === id) {
            setActiveConversationId(null)
        }
    }, [activeConversationId, API])

    const handleRenameChat = useCallback(async (id, newTitle) => {
        try {
            await fetch(`${API}/chat/conversations/${id}/rename/`, {
                method: 'PATCH',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle }),
            })
        } catch { /* ignore */ }
        setConversations((prev) =>
            prev.map((c) => c.id === id ? { ...c, title: newTitle } : c)
        )
    }, [API])

    const handleEditMessage = useCallback(async (messageId, newContent) => {
        if (!activeConversationId) return
        setIsLoading(true)

        // Optimistically trim messages after the edited one
        setConversations((prev) =>
            prev.map((c) => {
                if (c.id !== activeConversationId) return c
                const idx = c.messages.findIndex(m => m.id === messageId)
                if (idx === -1) return c
                const msgs = c.messages.slice(0, idx + 1)
                msgs[idx] = { ...msgs[idx], content: newContent }
                return { ...c, messages: msgs }
            })
        )

        try {
            const res = await fetch(`${API}/chat/messages/${messageId}/`, {
                method: 'PUT',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content: newContent }),
            })

            if (!res.ok) throw new Error(`API error: ${res.status}`)

            const reader = res.body.getReader()
            const decoder = new TextDecoder()
            let aiContent = ''
            let buffer = ''

            const aiMsg = { role: 'assistant', content: '', created_at: new Date().toISOString(), _streaming: true }

            // Add placeholder AI message
            setConversations((prev) =>
                prev.map((c) => c.id === activeConversationId ? { ...c, messages: [...c.messages, aiMsg] } : c)
            )

            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''
                for (const line of lines) {
                    if (line.startsWith('data: ') && !line.slice(6).startsWith('{')) {
                        aiContent += line.slice(6).replace(/\\n/g, '\n')
                        setConversations((prev) =>
                            prev.map((c) => {
                                if (c.id !== activeConversationId) return c
                                const msgs = [...c.messages]
                                const last = msgs[msgs.length - 1]
                                if (last?._streaming) msgs[msgs.length - 1] = { ...last, content: aiContent }
                                return { ...c, messages: msgs }
                            })
                        )
                    }
                }
            }

            setConversations((prev) =>
                prev.map((c) => {
                    if (c.id !== activeConversationId) return c
                    return { ...c, messages: c.messages.map(m => m._streaming ? { ...m, content: aiContent, _streaming: false } : m) }
                })
            )
        } catch (err) {
            console.error('Edit message error:', err)
        } finally {
            setIsLoading(false)
        }
    }, [activeConversationId, API])

    const handleResendMessage = useCallback(async (messageId) => {
        if (!activeConversationId) return
        setIsLoading(true)

        // Remove messages after the target message
        setConversations((prev) =>
            prev.map((c) => {
                if (c.id !== activeConversationId) return c
                const idx = c.messages.findIndex(m => m.id === messageId)
                if (idx === -1) return c
                return { ...c, messages: c.messages.slice(0, idx + 1) }
            })
        )

        try {
            const res = await fetch(`${API}/chat/messages/${messageId}/resend/`, {
                method: 'POST',
                credentials: 'include',
            })

            if (!res.ok) throw new Error(`API error: ${res.status}`)

            const reader = res.body.getReader()
            const decoder = new TextDecoder()
            let aiContent = ''
            let buffer = ''

            const aiMsg = { role: 'assistant', content: '', created_at: new Date().toISOString(), _streaming: true }

            setConversations((prev) =>
                prev.map((c) => c.id === activeConversationId ? { ...c, messages: [...c.messages, aiMsg] } : c)
            )

            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''
                for (const line of lines) {
                    if (line.startsWith('data: ') && !line.slice(6).startsWith('{')) {
                        aiContent += line.slice(6).replace(/\\n/g, '\n')
                        setConversations((prev) =>
                            prev.map((c) => {
                                if (c.id !== activeConversationId) return c
                                const msgs = [...c.messages]
                                const last = msgs[msgs.length - 1]
                                if (last?._streaming) msgs[msgs.length - 1] = { ...last, content: aiContent }
                                return { ...c, messages: msgs }
                            })
                        )
                    }
                }
            }

            setConversations((prev) =>
                prev.map((c) => {
                    if (c.id !== activeConversationId) return c
                    return { ...c, messages: c.messages.map(m => m._streaming ? { ...m, content: aiContent, _streaming: false } : m) }
                })
            )
        } catch (err) {
            console.error('Resend message error:', err)
        } finally {
            setIsLoading(false)
        }
    }, [activeConversationId, API])

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
                onToggleSidebar={() => sidebarCollapsed ? setSidebarCollapsed(false) : setSidebarOpen((prev) => !prev)}
                onShowAuth={handleShowAuth}
                user={user}
                onLogout={handleLogout}
                onEditMessage={handleEditMessage}
                onResendMessage={handleResendMessage}
            />
            {showAuthModal && (
                <AuthModal
                    onClose={() => setShowAuthModal(false)}
                    onLogin={(userData) => setUser(userData)}
                    initialMode={authMode}
                />
            )}
            <SettingsPanel
                isOpen={settingsOpen}
                onClose={() => setSettingsOpen(false)}
                user={user}
                onLogout={() => { setSettingsOpen(false); handleLogout() }}
                onUserUpdate={(data) => setUser(data)}
            />
        </div>
    )
}

export default ChatPage
