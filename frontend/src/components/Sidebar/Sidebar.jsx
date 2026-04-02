import { HiOutlineChatBubbleLeftRight, HiOutlinePlus, HiOutlineTrash, HiOutlineUser, HiOutlineArrowRightOnRectangle } from 'react-icons/hi2'
import { useNavigate } from 'react-router-dom'
import './Sidebar.css'

function Sidebar({ conversations, activeId, onNewChat, onSelectChat, onDeleteChat, isOpen, onClose, user }) {
    const navigate = useNavigate()

    return (
        <>
            <div className={`sidebar__overlay ${isOpen ? 'sidebar__overlay--visible' : ''}`} onClick={onClose} />
            <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}>
                {/* Header */}
                <div className="sidebar__header">
                    <div className="sidebar__logo">
                        <div className="sidebar__logo-icon">Rx</div>
                        <div className="sidebar__logo-text">
                            Rx<span>Chat</span>
                        </div>
                    </div>
                    <button className="sidebar__new-chat" onClick={onNewChat}>
                        <HiOutlinePlus size={16} />
                        New Conversation
                    </button>
                </div>

                {/* Conversations List */}
                <nav className="sidebar__conversations">
                    {conversations.length > 0 && (
                        <div className="sidebar__section-label">Recent</div>
                    )}
                    {conversations.map((chat) => (
                        <div
                            key={chat.id}
                            className={`sidebar__chat-item ${activeId === chat.id ? 'sidebar__chat-item--active' : ''}`}
                            onClick={() => onSelectChat(chat.id)}
                        >
                            <HiOutlineChatBubbleLeftRight className="sidebar__chat-item-icon" />
                            <span className="sidebar__chat-item-text">{chat.title}</span>
                            <button
                                className="sidebar__chat-item-delete"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    onDeleteChat(chat.id)
                                }}
                                aria-label="Delete conversation"
                            >
                                <HiOutlineTrash size={14} />
                            </button>
                        </div>
                    ))}
                </nav>

                {/* Footer */}
                <div className="sidebar__footer">
                    {user ? (
                        <button className="sidebar__user-btn">
                            <div className="sidebar__user-avatar">
                                {user.name?.charAt(0).toUpperCase() || 'U'}
                            </div>
                            <span>{user.name || user.email}</span>
                        </button>
                    ) : (
                        <button className="sidebar__user-btn" onClick={() => navigate('/auth')}>
                            <HiOutlineArrowRightOnRectangle size={18} />
                            <span>Sign in to save history</span>
                        </button>
                    )}
                </div>
            </aside>
        </>
    )
}

export default Sidebar
