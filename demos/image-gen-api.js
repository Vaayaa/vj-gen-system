/**
 * MiniMax Image Generation API Client
 * VJ-Gen System - V4.5
 * 
 * API Endpoint: https://api.minimax.chat/v1/image_generation
 */

class MiniMaxImageAPI {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.baseURL = 'https://api.minimax.chat/v1';
    }

    /**
     * Generate image using MiniMax API
     * @param {Object} params - Generation parameters
     * @param {string} params.prompt - Image prompt
     * @param {number} [params.num_images=1] - Number of images to generate (1-4)
     * @param {string} [params.aspect_ratio="1:1"] - Aspect ratio (1:1, 16:9, 9:16)
     * @param {string} [params.model="image-01"] - Model to use (image-01, image-01-turbo)
     * @param {string} [params.negative_prompt] - Negative prompt
     * @param {string} [params.group_id] - Group ID for grouping related generations
     * @returns {Promise<Object>} - Generation result with image URLs
     */
    async generateImage({
        prompt,
        num_images = 1,
        aspect_ratio = "1:1",
        model = "image-01",
        negative_prompt = "",
        group_id = ""
    } = {}) {
        const url = `${this.baseURL}/image_generation`;

        const payload = {
            model: model,
            prompt: prompt,
            num_images: Math.min(Math.max(num_images, 1), 4),
            aspect_ratio: aspect_ratio,
        };

        if (negative_prompt) {
            payload.negative_prompt = negative_prompt;
        }

        if (group_id) {
            payload.group_id = group_id;
        }

        console.log('[MiniMax API] Generating image...');
        console.log('[MiniMax API] Prompt:', prompt);
        console.log('[MiniMax API] Aspect Ratio:', aspect_ratio);
        console.log('[MiniMax API] Model:', model);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.apiKey}`
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('[MiniMax API] Error:', response.status, errorText);
                throw new Error(`API Error ${response.status}: ${errorText}`);
            }

            const data = await response.json();
            console.log('[MiniMax API] Success!', data);

            return data;
        } catch (error) {
            console.error('[MiniMax API] Request failed:', error);
            throw error;
        }
    }

    /**
     * Poll for generation result (if using async endpoint)
     * @param {string} taskId - Task ID from initial request
     * @returns {Promise<Object>} - Generation result
     */
    async getGenerationResult(taskId) {
        const url = `${this.baseURL}/image_generation/${taskId}`;

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`
                }
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`API Error ${response.status}: ${errorText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('[MiniMax API] Poll failed:', error);
            throw error;
        }
    }
}

// Export for both browser and Node.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { MiniMaxImageAPI };
} else if (typeof window !== 'undefined') {
    window.MiniMaxImageAPI = MiniMaxImageAPI;
}
