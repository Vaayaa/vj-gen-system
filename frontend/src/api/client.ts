// VJ-Gen API Client

const API_BASE = '/api/v1'

export interface ProjectSummary {
  id: string
  name: string
  status: string
  created_at: string
  updated_at: string
}

export interface Project {
  id: string
  name: string
  description?: string
  status: ProjectStatus
  audio_path?: string
  lyric_path?: string
  audio_analysis?: AudioAnalysisResult
  lyric_analysis?: LyricAnalysis
  shot_script?: ShotScript
  created_at: string
  updated_at: string
}

export type ProjectStatus = 
  | 'created' | 'uploading' | 'uploaded' | 'analyzing'
  | 'script_generated' | 'generating' | 'rendering' 
  | 'completed' | 'failed'

export interface AudioAnalysisResult {
  bpm: number
  time_signature: string
  duration: number
}

export interface LyricAnalysis {
  lines: LyricLine[]
  language: string
}

export interface LyricLine {
  start_time: number
  end_time: number
  text: string
  sentiment: string
}

export interface ShotScript {
  items: ShotScriptItem[]
  total_duration: number
}

export interface ShotScriptItem {
  id: string
  time_start: number
  time_end: number
  section_type: string
  lyric: string
  visual_prompt: string
}

export interface RenderProfile {
  name: string
  width: number
  height: number
  aspect_ratio: string
  fps: number
  description: string
}

export interface APIResponse<T = unknown> {
  success: boolean
  message: string
  data?: T
}

class APIClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }

    const data: APIResponse<T> = await response.json()
    
    if (!data.success) {
      throw new Error(data.message)
    }

    return data.data as T
  }

  // Project endpoints
  async listProjects(): Promise<{ projects: ProjectSummary[] }> {
    return this.request('/projects')
  }

  async getProject(id: string): Promise<Project> {
    return this.request(`/projects/${id}`)
  }

  async createProject(name: string, description?: string): Promise<{ id: string }> {
    return this.request('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    })
  }

  async deleteProject(id: string): Promise<void> {
    await this.request(`/projects/${id}`, { method: 'DELETE' })
  }

  // Upload endpoints
  async uploadFiles(
    projectId: string,
    audioFile: File,
    lyricsFile?: File
  ): Promise<{ audio_path: string; lyrics_path?: string }> {
    const formData = new FormData()
    formData.append('audio', audioFile)
    
    if (lyricsFile) {
      formData.append('lyrics', lyricsFile)
    }

    const response = await fetch(
      `${API_BASE}/projects/${projectId}/upload`,
      {
        method: 'POST',
        body: formData,
      }
    )

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`)
    }

    const data: APIResponse<{ audio_path: string; lyrics_path?: string }> = 
      await response.json()
    
    if (!data.success) {
      throw new Error(data.message)
    }

    return data.data!
  }

  // Analysis endpoints
  async analyzeProject(projectId: string): Promise<void> {
    await this.request(`/projects/${projectId}/analyze`, { method: 'POST' })
  }

  async getStatus(projectId: string): Promise<{ status: ProjectStatus }> {
    return this.request(`/projects/${projectId}/status`)
  }

  // Generation endpoints
  async generateVJ(projectId: string): Promise<void> {
    await this.request(`/projects/${projectId}/generate`, { method: 'POST' })
  }

  // Render endpoints
  async renderProject(projectId: string, profile: string): Promise<void> {
    await this.request(`/projects/${projectId}/render?profile=${profile}`, {
      method: 'POST',
    })
  }

  async getDownloadUrl(
    projectId: string,
    profile: string
  ): Promise<{ download_url: string; filename: string }> {
    return this.request(`/projects/${projectId}/download/${profile}`)
  }

  // Profiles
  async getRenderProfiles(): Promise<{ profiles: RenderProfile[] }> {
    return this.request('/profiles')
  }
}

export const api = new APIClient()
