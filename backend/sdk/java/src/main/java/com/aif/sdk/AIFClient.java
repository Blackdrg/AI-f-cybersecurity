package com.aif.sdk;

import java.io.File;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/**
 * Official Java SDK for AI-f Enterprise Face Recognition.
 */
public class AIFClient {
    private final String baseUrl;
    private final String apiKey;
    private final HttpClient httpClient;

    public AIFClient(String baseUrl, String apiKey) {
        this.baseUrl = baseUrl.replaceAll("/$", "");
        this.apiKey = apiKey;
        this.httpClient = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_2)
                .connectTimeout(Duration.ofSeconds(10))
                .build();
    }

    public String getHealth() throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/api/health"))
                .header("Authorization", "Bearer " + apiKey)
                .GET()
                .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
        return response.body();
    }

    // In a complete implementation, add multipart form data logic for /api/recognize
    public String recognize(File image, int topK) throws UnsupportedOperationException {
        throw new UnsupportedOperationException("Multipart form upload implementation omitted for brevity in stub.");
    }
}
