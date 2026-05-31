import Sidebar from '../components/Sidebar/Sidebar'
import ChatWindow from '../components/ChatWindow/ChatWindow'
import SessionContextModal from '../components/SessionContextModal/SessionContextModal'
import useChatController from '../hooks/useChatController'
import './ChatPage.css'

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
                onEditMessage={chat.handleEditMessage}
                onResendMessage={chat.handleResendMessage}
                onMessageVariantChange={chat.handleMessageVariantChange}
                onStopGeneration={chat.handleStopGeneration}
                sessionContext={chat.sessionContext}
                onEditSessionContext={chat.handleOpenSessionContextModal}
            />
            <SessionContextModal
                key={chat.sessionContextModalKey}
                isOpen={chat.sessionContextModalOpen}
                initialContext={chat.sessionContextDraft}
                canDismiss={chat.canDismissSessionContextModal}
                isSaving={chat.isSavingSessionContext}
                error={chat.sessionContextError}
                onClose={chat.handleCloseSessionContextModal}
                onSubmit={chat.handleSaveSessionContext}
            />
        </div>
    )
}

export default ChatPage
