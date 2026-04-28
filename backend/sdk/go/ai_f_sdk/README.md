# AI-f Go SDK

Official Go client library for the AI-f Enterprise Face Recognition API.

## Installation

```bash
go get github.com/owner/ai-f-backend/sdk/go/ai_f_sdk
```

## Quick Start

```go
package main

import (
	"fmt"
	"log"
	"github.com/owner/ai-f-backend/sdk/go/ai_f_sdk"
)

func main() {
	// Initialize client
	client := ai_f_sdk.NewClient("http://localhost:8000", "your-api-key")
	defer client.Close()

	// Perform recognition
	result, err := client.Recognize("person.jpg", 1, 0.4, true)
	if err != nil {
		log.Fatal(err)
	}

	// Print results
	for _, face := range result.Faces {
		for _, match := range face.Matches {
			fmt.Printf("Matched: %s (score: %.2f%%)\n", *match.Name, match.Score*100)
		}
	}

	// Enroll a new person
	enrollResult, err := client.Enroll("John Doe", []string{"photo1.jpg", "photo2.jpg"}, true)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Enrolled person ID: %s\n", enrollResult.PersonID)
}
```

## Features

- **Face Recognition**: Recognize faces in images with spoof detection
- **Person Enrollment**: Enroll new identities with multiple images
- **Person Management**: Get, update, delete person records
- **System Health**: Check API and model service health
- **Multi-modal**: Support for voice, gait, and behavioral biometrics (coming soon)

## Configuration

Optional configuration via functional options:

```go
client := ai_f_sdk.NewClient(
    "http://localhost:8000",
    "your-api-key",
    func(c *ai_f_sdk.Config) {
        c.Timeout = 60 * time.Second
    },
)
```

## Error Handling

All SDK methods return detailed errors with HTTP status codes:

```go
result, err := client.Recognize("person.jpg", 1, 0.4, true)
if err != nil {
    var apiErr *ai_f_sdk.AIFClientError
    if errors.As(err, &apiErr) {
        fmt.Printf("API Error %d: %s\n", apiErr.StatusCode, apiErr.Message)
    } else {
        fmt.Printf("Other error: %v\n", err)
    }
}
```

## Authentication

The SDK uses Bearer token authentication. Obtain an API key from your
AI-f server admin or via OAuth2 flow.

## Concurrency

The client is safe for concurrent use by multiple goroutines.

## Roadmap

- [ ] WebSocket streaming support
- [ ] Batch operations
- [ ] OTA model downloads
- [ ] Federated learning client
- [ ] Multi-organization support
