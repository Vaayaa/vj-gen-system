/**
 * VJ-Gen 音频分析集成
 * 调用本地Python服务进行专业级音频分析
 */

class VJAudioAnalyzer {
    constructor() {
        this.serverUrl = 'http://localhost:5000';
        this.analysisResult = null;
    }

    /**
     * 上传并分析音频文件
     * @param {File} file - 音频文件
     * @returns {Promise<Object>} 分析结果
     */
    async analyzeFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${this.serverUrl}/analyze`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`);
            }

            this.analysisResult = await response.json();
            return this.analysisResult;
        } catch (error) {
            console.error('Audio analysis failed:', error);
            throw error;
        }
    }

    /**
     * 获取当前分析结果
     */
    getResult() {
        return this.analysisResult;
    }

    /**
     * 生成波形数据
     * @param {AudioBuffer} buffer - Web Audio API buffer
     * @param {number} samples - 波形采样点数
     */
    generateWaveform(buffer, samples = 500) {
        const raw = buffer.getChannelData(0);
        const blockSize = Math.floor(raw.length / samples);
        const data = [];

        for (let i = 0; i < samples; i++) {
            let sum = 0;
            for (let j = 0; j < blockSize && i * blockSize + j < raw.length; j++) {
                sum += Math.abs(raw[i * blockSize + j]);
            }
            data.push(sum / blockSize);
        }

        const max = Math.max(...data);
        return data.map(d => d / max);
    }
}

// 导出全局
window.VJAudioAnalyzer = VJAudioAnalyzer;
