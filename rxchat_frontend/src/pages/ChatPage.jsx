import { lazy, Suspense } from 'react'
import Sidebar from '../components/Sidebar/Sidebar'
import ChatWindow from '../components/ChatWindow/ChatWindow'
import useChatController from '../hooks/useChatController'
import './ChatPage.css'

const AuthModal = lazy(() => import('../components/AuthModal/AuthModal'))
const SettingsPanel = lazy(() => import('../components/SettingsPanel/SettingsPanel'))

function ChatPage() {
    const chat = useChatController()

    return (
        <div className={`chat-layout ${chat.sidebarCollapsed ? 'chat-layout--collapsed' : ''}`}>
            <Sidebar
                conversations={chat.conversations}
                activeId={chat.activeConversationId}
                onNewChat={chat.handleNewChat}
                onSelectChat={chat.handleSelectChat}
                onDeleteChat={chat.handleDeleteChat}
                onRenameChat={chat.handleRenameChat}
                isOpen={chat.sidebarOpen}
                onClose={() => chat.setSidebarOpen(false)}
                collapsed={chat.sidebarCollapsed}
                onCollapse={() => chat.setSidebarCollapsed((prev) => !prev)}
                user={chat.user}
                onShowAuth={() => chat.handleShowAuth('login')}
                onLogout={chat.handleLogout}
                onOpenSettings={() => chat.setSettingsOpen(true)}
            />
            <ChatWindow
                conversationId={chat.activeConversationId}
                messages={chat.messages}
                onSendMessage={chat.handleSendMessage}
                isLoading={chat.isLoading}
                isLoadingMessages={chat.isLoadingMessages}
                onToggleSidebar={() => (
                    chat.sidebarCollapsed
                        ? chat.setSidebarCollapsed(false)
                        : chat.setSidebarOpen((prev) => !prev)
                )}
                onShowAuth={chat.handleShowAuth}
                user={chat.user}
                onLogout={chat.handleLogout}
                onEditMessage={chat.handleEditMessage}
                onResendMessage={chat.handleResendMessage}
                onMessageVariantChange={chat.handleMessageVariantChange}
                onStopGeneration={chat.handleStopGeneration}
            />
            <Suspense fallback={null}>
                {chat.showAuthModal && (
                    <AuthModal
                        onClose={() => chat.setShowAuthModal(false)}
                        onLogin={chat.handleLogin}
                        initialMode={chat.authMode}
                    />
                )}
                {chat.settingsOpen && (
                    <SettingsPanel
                        isOpen={chat.settingsOpen}
                        onClose={() => chat.setSettingsOpen(false)}
                        user={chat.user}
                        onLogout={() => {
                            chat.setSettingsOpen(false)
                            chat.handleLogout()
                        }}
                        onUserUpdate={chat.handleLogin}
                    />
                )}
            </Suspense>
        </div>
    )
}

export default ChatPage
