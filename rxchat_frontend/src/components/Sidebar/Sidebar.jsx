import { useState, useRef, useEffect, useMemo } from 'react'
import { HiOutlineChatBubbleLeftRight, HiOutlinePlus, HiOutlineTrash, HiOutlineArrowRightOnRectangle, HiOutlineCog6Tooth, HiOutlinePencil, HiOutlineCheck, HiOutlineXMark, HiOutlineChevronDoubleLeft } from 'react-icons/hi2'
import './Sidebar.css'

const DAY_MS = 24 * 60 * 60 * 1000

function getConversationTimestamp(conversation) {
    const rawDate = conversation?.updated_at || conversation?.created_at || ''
    const timestamp = Date.parse(rawDate)
    return Number.isNaN(timestamp) ? 0 : timestamp
}

function getStartOfLocalDay(date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
}

function groupConversations(conversations) {
    const now = new Date()
    const todayStart = getStartOfLocalDay(now)
    const sevenDaysAgo = now.getTime() - (7 * DAY_MS)
    const groups = {
        today: [],
        sevenDays: [],
        older: [],
    }

    conversations.forEach((conversation) => {
        const timestamp = getConversationTimestamp(conversation)
        if (timestamp >= todayStart) {
            groups.today.push(conversation)
            return
        }

        if (timestamp >= sevenDaysAgo) {
            groups.sevenDays.push(conversation)
            return
        }

        groups.older.push(conversation)
    })

    const sortNewestFirst = (items) => [...items].sort((a, b) => getConversationTimestamp(b) - getConversationTimestamp(a))

    return [
        { label: 'Today', items: sortNewestFirst(groups.today) },
        { label: 'Recent', items: sortNewestFirst(groups.sevenDays) },
        { label: 'Older', items: sortNewestFirst(groups.older) },
    ].filter((group) => group.items.length > 0)
}

function Sidebar({ conversations, activeId, onNewChat, onSelectChat, onDeleteChat, onRenameChat, isOpen, onClose, collapsed, onCollapse, user, onShowAuth, onOpenSettings }) {
    const [editingId, setEditingId] = useState(null)
    const [editTitle, setEditTitle] = useState('')
    const editInputRef = useRef(null)
    const groupedConversations = useMemo(() => groupConversations(conversations), [conversations])

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
            <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''} ${collapsed ? 'sidebar--collapsed' : ''}`}>
                {/* Header */}
                <div className="sidebar__header">
                    <div className="sidebar__header-top">
                        <div className="sidebar__logo">
                            <span className="sidebar__logo-text">
                                <span className="sidebar__logo-r">R</span>
                                <span className="sidebar__logo-x">x</span>
                                <span className="sidebar__logo-chat">Chat</span>
                            </span>
                        </div>
                        <button className="sidebar__collapse-btn" onClick={onCollapse} title="Hide sidebar">
                            <HiOutlineChevronDoubleLeft size={16} />
                        </button>
                        <button className="sidebar__close-btn" onClick={onClose} aria-label="Close sidebar">
                            <HiOutlineXMark size={20} />
                        </button>
                    </div>
                    <button className="sidebar__new-chat" onClick={onNewChat}>
                        <HiOutlinePlus size={16} />
                        New Conversation
                    </button>
                </div>

                {/* Conversations List */}
                <nav className="sidebar__conversations">
                    {groupedConversations.map((group) => (
                        <div className="sidebar__conversation-group" key={group.label}>
                            <div className="sidebar__section-label">{group.label}</div>
                            {group.items.map((chat) => (
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
                            <button className="sidebar__settings-btn" onClick={onOpenSettings} title="Settings">
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
