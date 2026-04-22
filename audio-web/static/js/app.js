// Madmom Audio Analysis - Enhanced Visualization
// VJ智能剪辑系统 - 增强版可视化

let wavesurfer = null;
let currentResult = null;
let audioBuffer = null;
let regions = [];

// DOM Elements
const uploadSection = document.getElementById('uploadSection');
const loadingSection = document.getElementById('loadingSection');
const resultSection = document.getElementById('resultSection');
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initDropZone();
    initControls();
    initWaveSurferRegions();
});

function initDropZone() {
    // Desktop click
    dropZone.addEventListener('click', () => fileInput.click());
    
    // Mobile file select button
    const selectBtn = document.getElementById('selectFileBtn');
    if (selectBtn) {
        selectBtn.addEventListener('click', () => fileInput.click());
    }
    
    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });
}

function initControls() {
    document.getElementById('analyzeAnother').addEventListener('click', resetUI);
    document.getElementById('copySegments').addEventListener('click', copySegments);
    
    // Toggle handlers
    document.getElementById('showDownbeats').addEventListener('change', () => updateAllMarkers());
    document.getElementById('showBeats').addEventListener('change', () => updateAllMarkers());
    document.getElementById('showEnergy').addEventListener('change', () => updateAllMarkers());
    document.getElementById('showPitch').addEventListener('change', () => updateAllMarkers());
}

function initWaveSurferRegions() {
    // Custom region plugin for better visualization
}

async function handleFile(file) {
    if (!file.type.startsWith('audio/') && !isValidAudioExt(file.name)) {
        alert('请上传音频文件');
        return;
    }
    
    showLoading();
    updateLoadingHint('上传音频中...');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        updateLoadingHint('正在分析节拍...');
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok || data.error) {
            throw new Error(data.error || '分析失败');
        }
        
        currentResult = data;
        await showResult(file, data);
        
    } catch (error) {
        alert('错误: ' + error.message);
        showUpload();
    }
}

function isValidAudioExt(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    return ['mp3', 'wav', 'm4a', 'flac', 'ogg', 'aac'].includes(ext);
}

async function showResult(file, data) {
    uploadSection.style.display = 'none';
    loadingSection.style.display = 'none';
    resultSection.style.display = 'block';
    
    // Update file info
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('duration').textContent = formatTime(data.duration);
    
    // Update stats with enhanced info
    document.getElementById('bpmValue').textContent = data.tempo?.toFixed(1) || '--';
    document.getElementById('downbeatsCount').textContent = data.downbeats?.length || 0;
    document.getElementById('beatsCount').textContent = data.beats?.length || 0;
    document.getElementById('segmentsCount').textContent = data.segments?.length || 0;
    
    // Calculate beat interval
    if (data.downbeats && data.downbeats.length > 1) {
        const interval = (data.downbeats[data.downbeats.length - 1] - data.downbeats[0]) / (data.downbeats.length - 1);
        document.getElementById('beatInterval').textContent = interval.toFixed(3) + 's';
    }
    
    // Initialize enhanced waveform
    await initWaveform(file, data);
    
    // Render enhanced timeline
    renderBeatTimeline(data);
    
    // Render segments
    renderSegments(data);
}

async function initWaveform(file, data) {
    // Destroy previous instance
    if (wavesurfer) {
        wavesurfer.destroy();
        wavesurfer = null;
    }
    
    // Load audio first to get duration
    audioBuffer = await file.arrayBuffer();
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const audioBufferDecoded = await audioContext.decodeAudioData(audioBuffer.slice(0));
    const duration = audioBufferDecoded.duration;
    
    // Create wavesurfer with enhanced config
    wavesurfer = WaveSurfer.create({
        container: '#waveform',
        waveColor: '#4a5568',
        progressColor: '#7c3aed',
        cursorColor: '#f472b6',
        cursorWidth: 3,
        height: 160,
        barWidth: 3,
        barGap: 2,
        barRadius: 3,
        normalize: true,
        interact: true,
        hideScrollbar: true,
        audioContext: audioContext,
    });
    
    // Load audio
    await wavesurfer.loadBlob(file);
    
    // After load, add all markers
    wavesurfer.on('ready', () => {
        updateAllMarkers();
    });
    
    // Click to seek and play
    wavesurfer.on('click', (relativeX) => {
        wavesurfer.seekTo(relativeX);
    });
    
    // Double click for precise positioning
    wavesurfer.on('dblclick', (relativeX) => {
        const time = relativeX * duration;
        wavesurfer.seekTo(relativeX);
        showTimeTooltip(relativeX, time);
    });
}

function updateAllMarkers() {
    if (!wavesurfer || !currentResult) return;
    
    // Clear existing regions
    wavesurfer.clearRegions();
    regions = [];
    
    const duration = currentResult.duration;
    const showDownbeats = document.getElementById('showDownbeats').checked;
    const showBeats = document.getElementById('showBeats').checked;
    const showEnergy = document.getElementById('showEnergy')?.checked || false;
    const showPitch = document.getElementById('showPitch')?.checked || false;
    
    // Color palette for different markers
    const colors = {
        downbeat: 'rgba(168, 85, 247, 0.7)',   // Purple - 小节起点
        beat: 'rgba(56, 189, 248, 0.5)',       // Cyan - 普通节拍
        energy: 'rgba(251, 146, 60, 0.6)',     // Orange - 能量突变
        pitch: 'rgba(74, 222, 128, 0.5)',      // Green - 音调变化
    };
    
    // Add downbeat markers (larger, more prominent)
    if (showDownbeats && currentResult.downbeats) {
        currentResult.downbeats.forEach((time, i) => {
            const region = wavesurfer.addRegion({
                start: time,
                end: Math.min(time + 0.08, duration),
                color: colors.downbeat,
                drag: false,
                resize: false,
                handleStyle: {
                    left: { backgroundColor: '#9333ea', width: '4px' },
                    right: { backgroundColor: '#9333ea', width: '4px' }
                }
            });
            region.time = time;
            region.type = 'downbeat';
            regions.push(region);
        });
    }
    
    // Add beat markers (smaller)
    if (showBeats && currentResult.beats) {
        // Only show a subset if too many
        const beats = currentResult.beats.length > 500 
            ? currentResult.beats.filter((_, i) => i % 5 === 0)
            : currentResult.beats;
        
        beats.forEach((time, i) => {
            const region = wavesurfer.addRegion({
                start: time,
                end: Math.min(time + 0.04, duration),
                color: colors.beat,
                drag: false,
                resize: false,
            });
            region.time = time;
            region.type = 'beat';
            regions.push(region);
        });
    }
    
    // Add energy markers if available
    if (showEnergy && currentResult.energy_points) {
        currentResult.energy_points.forEach((point) => {
            const time = typeof point === 'object' ? point.time : point;
            wavesurfer.addRegion({
                start: time,
                end: Math.min(time + 0.05, duration),
                color: colors.energy,
                drag: false,
                resize: false,
            });
        });
    }
    
    // Add pitch markers if available
    if (showPitch && currentResult.pitch_changes) {
        currentResult.pitch_changes.forEach((point) => {
            const time = typeof point === 'object' ? point.time : point;
            wavesurfer.addRegion({
                start: time,
                end: Math.min(time + 0.05, duration),
                color: colors.pitch,
                drag: false,
                resize: false,
            });
        });
    }
    
    // Add time ruler
    updateTimeRuler(duration);
}

function showTimeTooltip(relativeX, time) {
    // Remove existing tooltip
    const existing = document.querySelector('.time-tooltip');
    if (existing) existing.remove();
    
    const tooltip = document.createElement('div');
    tooltip.className = 'time-tooltip';
    tooltip.textContent = formatTime(time) + ' (' + time.toFixed(3) + 's)';
    tooltip.style.left = (relativeX * 100) + '%';
    document.getElementById('waveform').appendChild(tooltip);
    
    setTimeout(() => tooltip.remove(), 2000);
}

function updateTimeRuler(duration) {
    const ruler = document.getElementById('timeRuler');
    ruler.innerHTML = '';
    
    // Dynamic interval based on duration
    let interval = 10;
    if (duration > 300) interval = 60;
    else if (duration > 120) interval = 30;
    else if (duration > 60) interval = 15;
    else if (duration > 30) interval = 5;
    
    for (let t = 0; t <= duration; t += interval) {
        const span = document.createElement('span');
        span.textContent = formatTime(t);
        span.style.position = 'absolute';
        span.style.left = `${(t / duration) * 100}%`;
        span.style.transform = 'translateX(-50%)';
        ruler.appendChild(span);
    }
}

function renderBeatTimeline(data) {
    const container = document.getElementById('beatTimeline');
    container.innerHTML = '';
    
    const downbeats = data.downbeats || [];
    const beats = data.beats || [];
    const duration = data.duration || 1;
    
    // Combined sorted list
    const allBeats = [
        ...downbeats.map(t => ({ time: t, type: 'downbeat' })),
        ...beats.map(t => ({ time: t, type: 'beat' }))
    ].sort((a, b) => a.time - b.time);
    
    const timelineHint = document.getElementById('timelineHint');
    timelineHint.textContent = `${downbeats.length} downbeats · ${beats.length} beats`;
    
    // Create visual timeline
    const timeline = document.createElement('div');
    timeline.className = 'timeline-visual';
    
    //缩略图模式 - 显示所有节拍的相对位置
    allBeats.forEach((beat, i) => {
        const marker = document.createElement('div');
        marker.className = `timeline-marker ${beat.type}`;
        marker.style.left = `${(beat.time / duration) * 100}%`;
        marker.title = `${beat.type}: ${beat.time.toFixed(3)}s`;
        
        // Click to seek
        marker.addEventListener('click', () => {
            if (wavesurfer) {
                wavesurfer.seekTo(beat.time / duration);
            }
        });
        
        timeline.appendChild(marker);
    });
    
    container.appendChild(timeline);
    
    // Legend
    const legend = document.createElement('div');
    legend.className = 'timeline-legend';
    legend.innerHTML = `
        <span class="legend-item"><span class="legend-dot downbeat"></span>Downbeat</span>
        <span class="legend-item"><span class="legend-dot beat"></span>Beat</span>
    `;
    container.appendChild(legend);
}

function renderSegments(data) {
    const container = document.getElementById('segmentsList');
    container.innerHTML = '';
    
    const segments = data.segments || [];
    
    if (segments.length === 0) {
        container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">无小节数据</p>';
        return;
    }
    
    segments.forEach((seg, i) => {
        const div = document.createElement('div');
        div.className = 'segment-item';
        div.innerHTML = `
            <span class="segment-num">${i + 1}</span>
            <span class="segment-time">${seg.start.toFixed(3)}s → ${seg.end.toFixed(3)}s</span>
            <span class="segment-duration">${seg.duration?.toFixed(2)s || ''}</span>
        `;
        div.addEventListener('click', () => {
            if (wavesurfer) {
                wavesurfer.seekTo(seg.start / data.duration);
            }
        });
        container.appendChild(div);
    });
}

function copySegments() {
    if (!currentResult || !currentResult.segments) return;
    
    const text = currentResult.segments
        .map((s, i) => `${i + 1}. ${s.start.toFixed(3)}s`)
        .join('\n');
    
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('copySegments');
        btn.textContent = '已复制!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = '复制时间点';
            btn.classList.remove('copied');
        }, 2000);
    });
}

function showLoading() {
    uploadSection.style.display = 'none';
    loadingSection.style.display = 'block';
    resultSection.style.display = 'none';
}

function updateLoadingHint(text) {
    document.getElementById('loadingHint').textContent = text;
}

function showUpload() {
    uploadSection.style.display = 'block';
    loadingSection.style.display = 'none';
    resultSection.style.display = 'none';
}

function resetUI() {
    currentResult = null;
    if (wavesurfer) {
        wavesurfer.destroy();
        wavesurfer = null;
    }
    fileInput.value = '';
    showUpload();
}

function formatTime(seconds) {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}
