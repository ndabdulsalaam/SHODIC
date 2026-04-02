import { HiOutlineUser } from 'react-icons/hi2'
import './MessageBubble.css'

function MessageBubble({ message, index }) {
    const isUser = message.role === 'user'
    const time = message.timestamp
        ? new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : ''

    return (
        <div
            className={`message message--${isUser ? 'user' : 'ai'}`}
            style={{ animationDelay: `${index * 0.05}s` }}
        >
            <div className={`message__avatar message__avatar--${isUser ? 'user' : 'ai'}`}>
                {isUser ? <HiOutlineUser size={16} /> : 'Rx'}
            </div>
            <div className="message__content">
                <div className="message__bubble">
                    {formatMessage(message.content)}
                </div>
                {time && (
                    <div className="message__meta">
                        <span>{time}</span>
                    </div>
                )}
            </div>
        </div>
    )
}

function formatMessage(text) {
    // Simple markdown-like formatting
    const lines = text.split('\n')
    const elements = []
    let listItems = []

    lines.forEach((line, i) => {
        const trimmed = line.trim()

        if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
            listItems.push(trimmed.slice(2))
        } else {
            if (listItems.length > 0) {
                elements.push(
                    <ul key={`list-${i}`}>
                        {listItems.map((item, j) => (
                            <li key={j}>{processInline(item)}</li>
                        ))}
                    </ul>
                )
                listItems = []
            }

            if (trimmed.startsWith('⚠️') || trimmed.startsWith('Warning:') || trimmed.startsWith('CAUTION:')) {
                elements.push(
                    <div key={i} className="warning">{processInline(trimmed)}</div>
                )
            } else if (trimmed) {
                elements.push(<p key={i}>{processInline(trimmed)}</p>)
            }
        }
    })

    if (listItems.length > 0) {
        elements.push(
            <ul key="list-end">
                {listItems.map((item, j) => (
                    <li key={j}>{processInline(item)}</li>
                ))}
            </ul>
        )
    }

    return elements
}

function processInline(text) {
    // Bold text: **text**
    const parts = text.split(/\*\*(.*?)\*\*/g)
    return parts.map((part, i) =>
        i % 2 === 1 ? <strong key={i}>{part}</strong> : part
    )
}

export default MessageBubble
