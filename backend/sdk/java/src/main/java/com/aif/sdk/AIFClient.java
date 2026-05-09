package com.aif.sdk;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpRequest.BodyPublisher;
import java.net.http.HttpResponse.BodyHandlers;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.function.Supplier;

import javax.annotation.Nonnull;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Official Java SDK for AI-f Enterprise Face Recognition.
 * 
 * Complete implementation providing:
 * - Face recognition with liveness detection
 * - Person enrollment with multiple images
 * - Person management (get, update, delete, search)
 * - System health and metrics
 * - Audit logging and compliance data
 */
public class AIFClient {
    private final String baseUrl;
    private final String apiKey;
    private final Duration timeout;
    private final HttpClient httpClient;

    /**
     * Create a new AI-f SDK client.
     * @param baseUrl Base URL of the AI-f server (e.g., http://localhost:8000)
     * @param apiKey API key for authentication
     */
    public AIFClient(@Nonnull String baseUrl, @Nonnull String apiKey) {
        this(baseUrl, apiKey, Duration.ofSeconds(30));
    }

    /**
     * Create a new AI-f SDK client with custom timeout.
     * @param baseUrl Base URL of the AI-f server
     * @param apiKey API key for authentication
     * @param timeout Request timeout duration
     */
    public AIFClient(@Nonnull String baseUrl, @Nonnull String apiKey, @Nonnull Duration timeout) {
        this.baseUrl = baseUrl.replaceAll("/$", "");
        this.apiKey = apiKey;
        this.timeout = timeout;

        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_2)
                .connectTimeout(timeout)
                .followRedirects(HttpClient.Redirect.NORMAL)
                .build();
    }

    /**
     * Build authorization header
     */
    private HttpRequest.Builder authBuilder(String method, String url) {
        return HttpRequest.newBuilder()
                .uri(URI.create(url))
                .method(method, HttpRequest.BodyPublishers.noBody())
                .timeout(timeout)
                .header("Authorization", "Bearer " + apiKey)
                .header("Accept", "application/json");
    }

    /**
     * Build multipart form request with file
     */
    private HttpRequest.Builder multipartBuilder(String method, String url) {
        return HttpRequest.newBuilder()
                .uri(URI.create(url))
                .method(method, null)
                .timeout(timeout)
                .header("Authorization", "Bearer " + apiKey);
    }

    /**
     * Perform face recognition on an image file.
     * @param image JPEG/PNG image file
     * @param topK Number of top matches (default: 1)
     * @param threshold Recognition threshold 0-1 (default: 0.4)
     * @param enableSpoofCheck Enable liveness detection (default: true)
     * @param cameraId Optional camera ID
     * @return Recognition result JSON
     * @throws IOException On network or API error
     */
    public JSONObject recognize(File image, int topK, double threshold, boolean enableSpoofCheck, String cameraId) 
            throws IOException, InterruptedException {
        
        try {
            String boundary = "----AIFFormBoundary" + System.currentTimeMillis();
            String CRLF = "\r\n";
            
            StringBuilder sb = new StringBuilder();
            sb.append("--").append(boundary).append(CRLF);
            sb.append("Content-Disposition: form-data; name=\"top_k\"").append(CRLF).append(CRLF);
            sb.append(topK).append(CRLF);
            
            sb.append("--").append(boundary).append(CRLF);
            sb.append("Content-Disposition: form-data; name=\"threshold\"").append(CRLF).append(CRLF);
            sb.append(threshold).append(CRLF);
            
            sb.append("--").append(boundary).append(CRLF);
            sb.append("Content-Disposition: form-data; name=\"enable_spoof_check\"").append(CRLF).append(CRLF);
            sb.append(enableSpoofCheck).append(CRLF);
            
            if (cameraId != null && !cameraId.isEmpty()) {
                sb.append("--").append(boundary).append(CRLF);
                sb.append("Content-Disposition: form-data; name=\"camera_id\"").append(CRLF).append(CRLF);
                sb.append(cameraId).append(CRLF);
            }
            
            sb.append("--").append(boundary).append(CRLF);
            sb.append("Content-Disposition: form-data; name=\"image\"; filename=\"").append(image.getName()).append("\"").append(CRLF);
            sb.append("Content-Type: image/jpeg").append(CRLF).append(CRLF);
            
            byte[] preamble = sb.toString().getBytes("UTF-8");
            byte[] epilogue = ("\r\n--" + boundary + "--\r\n").getBytes("UTF-8");
            
            byte[] fileBytes = Files.readAllBytes(image.toPath());
            int contentLength = preamble.length + fileBytes.length + epilogue.length;
            
            BodyPublisher bodyPublisher = HttpRequest.BodyPublishers.ofByteArrays(
                java.util.List.of(preamble, fileBytes, epilogue)
            );
            
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/api/recognize"))
                    .header("Authorization", "Bearer " + apiKey)
                    .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                    .POST(bodyPublisher)
                    .timeout(timeout)
                    .build();
            
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            
            if (response.statusCode() >= 200 && response.statusCode() < 300) {
                return new JSONObject(new String(response.body()));
            } else {
                String errorBody = new String(response.body());
                throw new IOException("Recognition failed: " + response.statusCode() + " " + errorBody);
            }
        } catch (Exception e) {
            throw new IOException("Recognition failed: " + e.getMessage(), e);
        }
    }

    /**
     * Enroll a new person with multiple face images.
     * @param name Person's full name
     * @param images Array of image files (minimum 3 recommended)
     * @param consent Whether explicit consent was obtained (required)
     * @param cameraId Optional camera ID for audit
     * @param metadata Optional metadata JSON string
     * @param age Optional age
     * @param gender Optional gender
     * @return Enrollment result
     * @throws IOException On network or API error
     */
    public JSONObject enroll(
            String name, 
            File[] images, 
            boolean consent, 
            String cameraId, 
            String metadata,
            Integer age, 
            String gender) 
            throws IOException, InterruptedException {
        
        if (images == null || images.length == 0) {
            throw new IllegalArgumentException("At least one image is required for enrollment");
        }

        try {
            String boundary = "----AIFFormBoundary" + System.currentTimeMillis();
            StringBuilder sb = new StringBuilder();
            
            // Text fields
            sb.append("--").append(boundary).append("\r\n");
            sb.append("Content-Disposition: form-data; name=\"name\"").append("\r\n\r\n");
            sb.append(name).append("\r\n");
            
            sb.append("--").append(boundary).append("\r\n");
            sb.append("Content-Disposition: form-data; name=\"consent\"").append("\r\n\r\n");
            sb.append(consent).append("\r\n");
            
            if (cameraId != null) {
                sb.append("--").append(boundary).append("\r\n");
                sb.append("Content-Disposition: form-data; name=\"camera_id\"").append("\r\n\r\n");
                sb.append(cameraId).append("\r\n");
            }
            
            if (metadata != null) {
                sb.append("--").append(boundary).append("\r\n");
                sb.append("Content-Disposition: form-data; name=\"metadata\"").append("\r\n\r\n");
                sb.append(metadata).append("\r\n");
            }
            
            if (age != null) {
                sb.append("--").append(boundary).append("\r\n");
                sb.append("Content-Disposition: form-data; name=\"age\"").append("\r\n\r\n");
                sb.append(age).append("\r\n");
            }
            
            if (gender != null) {
                sb.append("--").append(boundary).append("\r\n");
                sb.append("Content-Disposition: form-data; name=\"gender\"").append("\r\n\r\n");
                sb.append(gender).append("\r\n");
            }
            
            byte[] preamble = sb.toString().getBytes("UTF-8");
            byte[] epilogue = ("\r\n--" + boundary + "--\r\n").getBytes("UTF-8");
            
            // Build file parts
            java.util.List<byte[]> parts = new java.util.ArrayList<>();
            parts.add(preamble);
            
            for (File img : images) {
                StringBuilder imgHeader = new StringBuilder();
                imgHeader.append("--").append(boundary).append("\r\n");
                imgHeader.append("Content-Disposition: form-data; name=\"images\"; filename=\"").append(img.getName()).append("\"").append("\r\n");
                imgHeader.append("Content-Type: image/jpeg").append("\r\n\r\n");
                parts.add(imgHeader.toString().getBytes("UTF-8"));
                parts.add(Files.readAllBytes(img.toPath()));
                parts.add("\r\n".getBytes("UTF-8"));
            }
            
            parts.add(epilogue);
            
            int totalSize = parts.stream().mapToInt(b -> b.length).sum();
            BodyPublisher bodyPublisher = HttpRequest.BodyPublishers.ofByteArrays(parts);
            
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(baseUrl + "/api/enroll"))
                    .header("Authorization", "Bearer " + apiKey)
                    .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                    .POST(bodyPublisher)
                    .timeout(timeout)
                    .build();
            
            HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
            
            if (response.statusCode() >= 200 && response.statusCode() < 300) {
                return new JSONObject(new String(response.body()));
            } else {
                String errorBody = new String(response.body());
                throw new IOException("Enrollment failed: " + response.statusCode() + " " + errorBody);
            }
        } catch (Exception e) {
            throw new IOException("Enrollment failed: " + e.getMessage(), e);
        }
    }

    /**
     * Simple enroll with one image (convenience method).
     */
    public JSONObject enroll(String name, File image, boolean consent) 
            throws IOException, InterruptedException {
        return enroll(name, new File[]{image}, consent, null, null, null, null);
    }

    /**
     * Get person details.
     * @param personId Unique identifier
     * @return Person details JSON
     */
    public JSONObject getPerson(String personId) 
            throws IOException, InterruptedException {
        HttpRequest request = authBuilder("GET", baseUrl + "/api/persons/" + personId).build();
        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        
        if (response.statusCode() >= 200 && response.statusCode() < 300) {
            return new JSONObject(new String(response.body()));
        } else {
            throw new IOException("Get person failed: " + response.statusCode() + " " + new String(response.body()));
        }
    }

    /**
     * Update person details.
     * @param personId Unique identifier
     * @param name New name (null = no change)
     * @param age New age (null = no change)
     * @param gender New gender (null = no change)
     * @return Updated person JSON
     */
    public JSONObject updatePerson(String personId, String name, Integer age, String gender) 
            throws IOException, InterruptedException {
        
        JSONObject payload = new JSONObject();
        if (name != null) payload.put("name", name);
        if (age != null) payload.put("age", age);
        if (gender != null) payload.put("gender", gender);
        
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/api/persons/" + personId))
                .header("Authorization", "Bearer " + apiKey)
                .header("Content-Type", "application/json")
                .PUT(HttpRequest.BodyPublishers.ofString(payload.toString()))
                .timeout(timeout)
                .build();
        
        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        
        if (response.statusCode() >= 200 && response.statusCode() < 300) {
            return new JSONObject(new String(response.body()));
        } else {
            throw new IOException("Update failed: " + response.statusCode() + " " + new String(response.body()));
        }
    }

    /**
     * Delete a person and all associated data.
     * @param personId Unique identifier
     * @return Deletion confirmation
     */
    public boolean deletePerson(String personId) 
            throws IOException, InterruptedException {
        HttpRequest request = authBuilder("DELETE", baseUrl + "/api/persons/" + personId).build();
        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        return response.statusCode() >= 200 && response.statusCode() < 300;
    }

    /**
     * Search for persons by name or metadata.
     * @param query Search query string
     * @param limit Maximum results (default: 10)
     * @return Search results with persons array and total count
     */
    public JSONObject searchPersons(String query, int limit) 
            throws IOException, InterruptedException {
        String url = String.format("%s/api/persons/search?query=%s&limit=%d", 
                baseUrl, 
                java.net.URLEncoder.encode(query, "UTF-8"),
                limit);
        
        HttpRequest request = authBuilder("GET", url).build();
        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        
        if (response.statusCode() >= 200 && response.statusCode() < 300) {
            return new JSONObject(new String(response.body()));
        } else {
            throw new IOException("Search failed: " + response.statusCode() + " " + new String(response.body()));
        }
    }

    /**
     * Get system metrics and statistics.
     * @return Metrics JSON
     */
    public JSONObject getMetrics() 
            throws IOException, InterruptedException {
        HttpRequest request = authBuilder("GET", baseUrl + "/api/metrics").build();
        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        
        if (response.statusCode() >= 200 && response.statusCode() < 300) {
            return new JSONObject(new String(response.body()));
        } else {
            throw new IOException("Get metrics failed: " + response.statusCode());
        }
    }

    /**
     * Check system health status.
     * @return Health JSON
     */
    public JSONObject getHealth() 
            throws IOException, InterruptedException {
        HttpRequest request = authBuilder("GET", baseUrl + "/api/health").build();
        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        
        if (response.statusCode() >= 200 && response.statusCode() < 300) {
            return new JSONObject(new String(response.body()));
        } else {
            throw new IOException("Health check failed: " + response.statusCode());
        }
    }

    /**
     * Get audit logs for compliance.
     * @param limit Maximum entries
     * @param startDate ISO start date
     * @param endDate ISO end date
     * @param action Action type filter
     * @param personId Person filter
     * @return Audit logs JSON
     */
    public JSONObject getAuditLogs(
            int limit, 
            String startDate, 
            String endDate, 
            String action, 
            String personId) 
            throws IOException, InterruptedException {
        
        StringBuilder url = new StringBuilder(baseUrl + "/api/audit?limit=" + limit);
        if (startDate != null) url.append("&start_date=").append(java.net.URLEncoder.encode(startDate, "UTF-8"));
        if (endDate != null) url.append("&end_date=").append(java.net.URLEncoder.encode(endDate, "UTF-8"));
        if (action != null) url.append("&action=").append(java.net.URLEncoder.encode(action, "UTF-8"));
        if (personId != null) url.append("&person_id=").append(java.net.URLEncoder.encode(personId, "UTF-8"));
        
        HttpRequest request = authBuilder("GET", url.toString()).build();
        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        
        if (response.statusCode() >= 200 && response.statusCode() < 300) {
            return new JSONObject(new String(response.body()));
        } else {
            throw new IOException("Get audit logs failed: " + response.statusCode());
        }
    }

    /**
     * Get usage statistics.
     * @param userId Optional specific user ID
     * @return Usage JSON
     */
    public JSONObject getUsage(String userId) 
            throws IOException, InterruptedException {
        String path = (userId != null) ? "/api/usage/" + userId : "/api/usage";
        HttpRequest request = authBuilder("GET", baseUrl + path).build();
        HttpResponse<byte[]> response = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray());
        
        if (response.statusCode() >= 200 && response.statusCode() < 300) {
            return new JSONObject(new String(response.body()));
        } else {
            throw new IOException("Get usage failed: " + response.statusCode());
        }
    }

    /**
     * Close the HTTP client and release resources.
     */
    public void close() {
        httpClient.dispatcher().executorService().shutdown();
    }
}
