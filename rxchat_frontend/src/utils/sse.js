function parseJsonData(data) {
    try {
        return JSON.parse(data)
    } catch {
        return null
    }
}

export function createSseParser({ onMeta, onStatus, onDone, onText }) {
    let buffer = ''
    let currentEvent = 'message'

    const handleParsedData = (eventName, data) => {
        if (eventName === 'status') {
            const parsed = parseJsonData(data)
            if (parsed) onStatus?.(parsed)
            return
        }

        if (eventName === 'meta') {
            const parsed = parseJsonData(data)
            if (parsed) onMeta?.(parsed)
            return
        }

        if (eventName === 'done') {
            const parsed = parseJsonData(data)
            if (parsed) onDone?.(parsed)
            return
        }

        const parsed = data.startsWith('{') ? parseJsonData(data) : null
        if (
            parsed
            && (parsed.conversation_id || parsed.user_message_id || parsed.edited_message_id || parsed.message_id)
        ) {
            onMeta?.(parsed)
            return
        }

        onText?.(data.replace(/\\n/g, '\n'))
    }

    const handleLine = (line) => {
        if (!line) {
            currentEvent = 'message'
            return
        }

        if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim() || 'message'
            return
        }

        if (!line.startsWith('data: ')) return

        const eventName = currentEvent
        currentEvent = 'message'
        handleParsedData(eventName, line.slice(6))
    }

    return {
        push(chunk) {
            buffer += chunk
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''
            lines.forEach(handleLine)
        },
        flush() {
            if (!buffer) return
            handleLine(buffer)
            buffer = ''
        },
    }
}

export async function readSseStream(response, handlers) {
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    const streamParser = createSseParser(handlers)

    while (true) {
        const { done, value } = await reader.read()
        if (done) break
        streamParser.push(decoder.decode(value, { stream: true }))
    }

    streamParser.push(decoder.decode())
    streamParser.flush()
}
