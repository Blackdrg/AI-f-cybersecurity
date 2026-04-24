const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

/**
 * Official Node.js SDK for AI-f Enterprise Face Recognition.
 */
class AIFClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = apiKey;
    }

    async recognize(imagePath, topK = 1) {
        try {
            const form = new FormData();
            form.append('image', fs.createReadStream(imagePath));
            form.append('top_k', topK);

            const response = await axios.post(`${this.baseUrl}/api/recognize`, form, {
                headers: {
                    ...form.getHeaders(),
                    'Authorization': `Bearer ${this.apiKey}`
                }
            });
            return response.data;
        } catch (error) {
            throw new Error(`Recognition failed: ${error.response ? error.response.data.error : error.message}`);
        }
    }

    async getHealth() {
        const response = await axios.get(`${this.baseUrl}/api/health`, {
            headers: { 'Authorization': `Bearer ${this.apiKey}` }
        });
        return response.data;
    }
}

module.exports = AIFClient;
