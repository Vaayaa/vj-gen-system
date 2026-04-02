import React, { useState, useEffect } from 'react'
import { Download, Monitor, Smartphone, Square, RectangleHorizontal } from 'lucide-react'
import { Button } from './ui/Button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/Card'
import { Progress } from './ui/Progress'
import { api, RenderProfile } from '@/api/client'

interface RenderPanelProps {
  projectId: string
  projectName: string
  isCompleted: boolean
  onRenderStart: (profile: string) => void
  isRendering: boolean
  renderProgress?: number
}

const PROFILE_ICONS: Record<string, React.ReactNode> = {
  '1080p': <Monitor className="w-6 h-6" />,
  '1080p_vertical': <Smartphone className="w-6 h-6" />,
  '720p': <Monitor className="w-5 h-5" />,
  'square': <Square className="w-6 h-6" />,
}

const PROFILE_LABELS: Record<string, string> = {
  '1080p': '横向 1080p',
  '1080p_vertical': '竖向 1080p (9:16)',
  '720p': '720p HD',
  'square': '方形 1:1',
}

export function RenderPanel({
  projectId,
  projectName,
  isCompleted,
  onRenderStart,
  isRendering,
  renderProgress = 0,
}: RenderPanelProps) {
  const [profiles, setProfiles] = useState<RenderProfile[]>([])
  const [selectedProfile, setSelectedProfile] = useState<string>('1080p')
  const [downloadUrls, setDownloadUrls] = useState<Record<string, string>>({})

  useEffect(() => {
    api.getRenderProfiles().then(({ profiles }) => {
      setProfiles(profiles)
    })
  }, [])

  const handleRender = () => {
    onRenderStart(selectedProfile)
  }

  const handleDownload = async (profile: string) => {
    try {
      const { download_url, filename } = await api.getDownloadUrl(projectId, profile)
      // In production, this would trigger actual download
      window.open(download_url, '_blank')
    } catch (error) {
      console.error('Download failed:', error)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Download className="w-5 h-5" />
          渲染输出
        </CardTitle>
        <CardDescription>
          选择画幅并渲染最终视频
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Profile Selection */}
        <div className="space-y-3">
          <label className="text-sm font-medium">选择画幅</label>
          <div className="grid grid-cols-2 gap-3">
            {profiles.map((profile) => (
              <button
                key={profile.name}
                onClick={() => setSelectedProfile(profile.name)}
                className={`p-4 rounded-lg border-2 transition-all text-left ${
                  selectedProfile === profile.name
                    ? 'border-primary bg-primary/10'
                    : 'border-border hover:border-primary/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`${
                    selectedProfile === profile.name ? 'text-primary' : 'text-muted-foreground'
                  }`}>
                    {PROFILE_ICONS[profile.name] || <RectangleHorizontal className="w-6 h-6" />}
                  </div>
                  <div>
                    <div className="font-medium text-sm">
                      {PROFILE_LABELS[profile.name] || profile.name}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {profile.width} × {profile.height}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Render Progress */}
        {isRendering && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">渲染进度</span>
              <span className="font-medium">{renderProgress}%</span>
            </div>
            <Progress value={renderProgress} className="h-2" />
            <p className="text-xs text-muted-foreground text-center">
              渲染完成后即可下载
            </p>
          </div>
        )}

        {/* Render Button */}
        <Button
          onClick={handleRender}
          disabled={!isCompleted || isRendering}
          className="w-full"
          size="lg"
        >
          {isRendering ? (
            <>
              <span className="animate-pulse mr-2">渲染中...</span>
            </>
          ) : (
            <>
              <Download className="w-4 h-4 mr-2" />
              开始渲染 {PROFILE_LABELS[selectedProfile] || selectedProfile}
            </>
          )}
        </Button>

        {/* Download Buttons */}
        {isCompleted && !isRendering && (
          <div className="space-y-2 pt-4 border-t">
            <label className="text-sm font-medium">已完成的画幅</label>
            <div className="grid grid-cols-2 gap-2">
              {profiles.map((profile) => (
                <Button
                  key={profile.name}
                  variant="outline"
                  onClick={() => handleDownload(profile.name)}
                  className="justify-start"
                >
                  <Download className="w-4 h-4 mr-2" />
                  {PROFILE_LABELS[profile.name] || profile.name}
                </Button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
