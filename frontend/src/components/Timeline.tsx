import React from 'react'
import { ShotScriptItem } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'

interface TimelineProps {
  shots: ShotScriptItem[]
  duration: number
  currentTime?: number
  onShotSelect?: (shot: ShotScriptItem) => void
}

const SECTION_COLORS: Record<string, string> = {
  intro: 'bg-purple-500',
  verse: 'bg-blue-500',
  pre_chorus: 'bg-cyan-500',
  chorus: 'bg-green-500',
  drop: 'bg-red-500',
  bridge: 'bg-yellow-500',
  outro: 'bg-gray-500',
  break: 'bg-orange-500',
  silence: 'bg-gray-700',
}

const SECTION_LABELS: Record<string, string> = {
  intro: '前奏',
  verse: '主歌',
  pre_chorus: '副歌前',
  chorus: '副歌',
  drop: 'Drop',
  bridge: '桥段',
  outro: '尾奏',
  break: 'Break',
  silence: '停顿',
}

export function Timeline({ shots, duration, currentTime = 0, onShotSelect }: TimelineProps) {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Time markers
  const markers = []
  for (let t = 0; t <= duration; t += 10) {
    markers.push(t)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>时间线</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Timeline ruler */}
        <div className="relative">
          <div className="h-6 bg-secondary rounded-t-lg border-b flex items-end">
            {markers.map((time) => (
              <div
                key={time}
                className="absolute bottom-0 text-xs text-muted-foreground"
                style={{ left: `${(time / duration) * 100}%` }}
              >
                {formatTime(time)}
              </div>
            ))}
          </div>
        </div>

        {/* Shot track */}
        <div className="relative h-16 bg-secondary rounded-lg overflow-hidden">
          {shots.length === 0 ? (
            <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
              暂无镜头数据
            </div>
          ) : (
            shots.map((shot, index) => {
              const left = (shot.time_start / duration) * 100
              const width = ((shot.time_end - shot.time_start) / duration) * 100
              const isActive = currentTime >= shot.time_start && currentTime < shot.time_end
              
              return (
                <div
                  key={shot.id}
                  className={`absolute top-1 bottom-1 rounded cursor-pointer transition-all ${
                    SECTION_COLORS[shot.section_type] || 'bg-primary'
                  } ${isActive ? 'ring-2 ring-white ring-offset-2 ring-offset-background' : 'opacity-70 hover:opacity-100'}`}
                  style={{ left: `${left}%`, width: `${width}%` }}
                  onClick={() => onShotSelect?.(shot)}
                  title={`${SECTION_LABELS[shot.section_type] || shot.section_type}: ${shot.lyric || '无歌词'}`}
                >
                  <div className="h-full flex items-center justify-center overflow-hidden px-1">
                    <span className="text-xs font-medium text-white truncate">
                      {shot.lyric?.slice(0, 20) || SECTION_LABELS[shot.section_type] || shot.section_type}
                    </span>
                  </div>
                </div>
              )
            })
          )}
          
          {/* Playhead */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10"
            style={{ left: `${(currentTime / duration) * 100}%` }}
          >
            <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-red-500 rounded-full" />
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-2">
          {Object.entries(SECTION_COLORS).map(([key, color]) => (
            <div key={key} className="flex items-center gap-1 text-xs">
              <div className={`w-3 h-3 rounded ${color}`} />
              <span className="text-muted-foreground">{SECTION_LABELS[key] || key}</span>
            </div>
          ))}
        </div>

        {/* Selected shot details */}
        {shots.length > 0 && (
          <div className="border-t pt-4 mt-4">
            <h4 className="text-sm font-medium mb-2">镜头详情</h4>
            <div className="space-y-2 text-sm">
              {shots.slice(0, 5).map((shot) => (
                <div
                  key={shot.id}
                  className="p-2 rounded bg-secondary hover:bg-secondary/80 cursor-pointer"
                  onClick={() => onShotSelect?.(shot)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      {SECTION_LABELS[shot.section_type] || shot.section_type}
                    </span>
                    <span className="text-muted-foreground">
                      {formatTime(shot.time_start)} - {formatTime(shot.time_end)}
                    </span>
                  </div>
                  {shot.lyric && (
                    <p className="text-muted-foreground mt-1 truncate">{shot.lyric}</p>
                  )}
                </div>
              ))}
              {shots.length > 5 && (
                <p className="text-sm text-muted-foreground text-center">
                  还有 {shots.length - 5} 个镜头...
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
