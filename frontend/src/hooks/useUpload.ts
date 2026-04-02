import { useState, useCallback } from 'react'
import { useProjectStore } from '@/stores/projectStore'

export function useUpload(projectId: string) {
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [lyricsFile, setLyricsFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const { uploadFiles } = useProjectStore()

  const handleAudioChange = useCallback((file: File | null) => {
    setAudioFile(file)
    setUploadError(null)
  }, [])

  const handleLyricsChange = useCallback((file: File | null) => {
    setLyricsFile(file)
    setUploadError(null)
  }, [])

  const upload = useCallback(async () => {
    if (!audioFile) {
      setUploadError('Please select an audio file')
      return false
    }

    setIsUploading(true)
    setUploadError(null)

    try {
      await uploadFiles(projectId, audioFile, lyricsFile || undefined)
      setIsUploading(false)
      return true
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed')
      setIsUploading(false)
      return false
    }
  }, [projectId, audioFile, lyricsFile, uploadFiles])

  return {
    audioFile,
    lyricsFile,
    isUploading,
    uploadError,
    handleAudioChange,
    handleLyricsChange,
    upload,
  }
}
