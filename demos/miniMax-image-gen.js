/**
 * MiniMax 图像生成 API 客户端（浏览器 / Node）
 * VJ-Gen V4.5 — demos/miniMax-image-gen.js
 *
 * 文档参考: https://www.minimax.io/ （具体 path 以账号控制台为准）
 * 注意: 浏览器直连可能受 CORS 限制，如遇跨域请用本地代理或后端转发。
 */

class MiniMaxImageAPI {
    constructor(apiKey, options = {}) {
        this.apiKey = apiKey || '';
        this.baseURL = (options.baseURL || 'https://api.minimax.chat/v1').replace(/\/$/, '');
    }

    /**
     * @param {object} params
     * @param {string} params.prompt
     * @param {number} [params.num_images=1]
     * @param {string} [params.aspect_ratio="16:9"]
     * @param {string} [params.model="image-01"]
     * @param {string} [params.negative_prompt=""]
     * @param {string} [params.group_id=""]
     */
    async generateImage({
        prompt,
        num_images = 1,
        aspect_ratio = '1:1',
        model = 'image-01',
        negative_prompt = '',
        group_id = '',
    } = {}) {
        if (!this.apiKey) {
            throw new Error('未配置 MiniMax API Key');
        }
        if (!prompt || !String(prompt).trim()) {
            throw new Error('prompt 不能为空');
        }

        const url = `${this.baseURL}/image_generation`;
        const payload = {
            model,
            prompt: String(prompt).trim(),
            num_images: Math.min(Math.max(Number(num_images) || 1, 1), 4),
            aspect_ratio,
        };
        if (negative_prompt) payload.negative_prompt = negative_prompt;
        if (group_id) payload.group_id = group_id;

        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${this.apiKey}`,
            },
            body: JSON.stringify(payload),
        });

        const rawText = await response.text();
        let data;
        try {
            data = rawText ? JSON.parse(rawText) : {};
        } catch {
            throw new Error(`API 返回非 JSON: ${rawText.slice(0, 200)}`);
        }

        if (!response.ok) {
            const msg = data.base_resp?.status_msg || data.message || rawText;
            throw new Error(`MiniMax ${response.status}: ${msg}`);
        }

        return MiniMaxImageAPI.normalizeGenerationResult(data);
    }

    /**
     * 将多种可能的响应形态统一为 { data: [{ url, b64? }], raw }
     * @param {object} data
     */
    static normalizeGenerationResult(data) {
        const raw = data;
        const urls = [];

        const pushUrl = (u) => {
            if (u && typeof u === 'string') urls.push(u);
        };

        if (Array.isArray(data?.data)) {
            for (const item of data.data) {
                if (typeof item === 'string') pushUrl(item);
                else if (item?.url) pushUrl(item.url);
                else if (item?.image_url) pushUrl(item.image_url);
            }
        }

        if (Array.isArray(data?.image_urls)) {
            data.image_urls.forEach(pushUrl);
        }
        if (Array.isArray(data?.data?.image_urls)) {
            data.data.image_urls.forEach(pushUrl);
        }
        if (Array.isArray(data?.images)) {
            for (const im of data.images) {
                if (im?.image_url) pushUrl(im.image_url);
                if (im?.url) pushUrl(im.url);
                if (im?.base64) {
                    urls.push(`data:image/png;base64,${im.base64}`);
                }
            }
        }

        const imgGen = data?.image_generation_result || data?.imageGenerationResult;
        if (imgGen) {
            const arr = imgGen.image_urls || imgGen.images || imgGen.generated_images;
            if (Array.isArray(arr)) arr.forEach((x) => (typeof x === 'string' ? pushUrl(x) : pushUrl(x?.url || x?.image_url)));
        }

        const normalized = {
            data: urls.map((url) => ({ url })),
            raw,
        };

        if (normalized.data.length === 0 && raw?.base_resp?.status_code != null && raw.base_resp.status_code !== 0) {
            throw new Error(raw.base_resp.status_msg || '生成失败');
        }

        return normalized;
    }

    async getGenerationResult(taskId) {
        const url = `${this.baseURL}/image_generation/${taskId}`;
        const response = await fetch(url, {
            method: 'GET',
            headers: { Authorization: `Bearer ${this.apiKey}` },
        });
            const rawText = await response.text();
        let data;
        try {
            data = rawText ? JSON.parse(rawText) : {};
        } catch {
            throw new Error(`API 返回非 JSON: ${rawText.slice(0, 200)}`);
        }
        if (!response.ok) {
            throw new Error(`MiniMax ${response.status}: ${rawText}`);
        }
        return MiniMaxImageAPI.normalizeGenerationResult(data);
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MiniMaxImageAPI };
} else if (typeof window !== 'undefined') {
    window.MiniMaxImageAPI = MiniMaxImageAPI;
}
