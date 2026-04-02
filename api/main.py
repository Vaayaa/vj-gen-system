"""
VJ-Gen System API
FastAPI backend for VJ project management
"""

import asyncio
import os
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn

# Import project schemas
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.models.schemas import (
    Project, ProjectStatus, ProjectCreateRequest, APIResponse,
    AudioAnalysisResult, LyricAnalysis, ShotScript,
    RenderProfile, AspectRatio, OutputFormat
)

# ============================================================================
# App Configuration
# ============================================================================

app = FastAPI(
    title="VJ-Gen API",
    description="VJ Generation System - Audio + Lyrics to VJ Video",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage paths
STORAGE_ROOT = Path(__file__).parent.parent / "storage"
AUDIO_DIR = STORAGE_ROOT / "audio"
LYRICS_DIR = STORAGE_ROOT / "lyrics"
OUTPUT_DIR = STORAGE_ROOT / "output"
TEMP_DIR = STORAGE_ROOT / "temp"

for d in [AUDIO_DIR, LYRICS_DIR, OUTPUT_DIR, TEMP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# In-memory project storage (replace with DB in production)
projects: dict[str, Project] = {}

# WebSocket connections for real-time progress
ws_connections: dict[str, list[WebSocket]] = {}

# ============================================================================
# WebSocket Manager
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections for project progress"""
    
    async def connect(self, project_id: str, websocket: WebSocket):
        await websocket.accept()
        if project_id not in ws_connections:
            ws_connections[project_id] = []
        ws_connections[project_id].append(websocket)
    
    def disconnect(self, project_id: str, websocket: WebSocket):
        if project_id in ws_connections:
            ws_connections[project_id].remove(websocket)
            if not ws_connections[project_id]:
                del ws_connections[project_id]
    
    async def broadcast(self, project_id: str, message: dict):
        if project_id in ws_connections:
            for connection in ws_connections[project_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# ============================================================================
# Helper Functions
# ============================================================================

def get_project_dir(project_id: str) -> Path:
    """Get project-specific directory"""
    project_dir = STORAGE_ROOT / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir

def update_project_status(project_id: str, status: ProjectStatus, **kwargs):
    """Update project status and broadcast to WebSocket"""
    if project_id not in projects:
        raise ValueError(f"Project {project_id} not found")
    
    project = projects[project_id]
    project.status = status
    project.updated_at = datetime.now()
    
    for key, value in kwargs.items():
        if hasattr(project, key):
            setattr(project, key, value)
    
    # Broadcast status update
    asyncio.create_task(manager.broadcast(project_id, {
        "type": "status_update",
        "project_id": project_id,
        "status": status.value,
        "timestamp": datetime.now().isoformat()
    }))

async def simulate_analysis_steps(project_id: str):
    """Simulate the analysis pipeline steps with progress updates"""
    steps = [
        ("audio_analysis", "正在分析音频...", 20),
        ("beat_detection", "检测节拍...", 40),
        ("lyric_parsing", "解析歌词...", 60),
        ("shot_script_generation", "生成镜头脚本...", 80),
        ("completed", "分析完成", 100),
    ]
    
    for step_key, message, progress in steps:
        await manager.broadcast(project_id, {
            "type": "progress",
            "project_id": project_id,
            "step": step_key,
            "message": message,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        })
        await asyncio.sleep(0.5)  # Simulate work

async def simulate_generation_steps(project_id: str):
    """Simulate the VJ generation pipeline steps"""
    steps = [
        ("keyframe_generation", "生成关键帧...", 15),
        ("video_synthesis", "合成视频片段...", 45),
        ("timeline_compilation", "编排时间线...", 70),
        ("render_preparation", "准备渲染...", 85),
        ("completed", "生成完成", 100),
    ]
    
    for step_key, message, progress in steps:
        await manager.broadcast(project_id, {
            "type": "generation_progress",
            "project_id": project_id,
            "step": step_key,
            "message": message,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        })
        await asyncio.sleep(0.5)

async def simulate_render_steps(project_id: str, profile: str):
    """Simulate the rendering steps"""
    steps = [
        ("initializing", "初始化渲染器...", 10),
        ("encoding_video", "编码视频...", 50),
        ("encoding_audio", "编码音频...", 70),
        ("finalizing", "完成最终处理...", 90),
        ("completed", "渲染完成", 100),
    ]
    
    for step_key, message, progress in steps:
        await manager.broadcast(project_id, {
            "type": "render_progress",
            "project_id": project_id,
            "profile": profile,
            "step": step_key,
            "message": message,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        })
        await asyncio.sleep(0.3)

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {"message": "VJ-Gen API v1.0.0", "docs": "/docs"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# --------------------------------------------------------------------------
# Project Management
# --------------------------------------------------------------------------

@app.post("/api/v1/projects", response_model=APIResponse)
async def create_project(request: ProjectCreateRequest):
    """Create a new VJ project"""
    project_id = str(uuid.uuid4())
    
    project = Project(
        id=project_id,
        name=request.name,
        description=request.description,
        status=ProjectStatus.CREATED
    )
    
    projects[project_id] = project
    
    # Create project directory
    get_project_dir(project_id)
    
    return APIResponse(
        success=True,
        message="Project created successfully",
        data={
            "id": project_id,
            "name": request.name,
            "status": project.status.value
        }
    )

@app.get("/api/v1/projects", response_model=APIResponse)
async def list_projects():
    """List all projects"""
    project_list = [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status.value,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat()
        }
        for p in projects.values()
    ]
    
    return APIResponse(
        success=True,
        message=f"Found {len(projects)} projects",
        data={"projects": project_list}
    )

@app.get("/api/v1/projects/{project_id}", response_model=APIResponse)
async def get_project(project_id: str):
    """Get project details"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    
    return APIResponse(
        success=True,
        message="Project retrieved successfully",
        data=project.model_dump(mode="json")
    )

@app.delete("/api/v1/projects/{project_id}", response_model=APIResponse)
async def delete_project(project_id: str):
    """Delete a project"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    del projects[project_id]
    
    # Clean up project directory
    project_dir = get_project_dir(project_id)
    import shutil
    shutil.rmtree(project_dir, ignore_errors=True)
    
    return APIResponse(
        success=True,
        message="Project deleted successfully"
    )

# --------------------------------------------------------------------------
# File Upload
# --------------------------------------------------------------------------

@app.post("/api/v1/projects/{project_id}/upload", response_model=APIResponse)
async def upload_files(
    project_id: str,
    audio: UploadFile = File(...),
    lyrics: Optional[UploadFile] = File(None)
):
    """Upload audio and/or lyrics files"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    project_dir = get_project_dir(project_id)
    
    # Update status
    update_project_status(project_id, ProjectStatus.UPLOADING)
    
    # Save audio file
    audio_path = project_dir / "audio" / audio.filename
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(audio_path, "wb") as f:
        content = await audio.read()
        f.write(content)
    
    project.audio_path = str(audio_path)
    
    # Save lyrics file if provided
    if lyrics:
        lyrics_path = project_dir / "lyrics" / lyrics.filename
        lyrics_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(lyrics_path, "wb") as f:
            content = await lyrics.read()
            f.write(content)
        
        project.lyric_path = str(lyrics_path)
    
    update_project_status(project_id, ProjectStatus.UPLOADED)
    
    return APIResponse(
        success=True,
        message="Files uploaded successfully",
        data={
            "audio_path": str(audio_path),
            "lyrics_path": str(project.lyric_path) if project.lyric_path else None
        }
    )

# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

@app.post("/api/v1/projects/{project_id}/analyze", response_model=APIResponse)
async def analyze_project(project_id: str):
    """Trigger the analysis pipeline"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    
    if not project.audio_path:
        raise HTTPException(status_code=400, detail="No audio file uploaded")
    
    update_project_status(project_id, ProjectStatus.ANALYZING)
    
    # Start analysis in background
    asyncio.create_task(run_analysis(project_id))
    
    return APIResponse(
        success=True,
        message="Analysis started"
    )

async def run_analysis(project_id: str):
    """Run the analysis pipeline (background task)"""
    try:
        # Simulate analysis steps
        await simulate_analysis_steps(project_id)
        
        # In production, this would call actual pipeline:
        # audio_result = await audio_pipeline.analyze(projects[project_id].audio_path)
        # lyric_result = await lyric_pipeline.analyze(projects[project_id].lyric_path)
        
        # Generate mock analysis results
        audio_analysis = AudioAnalysisResult(
            bpm=128.0,
            time_signature="4/4",
            duration=180.0,
            sections=[],
            energy_curve=[],
            beats=[],
            analysis_version="1.0.0"
        )
        
        lyric_analysis = LyricAnalysis(
            lines=[],
            language="unknown",
            analysis_version="1.0.0"
        )
        
        shot_script = ShotScript(
            items=[],
            total_duration=180.0,
            resolution=(1920, 1080),
            fps=30
        )
        
        update_project_status(
            project_id,
            ProjectStatus.SCRIPT_GENERATED,
            audio_analysis=audio_analysis,
            lyric_analysis=lyric_analysis,
            shot_script=shot_script
        )
        
    except Exception as e:
        await manager.broadcast(project_id, {
            "type": "error",
            "project_id": project_id,
            "message": str(e)
        })
        update_project_status(project_id, ProjectStatus.FAILED)

# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

@app.post("/api/v1/projects/{project_id}/generate", response_model=APIResponse)
async def generate_vj(project_id: str):
    """Trigger VJ generation"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    
    if project.status != ProjectStatus.SCRIPT_GENERATED:
        raise HTTPException(
            status_code=400,
            detail="Project must have completed analysis before generation"
        )
    
    update_project_status(project_id, ProjectStatus.GENERATING)
    
    # Start generation in background
    asyncio.create_task(run_generation(project_id))
    
    return APIResponse(
        success=True,
        message="Generation started"
    )

async def run_generation(project_id: str):
    """Run VJ generation pipeline (background task)"""
    try:
        await simulate_generation_steps(project_id)
        
        # In production, this would call actual pipelines
        # for shot in project.shot_script.items:
        #     keyframe = await keyframe_pipeline.generate(shot)
        #     video = await video_pipeline.generate(keyframe, shot)
        
        update_project_status(project_id, ProjectStatus.GENERATING)
        
    except Exception as e:
        await manager.broadcast(project_id, {
            "type": "error",
            "project_id": project_id,
            "message": str(e)
        })
        update_project_status(project_id, ProjectStatus.FAILED)

# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

@app.post("/api/v1/projects/{project_id}/render", response_model=APIResponse)
async def render_project(project_id: str, profile: str = "1080p"):
    """Trigger rendering for specified profile"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    
    if project.status not in [ProjectStatus.SCRIPT_GENERATED, ProjectStatus.GENERATING]:
        raise HTTPException(status_code=400, detail="Project must have script before rendering")
    
    update_project_status(project_id, ProjectStatus.RENDERING)
    
    # Start rendering in background
    asyncio.create_task(run_render(project_id, profile))
    
    return APIResponse(
        success=True,
        message=f"Rendering started for profile: {profile}"
    )

async def run_render(project_id: str, profile: str):
    """Run rendering pipeline (background task)"""
    try:
        await simulate_render_steps(project_id, profile)
        
        # In production, this would call ffmpeg rendering
        # output_path = await renderer.render(project, profile)
        
        # Create a placeholder output file
        project_dir = get_project_dir(project_id)
        output_dir = project_dir / "renders" / profile
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"vj_output_{profile}.mp4"
        output_path.write_text("placeholder")
        
        update_project_status(project_id, ProjectStatus.COMPLETED)
        
    except Exception as e:
        await manager.broadcast(project_id, {
            "type": "error",
            "project_id": project_id,
            "message": str(e)
        })
        update_project_status(project_id, ProjectStatus.FAILED)

# --------------------------------------------------------------------------
# Status & Download
# --------------------------------------------------------------------------

@app.get("/api/v1/projects/{project_id}/status", response_model=APIResponse)
async def get_status(project_id: str):
    """Get current project status"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    
    return APIResponse(
        success=True,
        message="Status retrieved",
        data={
            "id": project.id,
            "name": project.name,
            "status": project.status.value,
            "updated_at": project.updated_at.isoformat()
        }
    )

@app.get("/api/v1/projects/{project_id}/download/{profile}", response_model=APIResponse)
async def download_project(project_id: str, profile: str):
    """Get download URL for rendered video"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    project_dir = get_project_dir(project_id)
    output_path = project_dir / "renders" / profile / f"vj_output_{profile}.mp4"
    
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Rendered file not found")
    
    return APIResponse(
        success=True,
        message="Download ready",
        data={
            "download_url": f"/api/v1/files/{project_id}/renders/{profile}/vj_output_{profile}.mp4",
            "filename": f"{project.name}_{profile}.mp4"
        }
    )

@app.get("/api/v1/files/{project_id}/renders/{profile}/{filename}")
async def download_file(project_id: str, profile: str, filename: str):
    """Download rendered file"""
    file_path = STORAGE_ROOT / project_id / "renders" / profile / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="video/mp4"
    )

# --------------------------------------------------------------------------
# WebSocket
# --------------------------------------------------------------------------

@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await manager.connect(project_id, websocket)
    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            # Echo back for ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)

# --------------------------------------------------------------------------
# Render Profiles
# --------------------------------------------------------------------------

@app.get("/api/v1/profiles", response_model=APIResponse)
async def list_render_profiles():
    """List available render profiles"""
    profiles = [
        {
            "name": "1080p",
            "width": 1920,
            "height": 1080,
            "aspect_ratio": "16:9",
            "fps": 30,
            "description": "Full HD landscape"
        },
        {
            "name": "1080p_vertical",
            "width": 1080,
            "height": 1920,
            "aspect_ratio": "9:16",
            "fps": 30,
            "description": "Full HD vertical (TikTok/Reels)"
        },
        {
            "name": "720p",
            "width": 1280,
            "height": 720,
            "aspect_ratio": "16:9",
            "fps": 30,
            "description": "HD ready"
        },
        {
            "name": "square",
            "width": 1080,
            "height": 1080,
            "aspect_ratio": "1:1",
            "fps": 30,
            "description": "Square format"
        }
    ]
    
    return APIResponse(
        success=True,
        message="Render profiles",
        data={"profiles": profiles}
    )

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
