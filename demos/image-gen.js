/**
 * MiniMax 图像生成 — VJ-Gen V4.5
 * Endpoint: https://api.minimax.chat/v1/image_generation
 *
 * 密钥请仅在页面输入框或 sessionStorage 中配置，勿写入仓库。
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
     */
    async generateImage({
        prompt,
        num_images = 1,
        aspect_ratio = '16:9',
        model = 'image-01',
        negative_prompt = '',
    } = {}) {
        if (!this.apiKey) {
            throw new Error('未配置 MiniMax API Key');
        }
        if (!prompt || !String(prompt).trim()) {
            throw new Error('prompt 不能为空');
        }

        const url = `${this.baseURL}/image_generation`;
        const n = Math.min(Math.max(Number(num_images) || 1, 1), 4);

        const payload = {
            model,
            prompt: String(prompt).trim(),
            aspect_ratio,
        };
        if (negative_prompt) payload.negative_prompt = negative_prompt;
        if (n > 1) payload.num_images = n;

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
     * 统一为 { data: [{ url }], raw }，与编辑器主逻辑兼容。
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
            if (Array.isArray(arr)) {
                arr.forEach((x) =>
                    typeof x === 'string' ? pushUrl(x) : pushUrl(x?.url || x?.image_url)
                );
            }
        }

        const normalized = {
            data: urls.map((u) => ({ url: u })),
            raw,
        };

        if (
            normalized.data.length === 0 &&
            raw?.base_resp?.status_code != null &&
            raw.base_resp.status_code !== 0
        ) {
            throw new Error(raw.base_resp.status_msg || '生成失败');
        }

        if (normalized.data.length === 0) {
            throw new Error('响应中未找到图片 URL，请查看控制台 raw 返回');
        }

        return normalized;
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MiniMaxImageAPI };
} else if (typeof window !== 'undefined') {
    window.MiniMaxImageAPI = MiniMaxImageAPI;
}
