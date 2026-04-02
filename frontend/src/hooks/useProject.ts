import { useEffect, useCallback } from 'react'
import { useProjectStore } from '@/stores/projectStore'

export function useProject(projectId: string) {
  const {
    currentProject,
    isLoadingProject,
    progress,
    wsConnected,
    fetchProject,
    analyzeProject,
    generateVJ,
    renderProject,
    connectWebSocket,
    updateProgress,
  } = useProjectStore()

  useEffect(() => {
    fetchProject(projectId)
  }, [projectId, fetchProject])

  useEffect(() => {
    const cleanup = connectWebSocket(projectId)
    return cleanup
  }, [projectId, connectWebSocket])

  const startAnalysis = useCallback(async () => {
    await analyzeProject(projectId)
  }, [projectId, analyzeProject])

  const startGeneration = useCallback(async () => {
    await generateVJ(projectId)
  }, [projectId, generateVJ])

  const startRender = useCallback(async (profile: string) => {
    await renderProject(projectId, profile)
  }, [projectId, renderProject])

  const currentProgress = progress[projectId]

  return {
    project: currentProject,
    isLoading: isLoadingProject,
    progress: currentProgress,
    isWsConnected: wsConnected,
    startAnalysis,
    startGeneration,
    startRender,
    refresh: () => fetchProject(projectId),
  }
}
