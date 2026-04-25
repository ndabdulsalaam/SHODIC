import { useCallback, useEffect, useRef, useState } from 'react'

function getSpeechRecognition() {
    if (typeof window === 'undefined') return null
    return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function collectTranscript(results) {
    let finalText = ''
    let interimText = ''

    for (let index = 0; index < results.length; index += 1) {
        const result = results[index]
        const text = result[0]?.transcript || ''
        if (result.isFinal) {
            finalText += `${text} `
        } else {
            interimText += `${text} `
        }
    }

    return `${finalText}${interimText}`.replace(/\s+/g, ' ').trim()
}

export default function useSpeechRecognition() {
    const Recognition = getSpeechRecognition()
    const [isListening, setIsListening] = useState(false)
    const [transcript, setTranscript] = useState('')
    const recognitionRef = useRef(null)
    const activeLangRef = useRef('en-NG')
    const transcriptHandlerRef = useRef(null)

    const stopListening = useCallback(() => {
        if (recognitionRef.current) {
            recognitionRef.current.stop()
        }
        transcriptHandlerRef.current = null
        setIsListening(false)
    }, [])

    const startListening = useCallback((onTranscript) => {
        if (!Recognition) return

        if (recognitionRef.current) {
            recognitionRef.current.abort()
        }

        transcriptHandlerRef.current = typeof onTranscript === 'function' ? onTranscript : null

        const begin = (lang) => {
            const recognition = new Recognition()
            activeLangRef.current = lang
            recognition.lang = lang
            recognition.continuous = true
            recognition.interimResults = true

            recognition.onresult = (event) => {
                const nextTranscript = collectTranscript(event.results)
                setTranscript(nextTranscript)
                transcriptHandlerRef.current?.(nextTranscript)
            }

            recognition.onerror = (event) => {
                if (event.error === 'language-not-supported' && activeLangRef.current !== 'en-US') {
                    begin('en-US')
                    return
                }
                setIsListening(false)
            }

            recognition.onend = () => {
                setIsListening(false)
            }

            recognitionRef.current = recognition
            setTranscript('')
            setIsListening(true)
            recognition.start()
        }

        begin('en-NG')
    }, [Recognition])

    useEffect(() => () => {
        if (recognitionRef.current) {
            recognitionRef.current.abort()
        }
    }, [])

    return {
        isSupported: Boolean(Recognition),
        isListening,
        transcript,
        startListening,
        stopListening,
    }
}
