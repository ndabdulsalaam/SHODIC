import { useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { HiOutlinePencil, HiOutlineClipboard, HiOutlineArrowPath, HiOutlineCheck, HiOutlineXMark } from 'react-icons/hi2'
import './MessageBubble.css'

function MessageBubble({ message, index, onEdit, onResend, isLoading }) {
    const isUser = message.role === 'user'
    const [isEditing, setIsEditing] = useState(false)
    const [editText, setEditText] = useState(message.content)
    const [copied, setCopied] = useState(false)
    const time = message.created_at
        ? new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : ''

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(message.content)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch { /* fallback */ }
    }

    const handleEditStart = () => {
        setEditText(message.content)
        setIsEditing(true)
    }

    const handleEditSave = () => {
        const trimmed = editText.trim()
        if (trimmed && trimmed !== message.content && onEdit) {
            onEdit(message.id, trimmed)
        }
        setIsEditing(false)
    }

    const handleEditCancel = () => {
        setEditText(message.content)
        setIsEditing(false)
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleEditSave()
        }
        if (e.key === 'Escape') {
            handleEditCancel()
        }
    }

    return (
        <div
            className={`message message--${isUser ? 'user' : 'ai'}`}
            style={{ animationDelay: `${index * 0.05}s` }}
        >
            <div className="message__content">
                <div className="message__bubble">
                    {isEditing ? (
                        <div className="message__edit-area">
                            <textarea
                                className="message__edit-textarea"
                                value={editText}
                                onChange={(e) => setEditText(e.target.value)}
                                onKeyDown={handleKeyDown}
                                autoFocus
                                rows={3}
                            />
                            <div className="message__edit-actions">
                                <button className="message__edit-btn message__edit-btn--save" onClick={handleEditSave}>
                                    <HiOutlineCheck size={14} /> Save
                                </button>
                                <button className="message__edit-btn message__edit-btn--cancel" onClick={handleEditCancel}>
                                    <HiOutlineXMark size={14} /> Cancel
                                </button>
                            </div>
                        </div>
                    ) : isUser ? (
                        <p>{message.content}</p>
                    ) : (
                        <div className="message__markdown">
                            <Markdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    a: ({ node, ...props }) => (
                                        <a {...props} target="_blank" rel="noopener noreferrer" />
                                    ),
                                }}
                            >
                                {message.content}
                            </Markdown>
                        </div>
                    )}
                </div>

                {/* Bottom row: time + actions */}
                {!isEditing && (
                    <div className="message__bottom">
                        {time && <span className="message__time">{time}</span>}

                        {!message._streaming && (
                            <div className="message__actions">
                                <button
                                    className={`message__action-btn ${copied ? 'message__action-btn--copied' : ''}`}
                                    onClick={handleCopy}
                                    title={copied ? 'Copied!' : 'Copy'}
                                >
                                    {copied ? <HiOutlineCheck size={13} /> : <HiOutlineClipboard size={13} />}
                                </button>

                                {isUser && onEdit && (
                                    <button
                                        className="message__action-btn"
                                        onClick={handleEditStart}
                                        title="Edit message"
                                        disabled={isLoading}
                                    >
                                        <HiOutlinePencil size={13} />
                                    </button>
                                )}

                                {!isUser && onResend && (
                                    <button
                                        className="message__action-btn"
                                        onClick={() => onResend(message.id)}
                                        title="Regenerate response"
                                        disabled={isLoading}
                                    >
                                        <HiOutlineArrowPath size={13} />
                                    </button>
                                )}

                                {message._error && onResend && (
                                    <button
                                        className="message__action-btn message__action-btn--error"
                                        onClick={() => onResend(message.id)}
                                        title="Retry"
                                        disabled={isLoading}
                                    >
                                        <HiOutlineArrowPath size={13} /> Retry
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}

export default MessageBubble
