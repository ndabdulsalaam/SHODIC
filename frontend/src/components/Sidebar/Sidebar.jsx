import { useState, useRef, useEffect } from 'react'
import { HiOutlineChatBubbleLeftRight, HiOutlinePlus, HiOutlineTrash, HiOutlineUser, HiOutlineArrowRightOnRectangle, HiOutlineCog6Tooth, HiOutlinePencil, HiOutlineCheck, HiOutlineXMark } from 'react-icons/hi2'
import './Sidebar.css'

function Sidebar({ conversations, activeId, onNewChat, onSelectChat, onDeleteChat, onRenameChat, isOpen, onClose, user, onShowAuth, onLogout }) {
    const [editingId, setEditingId] = useState(null)
    const [editTitle, setEditTitle] = useState('')
    const editInputRef = useRef(null)

    useEffect(() => {
        if (editingId && editInputRef.current) {
            editInputRef.current.focus()
            editInputRef.current.select()
        }
    }, [editingId])

    const handleRenameStart = (chat) => {
        setEditingId(chat.id)
        setEditTitle(chat.title)
    }

    const handleRenameSave = () => {
        const trimmed = editTitle.trim()
        if (trimmed && editingId && onRenameChat) {
            onRenameChat(editingId, trimmed)
        }
        setEditingId(null)
    }

    const handleRenameCancel = () => {
        setEditingId(null)
        setEditTitle('')
    }

    const handleRenameKeyDown = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault()
            handleRenameSave()
        }
        if (e.key === 'Escape') {
            handleRenameCancel()
        }
    }

    // Build avatar initials from profile first/last name
    const getInitials = () => {
        const first = user?.first_name?.charAt(0)?.toUpperCase() || ''
        const last = user?.last_name?.charAt(0)?.toUpperCase() || ''
        if (first && last) return `${first}${last}`
        if (first) return first
        return user?.email?.charAt(0)?.toUpperCase() || 'U'
    }

    // Display name: first + last from profile
    const getDisplayName = () => {
        const name = [user?.first_name, user?.last_name].filter(Boolean).join(' ').trim()
        return name || user?.email || 'User'
    }

    return (
        <>
            <div className={`sidebar__overlay ${isOpen ? 'sidebar__overlay--visible' : ''}`} onClick={onClose} />
            <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}>
                {/* Header */}
                <div className="sidebar__header">
                    <div className="sidebar__logo">
                        <span className="sidebar__logo-text">
                            <span className="sidebar__logo-r">R</span>
                            <span className="sidebar__logo-x">x</span>
                            <span className="sidebar__logo-chat">Chat</span>
                        </span>
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
                            onClick={() => editingId !== chat.id && onSelectChat(chat.id)}
                        >
                            <HiOutlineChatBubbleLeftRight className="sidebar__chat-item-icon" />

                            {editingId === chat.id ? (
                                <input
                                    ref={editInputRef}
                                    className="sidebar__chat-item-input"
                                    value={editTitle}
                                    onChange={(e) => setEditTitle(e.target.value)}
                                    onKeyDown={handleRenameKeyDown}
                                    onBlur={handleRenameSave}
                                    onClick={(e) => e.stopPropagation()}
                                />
                            ) : (
                                <span className="sidebar__chat-item-text">{chat.title}</span>
                            )}

                            <div className="sidebar__chat-item-actions">
                                {editingId === chat.id ? (
                                    <>
                                        <button
                                            className="sidebar__chat-item-action"
                                            onClick={(e) => { e.stopPropagation(); handleRenameSave() }}
                                            aria-label="Save title"
                                        >
                                            <HiOutlineCheck size={14} />
                                        </button>
                                        <button
                                            className="sidebar__chat-item-action"
                                            onClick={(e) => { e.stopPropagation(); handleRenameCancel() }}
                                            aria-label="Cancel rename"
                                        >
                                            <HiOutlineXMark size={14} />
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        <button
                                            className="sidebar__chat-item-action"
                                            onClick={(e) => { e.stopPropagation(); handleRenameStart(chat) }}
                                            aria-label="Rename conversation"
                                        >
                                            <HiOutlinePencil size={14} />
                                        </button>
                                        <button
                                            className="sidebar__chat-item-action sidebar__chat-item-action--delete"
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                onDeleteChat(chat.id)
                                            }}
                                            aria-label="Delete conversation"
                                        >
                                            <HiOutlineTrash size={14} />
                                        </button>
                                    </>
                                )}
                            </div>
                        </div>
                    ))}
                </nav>

                {/* Footer */}
                <div className="sidebar__footer">
                    {user ? (
                        <div className="sidebar__user-profile">
                            <div className="sidebar__user-info">
                                <div className="sidebar__user-avatar">
                                    {getInitials()}
                                </div>
                                <div className="sidebar__user-details">
                                    <span className="sidebar__user-name">
                                        {getDisplayName()}
                                    </span>
                                </div>
                            </div>
                            <button className="sidebar__settings-btn" title="Settings (coming soon)">
                                <HiOutlineCog6Tooth size={18} />
                            </button>
                        </div>
                    ) : (
                        <button className="sidebar__user-btn" onClick={onShowAuth}>
                            <HiOutlineArrowRightOnRectangle size={18} />
                            <span>Sign in</span>
                        </button>
                    )}
                </div>
            </aside>
        </>
    )
}

export default Sidebar
