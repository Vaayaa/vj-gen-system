import React, { useRef, useEffect, useState } from 'react'

interface WaveformProps {
  audioPath?: string
  duration: number
  currentTime?: number
  onSeek?: (time: number) => void
  beats?: Array<{ timestamp: number; strength: number }>
}

export function Waveform({ audioPath, duration, currentTime = 0, onSeek, beats = [] }: WaveformProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [hoverTime, setHoverTime] = useState<number | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size
    const dpr = window.devicePixelRatio || 1
    canvas.width = canvas.offsetWidth * dpr
    canvas.height = canvas.offsetHeight * dpr
    ctx.scale(dpr, dpr)

    const width = canvas.offsetWidth
    const height = canvas.offsetHeight

    // Clear canvas
    ctx.clearRect(0, 0, width, height)

    // Generate mock waveform data (in production, use actual audio analysis)
    const barCount = Math.floor(width / 3)
    const barWidth = width / barCount - 1

    // Draw waveform bars
    for (let i = 0; i < barCount; i++) {
      const x = i * (barWidth + 1)
      const barHeight = Math.random() * 0.6 + 0.2
      const normalizedHeight = barHeight * height * 0.8
      
      // Color based on current position
      const barTime = (i / barCount) * duration
      const isPast = barTime <= currentTime
      const isNearBeat = beats.some(beat => Math.abs(beat.timestamp - barTime) < 0.1)
      
      ctx.fillStyle = isPast 
        ? 'hsl(217, 91%, 60%)' 
        : isNearBeat 
        ? 'hsl(280, 60%, 60%)' 
        : 'hsl(217, 32%, 30%)'

      // Center the bar
      const y = (height - normalizedHeight) / 2
      ctx.fillRect(x, y, barWidth, normalizedHeight)
    }

    // Draw playhead
    const playheadX = (currentTime / duration) * width
    ctx.fillStyle = 'hsl(0, 84%, 60%)'
    ctx.fillRect(playheadX - 1, 0, 2, height)

    // Draw beat markers
    beats.forEach(beat => {
      const beatX = (beat.timestamp / duration) * width
      ctx.fillStyle = 'hsl(50, 100%, 50%)'
      ctx.fillRect(beatX, height - 4, 2, 4)
    })

  }, [audioPath, duration, currentTime, beats])

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas || !duration) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const time = (x / rect.width) * duration
    setHoverTime(time)
  }

  const handleMouseLeave = () => {
    setHoverTime(null)
  }

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas || !onSeek || !duration) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const time = (x / rect.width) * duration
    onSeek(time)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>
      <div className="relative">
        <canvas
          ref={canvasRef}
          className="w-full h-24 bg-secondary rounded-lg cursor-pointer"
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          onClick={handleClick}
        />
        {/* Time tooltip */}
        {hoverTime !== null && (
          <div
            className="absolute top-0 transform -translate-x-1/2 bg-background border rounded px-2 py-1 text-xs pointer-events-none"
            style={{ left: `${(hoverTime / duration) * 100}%` }}
          >
            {formatTime(hoverTime)}
          </div>
        )}
      </div>
    </div>
  )
}
