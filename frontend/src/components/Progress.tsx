import React from 'react'
import { CheckCircle, Circle, Loader2, AlertCircle } from 'lucide-react'
import { Progress } from './ui/Progress'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'

interface ProgressUpdate {
  type: string
  step: string
  message: string
  progress: number
  timestamp: string
}

interface ProgressProps {
  progress?: ProgressUpdate
  isConnected: boolean
  currentStatus: string
}

const PIPELINE_STEPS = [
  { key: 'audio_analysis', label: '音频分析', icon: '🎵' },
  { key: 'beat_detection', label: '节拍检测', icon: '🥁' },
  { key: 'lyric_parsing', label: '歌词解析', icon: '📝' },
  { key: 'shot_script_generation', label: '生成镜头脚本', icon: '🎬' },
  { key: 'keyframe_generation', label: '生成关键帧', icon: '🖼️' },
  { key: 'video_synthesis', label: '合成视频', icon: '🎥' },
  { key: 'timeline_compilation', label: '编排时间线', icon: '📋' },
  { key: 'render_preparation', label: '准备渲染', icon: '⚙️' },
  { key: 'rendering', label: '渲染输出', icon: '🔥' },
]

export function ProgressPanel({ progress, isConnected, currentStatus }: ProgressProps) {
  const currentStep = progress?.step || ''
  const currentProgress = progress?.progress || 0
  
  const getStepStatus = (stepKey: string) => {
    const stepIndex = PIPELINE_STEPS.findIndex(s => s.key === stepKey)
    const currentIndex = PIPELINE_STEPS.findIndex(s => s.key === currentStep)
    
    if (currentIndex === -1) {
      return 'pending'
    }
    
    if (stepIndex < currentIndex) {
      return 'completed'
    } else if (stepIndex === currentIndex) {
      return 'running'
    } else {
      return 'pending'
    }
  }

  const getIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'running':
        return <Loader2 className="w-4 h-4 text-primary animate-spin" />
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-destructive" />
      default:
        return <Circle className="w-4 h-4 text-muted-foreground" />
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>处理进度</span>
          <div className="flex items-center gap-2 text-sm font-normal">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            <span className="text-muted-foreground">
              {isConnected ? '实时连接' : '连接断开'}
            </span>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Progress */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">总体进度</span>
            <span className="font-medium">{currentProgress}%</span>
          </div>
          <Progress value={currentProgress} className="h-3" />
        </div>

        {/* Current Message */}
        {progress?.message && (
          <div className="p-3 rounded-lg bg-primary/10 text-primary text-sm">
            {progress.message}
          </div>
        )}

        {/* Pipeline Steps */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-muted-foreground">处理阶段</h4>
          <div className="grid grid-cols-2 gap-2">
            {PIPELINE_STEPS.map((step) => {
              const status = getStepStatus(step.key)
              return (
                <div
                  key={step.key}
                  className={`flex items-center gap-2 p-2 rounded-lg transition-colors ${
                    status === 'running'
                      ? 'bg-primary/10'
                      : status === 'completed'
                      ? 'bg-green-500/10'
                      : 'bg-secondary'
                  }`}
                >
                  <span>{step.icon}</span>
                  {getIcon(status)}
                  <span className={`text-sm ${
                    status === 'completed' ? 'text-green-500' :
                    status === 'running' ? 'text-primary font-medium' :
                    'text-muted-foreground'
                  }`}>
                    {step.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Status Badge */}
        <div className="flex items-center justify-center pt-4 border-t">
          <div className={`px-4 py-2 rounded-full text-sm font-medium ${
            currentStatus === 'completed' ? 'bg-green-500/20 text-green-500' :
            currentStatus === 'failed' ? 'bg-destructive/20 text-destructive' :
            currentStatus === 'analyzing' || currentStatus === 'generating' || currentStatus === 'rendering'
              ? 'bg-primary/20 text-primary' :
              'bg-secondary text-muted-foreground'
          }`}>
            {currentStatus === 'analyzing' ? '分析中...' :
             currentStatus === 'generating' ? '生成中...' :
             currentStatus === 'rendering' ? '渲染中...' :
             currentStatus === 'completed' ? '已完成' :
             currentStatus === 'failed' ? '失败' :
             currentStatus}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
