import { useCallback, useEffect, useRef, useState } from 'react'

function getSpeechRecognition() {
    if (typeof window === 'undefined') return null
    return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

function cleanTranscript(value) {
    return String(value || '').replace(/\s+/g, ' ').trim()
}

function getPreferredSpeechLanguages() {
    const browserLanguage = typeof navigator !== 'undefined' ? navigator.language : ''
    const preferred = browserLanguage?.startsWith('en') ? browserLanguage : 'en-US'
    return [...new Set([preferred, 'en-NG', 'en-GB', 'en-US'])]
}

function collectTranscript(results, resultIndex, committedTranscript) {
    let interimText = ''
    let finalText = committedTranscript

    for (let index = resultIndex; index < results.length; index += 1) {
        const result = results[index]
        const text = result[0]?.transcript || ''
        if (result.isFinal) {
            finalText = cleanTranscript(`${finalText} ${text}`)
        } else {
            interimText += `${text} `
        }
    }

    return {
        committed: finalText,
        visible: cleanTranscript(`${finalText} ${interimText}`),
    }
}

export default function useSpeechRecognition() {
    const Recognition = getSpeechRecognition()
    const [isListening, setIsListening] = useState(false)
    const [transcript, setTranscript] = useState('')
    const recognitionRef = useRef(null)
    const languageIndexRef = useRef(0)
    const languageOptionsRef = useRef(getPreferredSpeechLanguages())
    const committedTranscriptRef = useRef('')
    const transcriptHandlerRef = useRef(null)
    const restartTimerRef = useRef(null)
    const shouldListenRef = useRef(false)

    const clearRestartTimer = useCallback(() => {
        if (restartTimerRef.current) {
            window.clearTimeout(restartTimerRef.current)
            restartTimerRef.current = null
        }
    }, [])

    const stopListening = useCallback(() => {
        shouldListenRef.current = false
        clearRestartTimer()
        if (recognitionRef.current) {
            recognitionRef.current.stop()
        }
        transcriptHandlerRef.current = null
        setIsListening(false)
    }, [clearRestartTimer])

    const startListening = useCallback((onTranscript) => {
        if (!Recognition) return

        clearRestartTimer()
        shouldListenRef.current = true
        committedTranscriptRef.current = ''
        languageOptionsRef.current = getPreferredSpeechLanguages()
        languageIndexRef.current = 0

        if (recognitionRef.current) {
            recognitionRef.current.abort()
        }

        transcriptHandlerRef.current = typeof onTranscript === 'function' ? onTranscript : null

        const begin = () => {
            if (!shouldListenRef.current) return

            const lang = languageOptionsRef.current[languageIndexRef.current] || 'en-US'
            const recognition = new Recognition()
            recognition.lang = lang
            recognition.continuous = true
            recognition.interimResults = true
            recognition.maxAlternatives = 3

            recognition.onresult = (event) => {
                const nextTranscript = collectTranscript(
                    event.results,
                    event.resultIndex,
                    committedTranscriptRef.current,
                )
                committedTranscriptRef.current = nextTranscript.committed
                setTranscript(nextTranscript.visible)
                transcriptHandlerRef.current?.(nextTranscript.visible)
            }

            recognition.onerror = (event) => {
                if (event.error === 'language-not-supported') {
                    if (languageIndexRef.current >= languageOptionsRef.current.length - 1) {
                        shouldListenRef.current = false
                        setIsListening(false)
                        return
                    }
                    languageIndexRef.current += 1
                    recognition.abort()
                    begin()
                    return
                }

                if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                    shouldListenRef.current = false
                    setIsListening(false)
                }
            }

            recognition.onend = () => {
                if (shouldListenRef.current) {
                    restartTimerRef.current = window.setTimeout(begin, 140)
                    return
                }
                setIsListening(false)
            }

            recognitionRef.current = recognition
            setTranscript('')
            setIsListening(true)
            try {
                recognition.start()
            } catch {
                shouldListenRef.current = false
                setIsListening(false)
            }
        }

        begin()
    }, [Recognition, clearRestartTimer])

    useEffect(() => () => {
        shouldListenRef.current = false
        clearRestartTimer()
        if (recognitionRef.current) {
            recognitionRef.current.abort()
        }
    }, [clearRestartTimer])

    return {
        isSupported: Boolean(Recognition),
        isListening,
        transcript,
        startListening,
        stopListening,
    }
}
