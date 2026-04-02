import { create } from 'zustand'
import { api, Project, ProjectStatus, ProjectSummary } from '@/api/client'

interface ProgressUpdate {
  type: string
  step: string
  message: string
  progress: number
  timestamp: string
}

interface ProjectState {
  // Projects list
  projects: ProjectSummary[]
  isLoadingProjects: boolean
  
  // Current project
  currentProject: Project | null
  isLoadingProject: boolean
  
  // Progress tracking
  progress: Record<string, ProgressUpdate>
  wsConnected: boolean
  
  // Actions
  fetchProjects: () => Promise<void>
  fetchProject: (id: string) => Promise<void>
  createProject: (name: string, description?: string) => Promise<string>
  deleteProject: (id: string) => Promise<void>
  
  // File operations
  uploadFiles: (projectId: string, audio: File, lyrics?: File) => Promise<void>
  
  // Pipeline operations
  analyzeProject: (projectId: string) => Promise<void>
  generateVJ: (projectId: string) => Promise<void>
  renderProject: (projectId: string, profile: string) => Promise<void>
  
  // WebSocket
  connectWebSocket: (projectId: string) => () => void
  updateProgress: (projectId: string, update: ProgressUpdate) => void
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  isLoadingProjects: false,
  currentProject: null,
  isLoadingProject: false,
  progress: {},
  wsConnected: false,

  fetchProjects: async () => {
    set({ isLoadingProjects: true })
    try {
      const { projects } = await api.listProjects()
      set({ projects, isLoadingProjects: false })
    } catch (error) {
      console.error('Failed to fetch projects:', error)
      set({ isLoadingProjects: false })
    }
  },

  fetchProject: async (id: string) => {
    set({ isLoadingProject: true })
    try {
      const project = await api.getProject(id)
      set({ currentProject: project, isLoadingProject: false })
    } catch (error) {
      console.error('Failed to fetch project:', error)
      set({ isLoadingProject: false })
    }
  },

  createProject: async (name: string, description?: string) => {
    const { id } = await api.createProject(name, description)
    await get().fetchProjects()
    return id
  },

  deleteProject: async (id: string) => {
    await api.deleteProject(id)
    await get().fetchProjects()
  },

  uploadFiles: async (projectId: string, audio: File, lyrics?: File) => {
    await api.uploadFiles(projectId, audio, lyrics)
    await get().fetchProject(projectId)
  },

  analyzeProject: async (projectId: string) => {
    await api.analyzeProject(projectId)
  },

  generateVJ: async (projectId: string) => {
    await api.generateVJ(projectId)
  },

  renderProject: async (projectId: string, profile: string) => {
    await api.renderProject(projectId, profile)
  },

  connectWebSocket: (projectId: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/${projectId}`
    
    const ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      set({ wsConnected: true })
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        get().updateProgress(projectId, data)
        
        // Refresh project status on major updates
        if (data.type === 'status_update' || data.type === 'generation_progress') {
          get().fetchProject(projectId)
        }
      } catch (error) {
        console.error('WebSocket message parse error:', error)
      }
    }
    
    ws.onclose = () => {
      set({ wsConnected: false })
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    // Return cleanup function
    return () => {
      ws.close()
    }
  },

  updateProgress: (projectId: string, update: ProgressUpdate) => {
    set((state) => ({
      progress: {
        ...state.progress,
        [projectId]: update,
      },
    }))
  },
}))
