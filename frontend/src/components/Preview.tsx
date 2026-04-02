import React, { useEffect, useRef, useState } from 'react'
import videojs from 'video.js'
import 'video.js/dist/video-js.css'
import { Play, Pause, Volume2, Maximize, Settings } from 'lucide-react'
import { Button } from './ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'

interface PreviewProps {
  videoUrl?: string
  posterUrl?: string
  isGenerating?: boolean
}

export function Preview({ videoUrl, posterUrl, isGenerating }: PreviewProps) {
  const videoRef = useRef<HTMLDivElement>(null)
  const playerRef = useRef<ReturnType<typeof videojs> | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(0.8)

  useEffect(() => {
    if (!videoRef.current || !videoUrl) return

    // Initialize video.js player
    const player = videojs(videoRef.current, {
      controls: false,
      autoplay: false,
      preload: 'auto',
      fluid: true,
      poster: posterUrl,
      sources: [{
        src: videoUrl,
        type: 'video/mp4',
      }],
    })

    playerRef.current = player

    player.on('play', () => setIsPlaying(true))
    player.on('pause', () => setIsPlaying(false))
    player.on('timeupdate', () => {
      setCurrentTime(player.currentTime() || 0)
    })
    player.on('loadedmetadata', () => {
      setDuration(player.duration() || 0)
    })

    return () => {
      if (playerRef.current) {
        playerRef.current.dispose()
        playerRef.current = null
      }
    }
  }, [videoUrl, posterUrl])

  const togglePlay = () => {
    if (!playerRef.current) return
    if (isPlaying) {
      playerRef.current.pause()
    } else {
      playerRef.current.play()
    }
  }

  const handleSeek = (time: number) => {
    if (!playerRef.current) return
    playerRef.current.currentTime(time)
  }

  const handleVolumeChange = (newVolume: number) => {
    if (!playerRef.current) return
    setVolume(newVolume)
    playerRef.current.volume(newVolume)
  }

  const toggleFullscreen = () => {
    if (!playerRef.current) return
    playerRef.current.requestFullscreen()
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Mock generation progress
  const mockProgress = isGenerating ? Math.min(currentTime / duration * 100, 95) : (currentTime / duration * 100)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>预览</span>
          {isGenerating && (
            <span className="text-xs bg-primary/20 text-primary px-2 py-1 rounded-full">
              生成中 {Math.round(mockProgress)}%
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative rounded-lg overflow-hidden bg-black aspect-video">
          {videoUrl ? (
            <>
              <div data-vjs-player ref={videoRef} className="w-full h-full" />
              
              {/* Custom controls overlay */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
                {/* Progress bar */}
                <div className="h-1 bg-white/30 rounded-full mb-3 cursor-pointer"
                     onClick={(e) => {
                       const rect = e.currentTarget.getBoundingClientRect()
                       const percent = (e.clientX - rect.left) / rect.width
                       handleSeek(percent * duration)
                     }}>
                  <div
                    className="h-full bg-primary rounded-full"
                    style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
                  />
                </div>

                {/* Controls */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={togglePlay}
                      className="text-white hover:text-white hover:bg-white/20"
                    >
                      {isPlaying ? (
                        <Pause className="w-5 h-5" />
                      ) : (
                        <Play className="w-5 h-5" />
                      )}
                    </Button>
                    
                    <div className="flex items-center gap-1 text-white text-sm">
                      <Volume2 className="w-4 h-4" />
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={volume}
                        onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                        className="w-16 accent-primary"
                      />
                    </div>
                    
                    <span className="text-white text-sm ml-2">
                      {formatTime(currentTime)} / {formatTime(duration)}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-white hover:text-white hover:bg-white/20"
                    >
                      <Settings className="w-5 h-5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={toggleFullscreen}
                      className="text-white hover:text-white hover:bg-white/20"
                    >
                      <Maximize className="w-5 h-5" />
                    </Button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center mb-4">
                <Play className="w-8 h-8" />
              </div>
              <p>暂无预览</p>
              <p className="text-sm">完成生成后可预览</p>
            </div>
          )}

          {/* Generating overlay */}
          {isGenerating && (
            <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin w-12 h-12 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4" />
                <p className="text-white font-medium">正在生成视频...</p>
                <p className="text-white/70 text-sm mt-1">请稍候</p>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
