import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Plus, Trash2, Clock, Music, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'
import { useProjectStore } from '@/stores/projectStore'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { ProjectSummary } from '@/api/client'

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  created: { icon: <Clock className="w-4 h-4" />, color: 'text-gray-400', label: '新建' },
  uploading: { icon: <Loader2 className="w-4 h-4 animate-spin" />, color: 'text-blue-400', label: '上传中' },
  uploaded: { icon: <CheckCircle className="w-4 h-4" />, color: 'text-green-400', label: '已上传' },
  analyzing: { icon: <Music className="w-4 h-4 animate-pulse" />, color: 'text-purple-400', label: '分析中' },
  script_generated: { icon: <FileText className="w-4 h-4" />, color: 'text-cyan-400', label: '脚本已生成' },
  generating: { icon: <Loader2 className="w-4 h-4 animate-spin" />, color: 'text-orange-400', label: '生成中' },
  rendering: { icon: <Loader2 className="w-4 h-4 animate-spin" />, color: 'text-yellow-400', label: '渲染中' },
  completed: { icon: <CheckCircle className="w-4 h-4" />, color: 'text-green-500', label: '已完成' },
  failed: { icon: <AlertCircle className="w-4 h-4" />, color: 'text-red-400', label: '失败' },
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { projects, isLoadingProjects, fetchProjects, createProject, deleteProject } = useProjectStore()
  const [isCreating, setIsCreating] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newProjectName.trim()) return

    setIsCreating(true)
    try {
      const id = await createProject(newProjectName)
      navigate(`/project/${id}`)
    } catch (error) {
      console.error('Failed to create project:', error)
    }
    setIsCreating(false)
  }

  const handleDeleteProject = async (e: React.MouseEvent, projectId: string) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (!confirm('确定要删除这个项目吗？')) return
    
    try {
      await deleteProject(projectId)
    } catch (error) {
      console.error('Failed to delete project:', error)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold">我的项目</h2>
          <p className="text-muted-foreground mt-1">
            管理你的 VJ 生成项目
          </p>
        </div>
        
        {/* Create New Project */}
        <form onSubmit={handleCreateProject} className="flex gap-2">
          <input
            type="text"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            placeholder="新项目名称..."
            className="px-4 py-2 rounded-lg border bg-background w-64"
          />
          <Button type="submit" disabled={isCreating || !newProjectName.trim()}>
            <Plus className="w-4 h-4 mr-2" />
            {isCreating ? '创建中...' : '新建项目'}
          </Button>
        </form>
      </div>

      {/* Loading State */}
      {isLoadingProjects && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      )}

      {/* Empty State */}
      {!isLoadingProjects && projects.length === 0 && (
        <Card className="py-12">
          <CardContent className="flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Music className="w-8 h-8 text-primary" />
            </div>
            <h3 className="text-xl font-semibold mb-2">暂无项目</h3>
            <p className="text-muted-foreground mb-4">
              创建一个新项目开始你的 VJ 创作之旅
            </p>
            <Button onClick={() => {
              setNewProjectName('我的 VJ 项目')
              document.querySelector<HTMLInputElement>('input[type="text"]')?.focus()
            }}>
              <Plus className="w-4 h-4 mr-2" />
              创建第一个项目
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Projects Grid */}
      {!isLoadingProjects && projects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => {
            const statusConfig = STATUS_CONFIG[project.status] || STATUS_CONFIG.created
            
            return (
              <Link key={project.id} to={`/project/${project.id}`}>
                <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-lg">{project.name}</CardTitle>
                      <button
                        onClick={(e) => handleDeleteProject(e, project.id)}
                        className="p-1 hover:bg-destructive/20 rounded text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <CardDescription>
                      {formatDate(project.created_at)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm ${statusConfig.color}`}
                         style={{ backgroundColor: 'currentColor', opacity: 0.1 }}>
                      {statusConfig.icon}
                      <span>{statusConfig.label}</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
