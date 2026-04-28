// Official Go SDK for AI-f Enterprise Face Recognition
//
// This SDK provides a simple interface for face recognition, enrollment,
// and management operations with the AI-f server.
//
// Installation:
//   go get github.com/owner/ai-f-backend/sdk/go/ai_f_sdk
//
// Example:
//   client := ai_f_sdk.NewClient("http://localhost:8000", "your-api-key")
//   result, err := client.Recognize("person.jpg", 1, 0.4, true)
//   fmt.Printf("Recognized: %v\n", result.Faces[0].Matches[0].Name)
package ai_f_sdk

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"time"
)

// Client represents the AI-f SDK client
type Client struct {
	baseURL    string
	apiKey     string
	timeout    time.Duration
	httpClient *http.Client
}

// Config optional configuration for the client
type Config struct {
	Timeout    time.Duration
	HTTPClient *http.Client
}

// RecognitionResult represents a recognition response
type RecognitionResult struct {
	Faces []DetectedFace `json:"faces"`
}

// DetectedFace represents a detected face in an image
type DetectedFace struct {
	FaceBox              []float64         `json:"face_box"`
	FaceEmbeddingID      string            `json:"face_embedding_id,omitempty"`
	Matches              []FaceMatch       `json:"matches"`
	InferenceMs          float64           `json:"inference_ms"`
	IsUnknown            bool              `json:"is_unknown"`
	SpoofScore           *float64          `json:"spoof_score,omitempty"`
	ReconstructionConfidence *float64    `json:"reconstruction_confidence,omitempty"`
	Emotion              map[string]float64 `json:"emotion,omitempty"`
	Age                  *int              `json:"age,omitempty"`
	Gender               *string           `json:"gender,omitempty"`
	Behavior             map[string]float64 `json:"behavior,omitempty"`
}

// FaceMatch represents a matched person
type FaceMatch struct {
	PersonID string  `json:"person_id"`
	Name     *string `json:"name,omitempty"`
	Score    float64 `json:"score"`
	Distance float64 `json:"distance"`
}

// EnrollResult represents an enrollment response
type EnrollResult struct {
	PersonID         string  `json:"person_id"`
	NumEmbeddings    int     `json:"num_embeddings"`
	ExampleEmbeddingID string `json:"example_embedding_id"`
	Confidence       *float64 `json:"confidence,omitempty"`
	Message          string  `json:"message"`
}

// Person represents a enrolled person
type Person struct {
	PersonID       string                 `json:"person_id"`
	Name           *string                `json:"name,omitempty"`
	Age            *int                   `json:"age,omitempty"`
	Gender         *string                `json:"gender,omitempty"`
	Embeddings     []string               `json:"embeddings"`
	ConsentRecord  map[string]interface{} `json:"consent_record"`
}

// Error represents an API error response
type ErrorResponse struct {
	Detail string `json:"detail"`
}

// AIFClientError represents an SDK-specific error
type AIFClientError struct {
	Message    string
	StatusCode int
	Response   []byte
}

func (e *AIFClientError) Error() string {
	return fmt.Sprintf("AI-f API error (%d): %s", e.StatusCode, e.Message)
}

// NewClient creates a new AI-f SDK client
func NewClient(baseURL, apiKey string, opts ...func(*Config)) *Client {
	config := &Config{
		Timeout: 30 * time.Second,
	}

	for _, opt := range opts {
		opt(config)
	}

	if config.HTTPClient == nil {
		config.HTTPClient = &http.Client{Timeout: config.Timeout}
	}

	return &Client{
		baseURL:    baseURL,
		apiKey:     apiKey,
		timeout:    config.Timeout,
		httpClient: config.HTTPClient,
	}
}

// Recognize performs face recognition on an image file
func (c *Client) Recognize(imagePath string, topK int, threshold float64, enableSpoofCheck bool) (*RecognitionResult, error) {
	url := fmt.Sprintf("%s/api/recognize", c.baseURL)

	// Open image file
	file, err := os.Open(imagePath)
	if err != nil {
		return nil, fmt.Errorf("failed to open image: %w", err)
	}
	defer file.Close()

	// Create multipart form
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)

	// Add image file
	part, err := writer.CreateFormFile("image", imagePath)
	if err != nil {
		return nil, fmt.Errorf("failed to create form file: %w", err)
	}
	_, err = io.Copy(part, file)
	if err != nil {
		return nil, fmt.Errorf("failed to copy file: %w", err)
	}

	// Add form fields
	_ = writer.WriteField("top_k", fmt.Sprintf("%d", topK))
	_ = writer.WriteField("threshold", fmt.Sprintf("%f", threshold))
	_ = writer.WriteField("enable_spoof_check", fmt.Sprintf("%t", enableSpoofCheck))

	err = writer.Close()
	if err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}

	// Create request
	req, err := http.NewRequest("POST", url, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	// Execute request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Handle errors
	if resp.StatusCode != 200 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		var errResp ErrorResponse
		if err := json.Unmarshal(bodyBytes, &errResp); err == nil {
			return nil, &AIFClientError{
				Message:    errResp.Detail,
				StatusCode: resp.StatusCode,
				Response:   bodyBytes,
			}
		}
		return nil, &AIFClientError{
			Message:    http.StatusText(resp.StatusCode),
			StatusCode: resp.StatusCode,
			Response:   bodyBytes,
		}
	}

	// Parse successful response
	var result RecognitionResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// Enroll enrolls a new person with multiple face images
func (c *Client) Enroll(name string, imagePaths []string, consent bool) (*EnrollResult, error) {
	url := fmt.Sprintf("%s/api/enroll", c.baseURL)

	// Create multipart form
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)

	// Add images
	for _, imgPath := range imagePaths {
		file, err := os.Open(imgPath)
		if err != nil {
			return nil, fmt.Errorf("failed to open image %s: %w", imgPath, err)
		}
		defer file.Close()

		part, err := writer.CreateFormFile("images", imgPath)
		if err != nil {
			return nil, fmt.Errorf("failed to create form file: %w", err)
		}
		_, err = io.Copy(part, file)
		if err != nil {
			return nil, fmt.Errorf("failed to copy file: %w", err)
		}
	}

	// Add form fields
	_ = writer.WriteField("name", name)
	_ = writer.WriteField("consent", fmt.Sprintf("%t", consent))

	err := writer.Close()
	if err != nil {
		return nil, fmt.Errorf("failed to close writer: %w", err)
	}

	// Create request
	req, err := http.NewRequest("POST", url, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", writer.FormDataContentType())

	// Execute request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Handle errors
	if resp.StatusCode != 200 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		var errResp ErrorResponse
		if err := json.Unmarshal(bodyBytes, &errResp); err == nil {
			return nil, &AIFClientError{
				Message:    errResp.Detail,
				StatusCode: resp.StatusCode,
				Response:   bodyBytes,
			}
		}
		return nil, &AIFClientError{
			Message:    http.StatusText(resp.StatusCode),
			StatusCode: resp.StatusCode,
			Response:   bodyBytes,
		}
	}

	// Parse response
	var result EnrollResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &result, nil
}

// GetPerson retrieves details for a specific person
func (c *Client) GetPerson(personID string) (*Person, error) {
	url := fmt.Sprintf("%s/api/persons/%s", c.baseURL, personID)

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+c.apiKey)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		var errResp ErrorResponse
		if err := json.Unmarshal(bodyBytes, &errResp); err == nil {
			return nil, &AIFClientError{
				Message:    errResp.Detail,
				StatusCode: resp.StatusCode,
				Response:   bodyBytes,
			}
		}
		return nil, &AIFClientError{
			Message:    http.StatusText(resp.StatusCode),
			StatusCode: resp.StatusCode,
			Response:   bodyBytes,
		}
	}

	var person Person
	if err := json.NewDecoder(resp.Body).Decode(&person); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &person, nil
}

// DeletePerson deletes a person and all associated data
func (c *Client) DeletePerson(personID string) error {
	url := fmt.Sprintf("%s/api/persons/%s", c.baseURL, personID)

	req, err := http.NewRequest("DELETE", url, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+c.apiKey)

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 && resp.StatusCode != 204 {
		bodyBytes, _ := io.ReadAll(resp.Body)
		var errResp ErrorResponse
		if err := json.Unmarshal(bodyBytes, &errResp); err == nil {
			return &AIFClientError{
				Message:    errResp.Detail,
				StatusCode: resp.StatusCode,
				Response:   bodyBytes,
			}
		}
		return &AIFClientError{
			Message:    http.StatusText(resp.StatusCode),
			StatusCode: resp.StatusCode,
			Response:   bodyBytes,
		}
	}

	return nil
}

// HealthCheck checks system health
func (c *Client) HealthCheck() (map[string]interface{}, error) {
	url := fmt.Sprintf("%s/api/health", c.baseURL)

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return result, nil
}

// Close closes the HTTP client
func (c *Client) Close() error {
	if c.httpClient != nil {
		return c.httpClient.CloseIdleConnections()
	}
	return nil
}
