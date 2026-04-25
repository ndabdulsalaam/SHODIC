import { Children, isValidElement, memo, useMemo, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import {
    HiOutlineArrowPath,
    HiOutlineCheck,
    HiOutlineChevronLeft,
    HiOutlineChevronRight,
    HiOutlineClipboard,
    HiOutlineDocument,
    HiOutlinePaperAirplane,
    HiOutlinePencil,
    HiOutlineXMark,
} from 'react-icons/hi2'
import './MessageBubble.css'

const sanitizedHtmlSchema = {
    ...defaultSchema,
    clobberPrefix: 'rxchat-user-content-',
    tagNames: [
        'a', 'b', 'blockquote', 'br', 'code', 'del', 'div', 'em', 'h1', 'h2',
        'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'li', 'ol', 'p', 'pre', 'span',
        'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'th', 'thead', 'tr',
        'ul',
    ],
    attributes: {
        '*': ['ariaLabel', 'ariaLabelledBy', 'title'],
        a: ['href', 'title'],
        code: ['className'],
        td: ['align'],
        th: ['align'],
    },
    protocols: {
        href: ['http', 'https', 'mailto', 'tel'],
    },
}

function extractText(node) {
    if (node === null || node === undefined || typeof node === 'boolean') return ''
    if (typeof node === 'string' || typeof node === 'number') return String(node)
    if (Array.isArray(node)) return node.map(extractText).join(' ')
    if (isValidElement(node)) return extractText(node.props.children)
    return ''
}

function collectRows(node, rows = []) {
    Children.forEach(node, (child) => {
        if (!isValidElement(child)) return

        if (child.type === 'tr') {
            const cells = []
            Children.forEach(child.props.children, (cell) => {
                if (!isValidElement(cell)) return
                if (cell.type === 'th' || cell.type === 'td') {
                    cells.push(extractText(cell.props.children).replace(/\s+/g, ' ').trim())
                }
            })
            if (cells.length) rows.push(cells)
            return
        }

        collectRows(child.props.children, rows)
    })

    return rows
}

function buildTableColumns(children) {
    const rows = collectRows(children)
    const columnCount = Math.max(0, ...rows.map((row) => row.length))
    if (!columnCount) return []

    const columns = Array.from({ length: columnCount }, (_, index) => {
        const values = rows.map((row) => row[index] || '').filter(Boolean)
        const header = rows[0]?.[index] || ''
        const headerLower = header.toLowerCase()
        const lengths = values.map((value) => value.length)
        const maxLength = Math.max(header.length, ...lengths, 1)
        const averageLength = lengths.length
            ? lengths.reduce((sum, length) => sum + length, 0) / lengths.length
            : header.length
        const mostlyShort = values.length > 0 && values.every((value) => value.length <= 18)
        const mostlySymbols = values.length > 0 && values.every((value) => /^[↑↓↔+\-–—=<>≤≥*\s.,()%/]+$/.test(value))
        const isCategoryColumn = index === 0 || headerLower.includes('category') || headerLower.includes('system')
        const isFrequencyColumn = headerLower.includes('frequency')

        let weight = Math.max(header.length * 1.15, averageLength * 1.7, Math.min(maxLength, 80))

        if (mostlySymbols) weight = Math.max(header.length * 0.65, 5)
        else if (mostlyShort && !isCategoryColumn && !isFrequencyColumn) weight *= 0.72

        if (maxLength >= 48 || averageLength >= 30) weight *= 1.3
        if (isCategoryColumn) weight = Math.max(weight, 30)
        if (isFrequencyColumn) weight = Math.max(weight, 28)

        return {
            index,
            maxLength,
            isCategoryColumn,
            isFrequencyColumn,
            weight: Math.min(Math.max(weight, 8), 72),
        }
    })

    const totalWeight = columns.reduce((sum, column) => sum + column.weight, 0)

    return columns.map((column) => ({
        ...column,
        width: `${((column.weight / totalWeight) * 100).toFixed(2)}%`,
        className: [
            column.maxLength >= 48 ? 'message__table-col--wide' : '',
            column.isCategoryColumn ? 'message__table-col--category' : '',
            column.isFrequencyColumn ? 'message__table-col--frequency' : '',
        ].filter(Boolean).join(' '),
    }))
}

function SmartMarkdownTable({ children, ...props }) {
    const columns = useMemo(() => buildTableColumns(children), [children])
    const tableStyle = {
        ...props.style,
        '--rxchat-table-columns': columns.length || 1,
    }

    return (
        <div className="message__table-wrapper">
            <table {...props} style={tableStyle}>
                {columns.length > 0 && (
                    <colgroup>
                        {columns.map((column) => (
                            <col
                                key={column.index}
                                className={column.className}
                                style={{ width: column.width }}
                            />
                        ))}
                    </colgroup>
                )}
                {children}
            </table>
        </div>
    )
}

function MessageBubble({ message, index, onEdit, onResend, onVariantChange, resendMessageId, isLoading }) {
    const isUser = message.role === 'user'
    const attachments = Array.isArray(message.attachments) ? message.attachments : []
    const hasAttachments = attachments.length > 0
    const hasEditableAttachments = hasAttachments
        && attachments.every((attachment) => attachment.kind === 'image' && attachment.preview_data_url)
    const canEdit = isUser && onEdit && (!hasAttachments || hasEditableAttachments)
    const variantNavigation = message._variantNavigation
    const hasVariants = Boolean(variantNavigation && variantNavigation.total > 1)
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
        const changed = trimmed !== message.content
        if (changed && (trimmed || hasEditableAttachments) && onEdit) {
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
            style={{ animationDelay: `${Math.min(index * 0.05, 0.5)}s` }}
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
                                <button
                                    className="message__edit-btn message__edit-btn--cancel"
                                    onClick={handleEditCancel}
                                    aria-label="Cancel edit"
                                    data-tooltip="Cancel edit"
                                >
                                    <HiOutlineXMark size={18} />
                                </button>
                                <button
                                    className="message__edit-btn message__edit-btn--send"
                                    onClick={handleEditSave}
                                    aria-label="Send edited message"
                                    data-tooltip="Send edit"
                                >
                                    <HiOutlinePaperAirplane size={17} />
                                </button>
                            </div>
                        </div>
                    ) : isUser ? (
                        <div className="message__user-body">
                            {hasAttachments && (
                                <div className="message__attachments">
                                    {attachments.map((attachment, attachmentIndex) => (
                                        <div
                                            className={`message__attachment message__attachment--${attachment.kind}`}
                                            key={`${attachment.name}-${attachmentIndex}`}
                                        >
                                            {attachment.kind === 'image' && attachment.preview_data_url ? (
                                                <img src={attachment.preview_data_url} alt={attachment.name} />
                                            ) : (
                                                <HiOutlineDocument size={17} />
                                            )}
                                            <span>{attachment.name}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                            {message.content && <p>{message.content}</p>}
                        </div>
                    ) : (
                        <div className="message__markdown">
                            <Markdown
                                remarkPlugins={[remarkGfm]}
                                rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizedHtmlSchema]]}
                                components={{
                                    a: ({ node, ...props }) => {
                                        void node
                                        return <a {...props} target="_blank" rel="noopener noreferrer" />
                                    },
                                    table: ({ node, ...props }) => {
                                        void node
                                        return <SmartMarkdownTable {...props} />
                                    },
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
                                    aria-label={copied ? 'Copied' : 'Copy message'}
                                    data-tooltip={copied ? 'Copied' : 'Copy message'}
                                >
                                    {copied ? <HiOutlineCheck size={13} /> : <HiOutlineClipboard size={13} />}
                                </button>

                                {canEdit && (
                                    <button
                                        className="message__action-btn"
                                        onClick={handleEditStart}
                                        aria-label="Edit message"
                                        data-tooltip="Edit message"
                                        disabled={isLoading}
                                    >
                                        <HiOutlinePencil size={13} />
                                    </button>
                                )}

                                {isUser && hasVariants && onVariantChange && (
                                    <div className="message__variant-nav" aria-label="Message edit versions">
                                        <button
                                            className="message__action-btn message__variant-btn"
                                            onClick={() => onVariantChange(variantNavigation.groupId, variantNavigation.index - 1)}
                                            disabled={isLoading || variantNavigation.index === 0}
                                            aria-label="Previous edit"
                                            data-tooltip="Previous edit"
                                        >
                                            <HiOutlineChevronLeft size={15} />
                                        </button>
                                        <span className="message__variant-count">
                                            {variantNavigation.index + 1}/{variantNavigation.total}
                                        </span>
                                        <button
                                            className="message__action-btn message__variant-btn"
                                            onClick={() => onVariantChange(variantNavigation.groupId, variantNavigation.index + 1)}
                                            disabled={isLoading || variantNavigation.index === variantNavigation.total - 1}
                                            aria-label="Next edit"
                                            data-tooltip="Next edit"
                                        >
                                            <HiOutlineChevronRight size={15} />
                                        </button>
                                    </div>
                                )}

                                {!isUser && !message._error && onResend && resendMessageId && (
                                    <button
                                        className="message__action-btn"
                                        onClick={() => onResend(resendMessageId)}
                                        aria-label="Regenerate response"
                                        data-tooltip="Regenerate response"
                                        disabled={isLoading}
                                    >
                                        <HiOutlineArrowPath size={13} />
                                    </button>
                                )}

                                {message._error && onResend && resendMessageId && (
                                    <button
                                        className="message__action-btn message__action-btn--error"
                                        onClick={() => onResend(resendMessageId)}
                                        aria-label="Retry response"
                                        data-tooltip="Retry response"
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

export default memo(MessageBubble)
