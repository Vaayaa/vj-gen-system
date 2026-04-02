import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Play, Sparkles, Download, Loader2 } from 'lucide-react'
import { useProject } from '@/hooks/useProject'
import { useUpload } from '@/hooks/useUpload'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Upload as UploadComponent } from '@/components/Upload'
import { ProgressPanel } from '@/components/Progress'
import { Waveform } from '@/components/Waveform'
import { Timeline } from '@/components/Timeline'
import { Preview } from '@/components/Preview'
import { RenderPanel } from '@/components/RenderPanel'

export default function Project() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [currentTime, setCurrentTime] = useState(0)

  const {
    project,
    isLoading,
    progress,
    isWsConnected,
    startAnalysis,
    startGeneration,
    startRender,
    refresh,
  } = useProject(id!)

  const {
    audioFile,
    lyricsFile,
    isUploading,
    uploadError,
    handleAudioChange,
    handleLyricsChange,
    upload,
  } = useUpload(id!)

  const handleUploadAndAnalyze = async () => {
    const success = await upload()
    if (success) {
      await startAnalysis()
    }
  }

  const handleGenerate = async () => {
    await startGeneration()
  }

  const handleRender = async (profile: string) => {
    await startRender(profile)
  }

  if (isLoading || !project) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  const audioDuration = project.audio_analysis?.duration || 180
  const shots = project.shot_script?.items || []
  const isRendering = project.status === 'rendering'
  const renderProgress = progress?.progress || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1">
          <h2 className="text-2xl font-bold">{project.name}</h2>
          <p className="text-muted-foreground">
            {project.description || 'VJ 生成项目'}
          </p>
        </div>
        
        {/* Action Buttons */}
        <div className="flex gap-2">
          {project.status === 'uploaded' && (
            <Button onClick={startAnalysis}>
              <Sparkles className="w-4 h-4 mr-2" />
              开始分析
            </Button>
          )}
          
          {project.status === 'script_generated' && (
            <Button onClick={handleGenerate}>
              <Play className="w-4 h-4 mr-2" />
              生成 VJ
            </Button>
          )}
          
          {project.status === 'generating' && (
            <Button disabled>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              生成中...
            </Button>
          )}
          
          {project.status === 'completed' && (
            <Button variant="outline" onClick={() => refresh()}>
              <Download className="w-4 h-4 mr-2" />
              刷新状态
            </Button>
          )}
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Upload & Controls */}
        <div className="space-y-6">
          {/* Upload Section */}
          {project.status === 'created' && (
            <Card>
              <CardHeader>
                <CardTitle>上传文件</CardTitle>
              </CardHeader>
              <CardContent>
                <UploadComponent
                  audioFile={audioFile}
                  lyricsFile={lyricsFile}
                  onAudioSelect={handleAudioChange}
                  onLyricsSelect={handleLyricsChange}
                  onUpload={handleUploadAndAnalyze}
                  isUploading={isUploading}
                  uploadError={uploadError}
                />
              </CardContent>
            </Card>
          )}

          {/* Progress */}
          {['analyzing', 'script_generated', 'generating', 'rendering'].includes(project.status) && (
            <ProgressPanel
              progress={progress}
              isConnected={isWsConnected}
              currentStatus={project.status}
            />
          )}

          {/* Analysis Results */}
          {project.audio_analysis && (
            <Card>
              <CardHeader>
                <CardTitle>音频分析</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">BPM</span>
                  <span className="font-medium">{project.audio_analysis.bpm}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">拍号</span>
                  <span className="font-medium">{project.audio_analysis.time_signature}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">时长</span>
                  <span className="font-medium">{Math.round(audioDuration)}秒</span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Render Panel */}
          {['script_generated', 'generating', 'completed'].includes(project.status) && (
            <RenderPanel
              projectId={project.id}
              projectName={project.name}
              isCompleted={project.status === 'completed'}
              onRenderStart={handleRender}
              isRendering={isRendering}
              renderProgress={renderProgress}
            />
          )}
        </div>

        {/* Middle Column - Timeline & Waveform */}
        <div className="space-y-6">
          {/* Waveform */}
          {project.audio_path && (
            <Card>
              <CardHeader>
                <CardTitle>音频波形</CardTitle>
              </CardHeader>
              <CardContent>
                <Waveform
                  duration={audioDuration}
                  currentTime={currentTime}
                  onSeek={setCurrentTime}
                  beats={project.audio_analysis?.beats?.map(b => ({
                    timestamp: b.timestamp,
                    strength: b.strength,
                  }))}
                />
              </CardContent>
            </Card>
          )}

          {/* Timeline */}
          {shots.length > 0 && (
            <Timeline
              shots={shots}
              duration={audioDuration}
              currentTime={currentTime}
            />
          )}
        </div>

        {/* Right Column - Preview */}
        <div className="space-y-6">
          <Preview
            isGenerating={project.status === 'generating'}
          />

          {/* Shot Details */}
          {shots.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>镜头脚本</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {shots.slice(0, 10).map((shot, index) => (
                    <div
                      key={shot.id}
                      className="p-3 rounded-lg bg-secondary hover:bg-secondary/80 cursor-pointer"
                      onClick={() => setCurrentTime(shot.time_start)}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium">镜头 {index + 1}</span>
                        <span className="text-xs text-muted-foreground">
                          {shot.time_start.toFixed(1)}s - {shot.time_end.toFixed(1)}s
                        </span>
                      </div>
                      {shot.lyric && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {shot.lyric}
                        </p>
                      )}
                      {shot.visual_prompt && (
                        <p className="text-xs text-muted-foreground/70 mt-1 line-clamp-2">
                          Prompt: {shot.visual_prompt}
                        </p>
                      )}
                    </div>
                  ))}
                  {shots.length > 10 && (
                    <p className="text-sm text-muted-foreground text-center py-2">
                      还有 {shots.length - 10} 个镜头...
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
