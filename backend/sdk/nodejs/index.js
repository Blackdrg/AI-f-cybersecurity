const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

/**
 * Official Node.js SDK for AI-f Enterprise Face Recognition.
 * 
 * Provides methods for face recognition, enrollment, person management,
 * and system operations.
 * 
 * Example:
 *   const AIFClient = require('./index.js');
 *   const client = new AIFClient('http://localhost:8000', 'your-api-key');
 *   const result = await client.recognize('person.jpg');
 *   console.log(result.faces[0].matches);
 */
class AIFClient {
    /**
     * Create a new AI-f client.
     * @param {string} baseUrl - Base URL of the AI-f server
     * @param {string} apiKey - API key for authentication
     */
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.apiKey = apiKey;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`
        };
    }

    /**
     * Perform face recognition on an image.
     * @param {string} imagePath - Path to the image file
     * @param {number} topK - Number of top matches to return (default: 1)
     * @param {number} threshold - Recognition threshold 0-1 (default: 0.4)
     * @param {boolean} enableSpoofCheck - Enable liveness detection (default: true)
     * @returns {Promise<Object>} Recognition result
     */
    async recognize(imagePath, topK = 1, threshold = 0.4, enableSpoofCheck = true) {
        try {
            const form = new FormData();
            form.append('image', fs.createReadStream(imagePath));
            form.append('top_k', topK);
            form.append('threshold', threshold);
            form.append('enable_spoof_check', enableSpoofCheck);

            const response = await axios.post(`${this.baseUrl}/api/recognize`, form, {
                headers: {
                    ...form.getHeaders(),
                    ...this.headers
                }
            });
            return response.data;
        } catch (error) {
            throw new Error(`Recognition failed: ${error.response ? error.response.data?.detail || error.response.data?.error : error.message}`);
        }
    }

    /**
     * Perform face recognition on image buffer.
     * @param {Buffer} imageBuffer - Raw image buffer
     * @param {string} filename - Filename for the upload
     * @param {number} topK - Number of top matches
     * @param {number} threshold - Recognition threshold
     * @returns {Promise<Object>} Recognition result
     */
    async recognizeBuffer(imageBuffer, filename = 'image.jpg', topK = 1, threshold = 0.4) {
        try {
            const form = new FormData();
            form.append('image', imageBuffer, { filename });
            form.append('top_k', topK);
            form.append('threshold', threshold);

            const response = await axios.post(`${this.baseUrl}/api/recognize`, form, {
                headers: {
                    ...form.getHeaders(),
                    ...this.headers
                }
            });
            return response.data;
        } catch (error) {
            throw new Error(`Recognition failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }

    /**
     * Enroll a new person with multiple face images.
     * @param {string} name - Person's name
     * @param {string[]} images - Array of image file paths
     * @param {boolean} consent - Whether consent was obtained
     * @param {string} cameraId - Optional camera ID
     * @param {Object} metadata - Optional metadata
     * @returns {Promise<Object>} Enrollment result
     */
    async enroll(name, images, consent = true, cameraId = null, metadata = null) {
        try {
            const form = new FormData();

            for (const imagePath of images) {
                form.append('images', fs.createReadStream(imagePath));
            }

            form.append('name', name);
            form.append('consent', consent);

            if (cameraId) form.append('camera_id', cameraId);
            if (metadata) form.append('metadata', JSON.stringify(metadata));

            const response = await axios.post(`${this.baseUrl}/api/enroll`, form, {
                headers: {
                    ...form.getHeaders(),
                    ...this.headers
                }
            });
            return response.data;
        } catch (error) {
            throw new Error(`Enrollment failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }

    /**
     * Enroll a person with image buffers.
     * @param {string} name - Person's name
     * @param {Buffer[]} imageBuffers - Array of image buffers
     * @param {boolean} consent - Whether consent was obtained
     * @returns {Promise<Object>} Enrollment result
     */
    async enrollBuffers(name, imageBuffers, consent = true) {
        try {
            const form = new FormData();

            imageBuffers.forEach((buffer, i) => {
                form.append('images', buffer, { filename: `image_${i}.jpg` });
            });

            form.append('name', name);
            form.append('consent', consent);

            const response = await axios.post(`${this.baseUrl}/api/enroll`, form, {
                headers: {
                    ...form.getHeaders(),
                    ...this.headers
                }
            });
            return response.data;
        } catch (error) {
            throw new Error(`Enrollment failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }

    /**
     * Get person details.
     * @param {string} personId - Unique person identifier
     * @returns {Promise<Object>} Person details
     */
    async getPerson(personId) {
        try {
            const response = await axios.get(
                `${this.baseUrl}/api/persons/${personId}`,
                { headers: this.headers }
            );
            return response.data;
        } catch (error) {
            throw new Error(`Get person failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }

    /**
     * Update person details.
     * @param {string} personId - Unique person identifier
     * @param {Object} updates - Fields to update (name, age, gender)
     * @returns {Promise<Object>} Updated person details
     */
    async updatePerson(personId, updates) {
        try {
            const response = await axios.put(
                `${this.baseUrl}/api/persons/${personId}`,
                updates,
                { headers: { ...this.headers, 'Content-Type': 'application/json' } }
            );
            return response.data;
        } catch (error) {
            throw new Error(`Update person failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }

    /**
     * Delete a person and all associated data.
     * @param {string} personId - Unique person identifier
     * @returns {Promise<Object>} Deletion confirmation
     */
    async deletePerson(personId) {
        try {
            const response = await axios.delete(
                `${this.baseUrl}/api/persons/${personId}`,
                { headers: this.headers }
            );
            return response.data;
        } catch (error) {
            throw new Error(`Delete person failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }

    /**
     * Search for persons by name or metadata.
     * @param {string} query - Search query string
     * @param {number} limit - Maximum results (default: 10)
     * @returns {Promise<Object>} List of matching persons
     */
    async searchPersons(query, limit = 10) {
        try {
            const response = await axios.get(
                `${this.baseUrl}/api/persons/search`,
                {
                    params: { query, limit },
                    headers: this.headers
                }
            );
            return response.data;
        } catch (error) {
            throw new Error(`Search failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }

    /**
     * Get system metrics and statistics.
     * @returns {Promise<Object>} System metrics
     */
    async getMetrics() {
        try {
            const response = await axios.get(
                `${this.baseUrl}/api/metrics`,
                { headers: this.headers }
            );
            return response.data;
        } catch (error) {
            throw new Error(`Get metrics failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }

    /**
     * Check system health status.
     * @returns {Promise<Object>} Health status
     */
    async getHealth() {
        try {
            const response = await axios.get(
                `${this.baseUrl}/api/health`,
                { headers: this.headers }
            );
            return response.data;
        } catch (error) {
            throw new Error(`Health check failed: ${error.message}`);
        }
    }

    /**
     * Get audit logs for compliance and forensics.
     * @param {number} limit - Maximum entries (default: 100)
     * @param {string} startDate - Filter from this date
     * @param {string} endDate - Filter until this date
     * @param {string} action - Filter by action type
     * @returns {Promise<Object>} Audit log entries
     */
    async getAuditLogs(limit = 100, startDate = null, endDate = null, action = null) {
        try {
            const params = { limit };
            if (startDate) params.start_date = startDate;
            if (endDate) params.end_date = endDate;
            if (action) params.action = action;

            const response = await axios.get(
                `${this.baseUrl}/api/audit`,
                { params, headers: this.headers }
            );
            return response.data;
        } catch (error) {
            throw new Error(`Get audit logs failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }

    /**
     * Get usage statistics.
     * @param {string} userId - Optional user ID
     * @returns {Promise<Object>} Usage statistics
     */
    async getUsage(userId = null) {
        try {
            const url = userId
                ? `${this.baseUrl}/api/usage/${userId}`
                : `${this.baseUrl}/api/usage`;

            const response = await axios.get(url, { headers: this.headers });
            return response.data;
        } catch (error) {
            throw new Error(`Get usage failed: ${error.response ? error.response.data?.detail : error.message}`);
        }
    }
}

module.exports = AIFClient;
