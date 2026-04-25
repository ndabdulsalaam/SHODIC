import { useState, useRef, useEffect } from 'react'
import {
    HiOutlineCamera,
    HiOutlineDocument,
    HiOutlineMicrophone,
    HiOutlinePaperAirplane,
    HiOutlinePaperClip,
    HiOutlinePhoto,
    HiOutlineStopCircle,
    HiOutlineXMark,
    HiMiniStop,
} from 'react-icons/hi2'
import useSpeechRecognition from '../../hooks/useSpeechRecognition'
import './ChatInput.css'

const MAX_ATTACHMENTS = 3
const MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

const IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp'])
const FILE_TYPES = new Set([
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
])

const EXTENSION_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls': 'application/vnd.ms-excel',
}

function getExtension(fileName) {
    const dotIndex = fileName.lastIndexOf('.')
    return dotIndex >= 0 ? fileName.slice(dotIndex).toLowerCase() : ''
}

function readFileAsDataUrl(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result)
        reader.onerror = () => reject(reader.error)
        reader.readAsDataURL(file)
    })
}

function createImagePreview(dataUrl) {
    return new Promise((resolve) => {
        const image = new Image()
        image.onload = () => {
            const maxSide = 420
            const scale = Math.min(1, maxSide / Math.max(image.width, image.height))
            const width = Math.max(1, Math.round(image.width * scale))
            const height = Math.max(1, Math.round(image.height * scale))
            const canvas = document.createElement('canvas')
            canvas.width = width
            canvas.height = height
            const context = canvas.getContext('2d')
            if (!context) {
                resolve('')
                return
            }
            context.drawImage(image, 0, 0, width, height)
            resolve(canvas.toDataURL('image/jpeg', 0.78))
        }
        image.onerror = () => resolve('')
        image.src = dataUrl
    })
}

function normalizeDataUrlMime(dataUrl, type) {
    if (!type || typeof dataUrl !== 'string') return dataUrl
    return dataUrl.replace(/^data:[^;]*;base64,/, `data:${type};base64,`)
}

function getAttachmentKind(type) {
    if (IMAGE_TYPES.has(type)) return 'image'
    if (FILE_TYPES.has(type)) return 'file'
    return ''
}

function ChatInput({ onSend, isLoading, onStop, prefillText }) {
    const [text, setText] = useState(prefillText || '')
    const [attachments, setAttachments] = useState([])
    const [attachMenuOpen, setAttachMenuOpen] = useState(false)
    const [error, setError] = useState('')
    const textareaRef = useRef(null)
    const menuRef = useRef(null)
    const cameraInputRef = useRef(null)
    const imageInputRef = useRef(null)
    const fileInputRef = useRef(null)
    const dictationBaseRef = useRef('')
    const {
        isSupported: speechSupported,
        isListening,
        startListening,
        stopListening,
    } = useSpeechRecognition()

    useEffect(() => {
        if (prefillText) {
            setTimeout(() => textareaRef.current?.focus(), 0)
        }
    }, [prefillText])

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
        }
    }, [text])

    useEffect(() => {
        const handlePointerDown = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setAttachMenuOpen(false)
            }
        }

        document.addEventListener('pointerdown', handlePointerDown)
        return () => document.removeEventListener('pointerdown', handlePointerDown)
    }, [])

    const handleSubmit = () => {
        const trimmed = text.trim()
        if ((!trimmed && attachments.length === 0) || isLoading) return
        onSend({
            text: trimmed,
            attachments,
        })
        setText('')
        setAttachments([])
        setError('')
        setAttachMenuOpen(false)
        if (isListening) stopListening()
    }

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        }
    }

    const handleFilesSelected = async (fileList) => {
        const files = Array.from(fileList || [])
        if (!files.length) return

        setAttachMenuOpen(false)
        setError('')
        const slotsLeft = MAX_ATTACHMENTS - attachments.length
        if (slotsLeft <= 0) {
            setError(`Attach up to ${MAX_ATTACHMENTS} files per message.`)
            return
        }

        const selected = files.slice(0, slotsLeft)
        if (files.length > slotsLeft) {
            setError(`Only ${slotsLeft} more attachment${slotsLeft === 1 ? '' : 's'} can be added.`)
        }

        const nextAttachments = []
        for (const file of selected) {
            const extension = getExtension(file.name)
            const type = file.type || EXTENSION_TYPES[extension] || ''
            const kind = getAttachmentKind(type)

            if (!kind || extension === '.doc') {
                setError(`${file.name} is not a supported file type.`)
                continue
            }

            if (file.size > MAX_ATTACHMENT_BYTES) {
                setError(`${file.name} exceeds the 10 MB upload limit.`)
                continue
            }

            try {
                const dataUrl = normalizeDataUrlMime(await readFileAsDataUrl(file), type)
                const previewDataUrl = kind === 'image' ? await createImagePreview(dataUrl) : ''
                nextAttachments.push({
                    id: `${file.name}-${file.size}-${file.lastModified}-${globalThis.crypto?.randomUUID?.() || Date.now()}`,
                    kind,
                    name: file.name,
                    type,
                    data_url: dataUrl,
                    preview_data_url: previewDataUrl,
                    size_bytes: file.size,
                })
            } catch {
                setError(`Could not read ${file.name}.`)
            }
        }

        if (nextAttachments.length) {
            setAttachments((current) => [...current, ...nextAttachments].slice(0, MAX_ATTACHMENTS))
        }

        if (cameraInputRef.current) cameraInputRef.current.value = ''
        if (imageInputRef.current) imageInputRef.current.value = ''
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    const handleRemoveAttachment = (id) => {
        setAttachments((current) => current.filter((attachment) => attachment.id !== id))
        setError('')
    }

    const handleMicClick = () => {
        if (isListening) {
            stopListening()
            return
        }
        dictationBaseRef.current = text.trimEnd() ? `${text.trimEnd()} ` : ''
        startListening((nextTranscript) => {
            setText(`${dictationBaseRef.current}${nextTranscript}`.trimStart())
        })
    }

    const canSend = text.trim().length > 0 || attachments.length > 0
    const slotsLeft = MAX_ATTACHMENTS - attachments.length
    const handleAttachOptionClick = (inputRef) => {
        setAttachMenuOpen(false)
        inputRef.current?.click()
    }

    return (
        <div className="chat-input-shell">
            <div className="chat-input">
                {attachments.length > 0 && (
                    <div className="chat-input__previews" aria-label="Selected attachments">
                        {attachments.map((attachment) => (
                            <div
                                className={`chat-input__preview chat-input__preview--${attachment.kind}`}
                                key={attachment.id}
                            >
                                {attachment.kind === 'image' ? (
                                    <img src={attachment.preview_data_url || attachment.data_url} alt="" />
                                ) : (
                                    <HiOutlineDocument size={18} />
                                )}
                                <span>{attachment.name}</span>
                                <button
                                    type="button"
                                    onClick={() => handleRemoveAttachment(attachment.id)}
                                    aria-label={`Remove ${attachment.name}`}
                                    title={`Remove ${attachment.name}`}
                                >
                                    <HiOutlineXMark size={15} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {error && <div className="chat-input__error" role="alert">{error}</div>}

                <div className="chat-input__composer">
                    <div className="chat-input__attach-wrap" ref={menuRef}>
                        <button
                            type="button"
                            className="chat-input__icon-btn"
                            onClick={() => setAttachMenuOpen((open) => !open)}
                            disabled={isLoading || slotsLeft <= 0}
                            aria-label="Attach files"
                            title={slotsLeft <= 0 ? 'Attachment limit reached' : 'Attach files'}
                        >
                            <HiOutlinePaperClip size={20} />
                        </button>
                        {attachMenuOpen && (
                            <div className="chat-input__attach-menu">
                                <button
                                    type="button"
                                    className="chat-input__attach-menu-camera"
                                    onClick={() => handleAttachOptionClick(cameraInputRef)}
                                >
                                    <HiOutlineCamera size={17} />
                                    Take photo
                                </button>
                                <button type="button" onClick={() => handleAttachOptionClick(imageInputRef)}>
                                    <HiOutlinePhoto size={17} />
                                    Choose image
                                </button>
                                <button type="button" onClick={() => handleAttachOptionClick(fileInputRef)}>
                                    <HiOutlineDocument size={17} />
                                    Choose file
                                </button>
                            </div>
                        )}
                    </div>

                    <textarea
                        ref={textareaRef}
                        className="chat-input__textarea"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask about medications, interactions, side effects..."
                        rows={1}
                        aria-label="Type your message"
                    />

                    {speechSupported && (
                        <button
                            type="button"
                            className={`chat-input__icon-btn ${isListening ? 'chat-input__icon-btn--recording' : ''}`}
                            onClick={handleMicClick}
                            disabled={isLoading}
                            aria-label={isListening ? 'Stop dictation' : 'Start dictation'}
                            title={isListening ? 'Tap to stop dictation' : 'Start dictation'}
                        >
                            {isListening ? <HiMiniStop size={18} /> : <HiOutlineMicrophone size={20} />}
                        </button>
                    )}

                    {isLoading ? (
                        <button
                            className="chat-input__stop"
                            onClick={onStop}
                            aria-label="Stop generating"
                            title="Stop generating"
                        >
                            <HiOutlineStopCircle size={20} />
                        </button>
                    ) : (
                        <button
                            className={`chat-input__send ${canSend ? 'chat-input__send--active' : ''}`}
                            onClick={handleSubmit}
                            disabled={!canSend}
                            aria-label="Send message"
                            title="Send message"
                        >
                            <HiOutlinePaperAirplane size={18} />
                        </button>
                    )}
                </div>
            </div>

            <input
                ref={cameraInputRef}
                className="chat-input__file-input"
                type="file"
                accept="image/*"
                capture="environment"
                onChange={(event) => handleFilesSelected(event.target.files)}
            />
            <input
                ref={imageInputRef}
                className="chat-input__file-input"
                type="file"
                accept=".jpg,.jpeg,.png,.gif,.webp,image/jpeg,image/png,image/gif,image/webp"
                multiple
                onChange={(event) => handleFilesSelected(event.target.files)}
            />
            <input
                ref={fileInputRef}
                className="chat-input__file-input"
                type="file"
                accept=".pdf,.docx,.pptx,.xls,.xlsx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
                multiple
                onChange={(event) => handleFilesSelected(event.target.files)}
            />
        </div>
    )
}

export default ChatInput
