import React, { useCallback, useState } from 'react'
import { Upload, Music, FileText, X } from 'lucide-react'
import { Button } from './ui/Button'

interface UploadProps {
  onAudioSelect: (file: File) => void
  onLyricsSelect: (file: File) => void
  onUpload: () => Promise<void>
  audioFile: File | null
  lyricsFile: File | null
  isUploading: boolean
  uploadError: string | null
}

export function Upload({
  onAudioSelect,
  onLyricsSelect,
  onUpload,
  audioFile,
  lyricsFile,
  isUploading,
  uploadError,
}: UploadProps) {
  const [isDraggingAudio, setIsDraggingAudio] = useState(false)
  const [isDraggingLyrics, setIsDraggingLyrics] = useState(false)

  const handleAudioDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDraggingAudio(true)
  }, [])

  const handleAudioDragLeave = useCallback(() => {
    setIsDraggingAudio(false)
  }, [])

  const handleAudioDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDraggingAudio(false)
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('audio/')) {
      onAudioSelect(file)
    }
  }, [onAudioSelect])

  const handleLyricsDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDraggingLyrics(true)
  }, [])

  const handleLyricsDragLeave = useCallback(() => {
    setIsDraggingLyrics(false)
  }, [])

  const handleLyricsDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDraggingLyrics(false)
    const file = e.dataTransfer.files[0]
    if (file && (file.name.endsWith('.txt') || file.name.endsWith('.lrc'))) {
      onLyricsSelect(file)
    }
  }, [onLyricsSelect])

  return (
    <div className="space-y-6">
      {/* Audio Upload */}
      <div
        className={`drop-zone ${isDraggingAudio ? 'active' : ''}`}
        onDragOver={handleAudioDragOver}
        onDragLeave={handleAudioDragLeave}
        onDrop={handleAudioDrop}
      >
        <input
          type="file"
          accept="audio/*"
          onChange={(e) => onAudioSelect(e.target.files?.[0] || null)}
          className="hidden"
          id="audio-upload"
        />
        <label htmlFor="audio-upload" className="cursor-pointer flex flex-col items-center gap-3">
          {audioFile ? (
            <>
              <div className="flex items-center gap-2 text-primary">
                <Music className="w-8 h-8" />
                <span className="font-medium">{audioFile.name}</span>
                <button
                  onClick={(e) => {
                    e.preventDefault()
                    onAudioSelect(null as any)
                  }}
                  className="ml-2 p-1 hover:bg-destructive/20 rounded"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <span className="text-sm text-muted-foreground">
                {(audioFile.size / (1024 * 1024)).toFixed(2)} MB
              </span>
            </>
          ) : (
            <>
              <Upload className="w-8 h-8 text-muted-foreground" />
              <div className="text-center">
                <p className="font-medium">拖放音频文件或点击选择</p>
                <p className="text-sm text-muted-foreground mt-1">
                  支持 MP3, WAV, FLAC, M4A 格式
                </p>
              </div>
            </>
          )}
        </label>
      </div>

      {/* Lyrics Upload */}
      <div
        className={`drop-zone ${isDraggingLyrics ? 'active' : ''}`}
        onDragOver={handleLyricsDragOver}
        onDragLeave={handleLyricsDragLeave}
        onDrop={handleLyricsDrop}
      >
        <input
          type="file"
          accept=".txt,.lrc"
          onChange={(e) => onLyricsSelect(e.target.files?.[0] || null)}
          className="hidden"
          id="lyrics-upload"
        />
        <label htmlFor="lyrics-upload" className="cursor-pointer flex flex-col items-center gap-3">
          {lyricsFile ? (
            <>
              <div className="flex items-center gap-2 text-primary">
                <FileText className="w-8 h-8" />
                <span className="font-medium">{lyricsFile.name}</span>
                <button
                  onClick={(e) => {
                    e.preventDefault()
                    onLyricsSelect(null as any)
                  }}
                  className="ml-2 p-1 hover:bg-destructive/20 rounded"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <span className="text-sm text-muted-foreground">
                {(lyricsFile.size / 1024).toFixed(2)} KB
              </span>
            </>
          ) : (
            <>
              <FileText className="w-8 h-8 text-muted-foreground" />
              <div className="text-center">
                <p className="font-medium">拖放歌词文件或点击选择（可选）</p>
                <p className="text-sm text-muted-foreground mt-1">
                  支持 TXT, LRC 格式
                </p>
              </div>
            </>
          )}
        </label>
      </div>

      {/* Error Message */}
      {uploadError && (
        <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
          {uploadError}
        </div>
      )}

      {/* Upload Button */}
      <Button
        onClick={onUpload}
        disabled={!audioFile || isUploading}
        className="w-full"
        size="lg"
      >
        {isUploading ? (
          <>
            <span className="animate-pulse mr-2">上传中...</span>
          </>
        ) : (
          <>
            <Upload className="w-4 h-4 mr-2" />
            开始分析
          </>
        )}
      </Button>
    </div>
  )
}
