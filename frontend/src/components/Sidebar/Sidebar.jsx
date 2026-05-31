import { memo, useEffect, useMemo, useRef, useState } from 'react'
import { HiOutlineChatBubbleLeftRight, HiOutlinePlus, HiOutlineTrash, HiOutlinePencil, HiOutlineCheck, HiOutlineXMark, HiOutlineChevronDoubleLeft } from 'react-icons/hi2'
import { PRODUCT } from '../../config/product'
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

function Sidebar({ conversations, activeId, onNewChat, onSelectChat, onDeleteChat, onRenameChat, isOpen, onClose, collapsed, onCollapse }) {
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

    return (
        <>
            <div className={`sidebar__overlay ${isOpen ? 'sidebar__overlay--visible' : ''}`} onClick={onClose} />
            <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''} ${collapsed ? 'sidebar--collapsed' : ''}`}>
                <div className="sidebar__header">
                    <div className="sidebar__header-top">
                        <div className="sidebar__logo">
                            <span className="sidebar__logo-text">{PRODUCT.name}</span>
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
                        New Session
                    </button>
                </div>

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
            </aside>
        </>
    )
}

function sameConversationSummaries(prevConversations = [], nextConversations = []) {
    if (prevConversations.length !== nextConversations.length) return false

    return prevConversations.every((conversation, index) => {
        const nextConversation = nextConversations[index]
        return conversation.id === nextConversation.id
            && conversation.title === nextConversation.title
            && conversation.created_at === nextConversation.created_at
            && conversation.updated_at === nextConversation.updated_at
            && conversation.message_count === nextConversation.message_count
    })
}

function areSidebarPropsEqual(prevProps, nextProps) {
    return prevProps.activeId === nextProps.activeId
        && prevProps.isOpen === nextProps.isOpen
        && prevProps.collapsed === nextProps.collapsed
        && prevProps.onNewChat === nextProps.onNewChat
        && prevProps.onSelectChat === nextProps.onSelectChat
        && prevProps.onDeleteChat === nextProps.onDeleteChat
        && prevProps.onRenameChat === nextProps.onRenameChat
        && prevProps.onClose === nextProps.onClose
        && prevProps.onCollapse === nextProps.onCollapse
        && sameConversationSummaries(prevProps.conversations, nextProps.conversations)
}

export default memo(Sidebar, areSidebarPropsEqual)
