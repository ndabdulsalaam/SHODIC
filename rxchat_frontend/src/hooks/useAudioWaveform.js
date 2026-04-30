import { useCallback, useEffect, useRef, useState } from 'react'

function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max)
}

function buildFlatLevels(count, level = 0.12) {
    return Array.from({ length: count }, () => level)
}

function appendLevel(levels, nextLevel) {
    return [...levels.slice(1), nextLevel]
}

function idleLevel(time = 0) {
    return clamp(0.11 + (Math.sin(time / 360) * 0.015), 0.09, 0.14)
}

export default function useAudioWaveform(barCount = 36) {
    const [levels, setLevels] = useState(() => buildFlatLevels(barCount))
    const [isActive, setIsActive] = useState(false)
    const audioContextRef = useRef(null)
    const analyserRef = useRef(null)
    const sourceRef = useRef(null)
    const streamRef = useRef(null)
    const frameRef = useRef(null)
    const levelsRef = useRef(buildFlatLevels(barCount))
    const lastSampleAtRef = useRef(0)
    const noiseFloorRef = useRef(0.012)
    const startTokenRef = useRef(0)

    const cancelFrame = useCallback(() => {
        if (frameRef.current !== null) {
            cancelAnimationFrame(frameRef.current)
            frameRef.current = null
        }
    }, [])

    const cleanupAudio = useCallback(() => {
        sourceRef.current?.disconnect()
        sourceRef.current = null
        analyserRef.current = null

        streamRef.current?.getTracks().forEach((track) => track.stop())
        streamRef.current = null

        const context = audioContextRef.current
        audioContextRef.current = null
        if (context && context.state !== 'closed') {
            context.close().catch(() => { /* ignore close errors */ })
        }
    }, [])

    const animateFallback = useCallback(() => {
        const tick = () => {
            const now = performance.now()
            if (now - lastSampleAtRef.current >= 42) {
                lastSampleAtRef.current = now
                const nextLevels = appendLevel(levelsRef.current, idleLevel(now))
                levelsRef.current = nextLevels
                setLevels(nextLevels)
            }
            frameRef.current = requestAnimationFrame(tick)
        }

        cancelFrame()
        tick()
    }, [cancelFrame])

    const resetLevels = useCallback(() => {
        const nextLevels = buildFlatLevels(barCount)
        levelsRef.current = nextLevels
        setLevels(nextLevels)
    }, [barCount])

    const pushLiveLevel = useCallback((timeData) => {
        let sumSquares = 0
        let peak = 0

        for (let index = 0; index < timeData.length; index += 1) {
            const centered = Math.abs((timeData[index] - 128) / 128)
            sumSquares += centered * centered
            peak = Math.max(peak, centered)
        }

        const rms = Math.sqrt(sumSquares / timeData.length)
        const currentNoiseFloor = noiseFloorRef.current
        if (rms < currentNoiseFloor * 1.8) {
            noiseFloorRef.current = (currentNoiseFloor * 0.96) + (rms * 0.04)
        }

        const noiseFloor = Math.max(noiseFloorRef.current, 0.006)
        const voiceRms = Math.max(0, rms - (noiseFloor * 1.25))
        const voicePeak = Math.max(0, peak - (noiseFloor * 2.4))
        const rmsLevel = clamp(voiceRms * 34, 0, 1)
        const peakLevel = clamp(voicePeak * 2.6, 0, 1)
        const voiceLevel = Math.max(rmsLevel, peakLevel * 0.72)
        const nextLevel = voiceLevel > 0.025
            ? clamp(0.18 + (Math.pow(voiceLevel, 0.72) * 1.75), 0.18, 1.9)
            : idleLevel(performance.now())

        const nextLevels = appendLevel(levelsRef.current, nextLevel)
        levelsRef.current = nextLevels
        setLevels(nextLevels)
    }, [])

    const animateLiveAudio = useCallback((analyser, timeData) => {
        const tick = () => {
            const now = performance.now()
            analyser.getByteTimeDomainData(timeData)

            if (now - lastSampleAtRef.current >= 42) {
                lastSampleAtRef.current = now
                pushLiveLevel(timeData)
            }

            frameRef.current = requestAnimationFrame(tick)
        }

        cancelFrame()
        tick()
    }, [cancelFrame, pushLiveLevel])

    const stop = useCallback(() => {
        startTokenRef.current += 1
        cancelFrame()
        cleanupAudio()
        resetLevels()
        setIsActive(false)
    }, [cancelFrame, cleanupAudio, resetLevels])

    const start = useCallback(async () => {
        const token = startTokenRef.current + 1
        startTokenRef.current = token
        cancelFrame()
        cleanupAudio()
        lastSampleAtRef.current = 0
        noiseFloorRef.current = 0.012
        resetLevels()
        setIsActive(true)
        animateFallback()

        if (
            typeof window === 'undefined'
            || !navigator.mediaDevices?.getUserMedia
            || (!window.AudioContext && !window.webkitAudioContext)
        ) {
            return
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    autoGainControl: true,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                },
            })
            if (token !== startTokenRef.current) {
                stream.getTracks().forEach((track) => track.stop())
                return
            }

            const AudioContextCtor = window.AudioContext || window.webkitAudioContext
            const context = new AudioContextCtor()
            const analyser = context.createAnalyser()
            analyser.fftSize = 1024
            analyser.smoothingTimeConstant = 0.42

            const source = context.createMediaStreamSource(stream)
            source.connect(analyser)

            audioContextRef.current = context
            analyserRef.current = analyser
            sourceRef.current = source
            streamRef.current = stream

            const timeData = new Uint8Array(analyser.fftSize)

            if (context.state === 'suspended') {
                await context.resume()
            }
            if (token !== startTokenRef.current) {
                cleanupAudio()
                return
            }
            animateLiveAudio(analyser, timeData)
        } catch {
            if (token === startTokenRef.current) {
                animateFallback()
            }
        }
    }, [animateFallback, animateLiveAudio, cancelFrame, cleanupAudio, resetLevels])

    useEffect(() => () => {
        startTokenRef.current += 1
        cancelFrame()
        cleanupAudio()
    }, [cancelFrame, cleanupAudio])

    return {
        levels,
        isActive,
        start,
        stop,
    }
}
