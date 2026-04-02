/**
 * VJ编辑器音频分析集成
 * 
 * 功能:
 * 1. 音频上传 → 分析BPM/Key/段落
 * 2. 自动填充到VJ编辑器
 * 3. 素材生成匹配音乐结构
 */

// 音频分析类
class VJAudioAnalyzer {
    constructor(serverUrl = 'http://localhost:5001') {
        this.serverUrl = serverUrl;
    }
    
    async analyze(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${this.serverUrl}/analyze`, {
                method: 'POST',
                body: formData
            });
            return await response.json();
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    // 将分析结果转换为编辑器格式
    toEditorFormat(analysis) {
        return {
            bpm: analysis.bpm || 120,
            key: analysis.key || 'C',
            sections: analysis.sections || [],
            beats: analysis.beats || [],
            duration: analysis.duration || 0
        };
    }
}

// 素材生成提示词
const SECTION_PROMPTS = {
    intro: '神秘氛围，暗色调，渐亮效果，VJ舞台背景',
    verse: '情感叙事，故事性强，电影感',
    preChorus: '能量积累，渐强推进，张力',
    chorus: '高能量，视觉冲击，峰值时刻',
    bridge: '转折变化，对比鲜明',
    outro: '渐暗收尾，余韵感'
};

// 素材生成类
class VJMaterialGenerator {
    constructor() {
        this.prompts = SECTION_PROMPTS;
    }
    
    generatePrompt(section, bpm, key) {
        const base = this.prompts[section.type] || '现代风格，VJ背景';
        return `${base}, ${bpm}BPM, ${key}调`;
    }
    
    generateForSections(sections, bpm, key) {
        return sections.map(section => ({
            section: section.name || section.type,
            start: section.start,
            end: section.end,
            duration: section.end - section.start,
            prompt: this.generatePrompt(section, bpm, key)
        }));
    }
}

// 主类
class VJEditorIntegration {
    constructor(editorElement) {
        this.editor = editorElement;
        this.analyzer = new VJAudioAnalyzer();
        this.generator = new VJMaterialGenerator();
        this.analysis = null;
    }
    
    async handleAudioUpload(file) {
        console.log('分析音频:', file.name);
        
        // 显示加载状态
        this.showStatus('分析中...');
        
        // 分析音频
        this.analysis = await this.analyzer.analyze(file);
        
        if (this.analysis.success) {
            // 填充编辑器
            this.fillEditor();
            this.showStatus('✅ 分析完成');
            return true;
        } else {
            this.showStatus('❌ 分析失败: ' + this.analysis.error);
            return false;
        }
    }
    
    fillEditor() {
        if (!this.analysis) return;
        
        const data = this.analyzer.toEditorFormat(this.analysis);
        
        // 填充BPM
        const bpmInput = this.editor.querySelector('[name="bpm"], #bpm-input');
        if (bpmInput) bpmInput.value = data.bpm;
        
        // 填充调性
        const keyInput = this.editor.querySelector('[name="key"], #key-input');
        if (keyInput) keyInput.value = data.key;
        
        // 填充时长
        const durationEl = this.editor.querySelector('[name="duration"], #duration');
        if (durationEl) durationEl.textContent = `${data.duration.toFixed(1)}s`;
        
        // 生成素材提示词
        const materials = this.generator.generateForSections(
            data.sections, 
            data.bpm, 
            data.key
        );
        
        // 填充段落
        const sectionsContainer = this.editor.querySelector('#sections, .sections');
        if (sectionsContainer) {
            sectionsContainer.innerHTML = '';
            materials.forEach((m, i) => {
                const el = document.createElement('div');
                el.className = 'section-item';
                el.innerHTML = `
                    <span class="section-name">${m.section}</span>
                    <span class="section-time">${m.start.toFixed(1)}s - ${m.end.toFixed(1)}s</span>
                    <span class="section-prompt">${m.prompt}</span>
                `;
                el.onclick = () => this.selectSection(i);
                sectionsContainer.appendChild(el);
            });
        }
        
        // 存储素材数据
        this.materials = materials;
    }
    
    selectSection(index) {
        const section = this.materials[index];
        if (!section) return;
        
        // 更新选中状态
        const items = this.editor.querySelectorAll('.section-item');
        items.forEach((item, i) => {
            item.classList.toggle('selected', i === index);
        });
        
        // 触发素材生成
        this.onSectionSelect?.(section);
    }
    
    showStatus(message) {
        const statusEl = this.editor.querySelector('#status, .status');
        if (statusEl) statusEl.textContent = message;
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { VJAudioAnalyzer, VJMaterialGenerator, VJEditorIntegration };
}

// 全局
window.VJAudioAnalyzer = VJAudioAnalyzer;
window.VJMaterialGenerator = VJMaterialGenerator;
window.VJEditorIntegration = VJEditorIntegration;
