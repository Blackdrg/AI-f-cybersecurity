#!/bin/bash
# Generate SBOM (Software Bill of Materials) for AI-f
# Outputs CycloneDX JSON format
#
# Usage:
#   ./scripts/generate_sbom.sh [output-file]
#   ./scripts/generate_sbom.sh sbom.xml

set -e

OUTPUT_FILE="${1:-sbom/cyclonedx.json}"
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")

echo "Generating SBOM..."

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Method 1: Use Syft (recommended)
if command -v syft &> /dev/null; then
    echo "Using Syft..."
    syft dir:./backend \
        --platform linux/amd64 \
        --output cyclonedx-json \
        --file "$OUTPUT_FILE"
    
# Method 2: Use GitHub's sbom-action via container
elif command -v docker &> /dev/null; then
    echo "Using Docker (anchore/sbom-action)..."
    docker run --rm \
        -v "$(pwd):/src" \
        -w /src \
        ghcr.io/anchore/sbom-action:latest \
        --platform linux/amd64 \
        --output-format cyclonedx-json \
        --file "$OUTPUT_FILE" .
else
    echo "ERROR: Neither syft nor docker found. Install syft: https://github.com/anchore/syft#installation"
    exit 1
fi

# Validate SBOM
if command -v cyclonedx-cli &> /dev/null; then
    echo "Validating SBOM..."
    cyclonedx validate --input-file "$OUTPUT_FILE"
fi

echo "SBOM generated: $OUTPUT_FILE"
echo "Size: $(du -h "$OUTPUT_FILE" | cut -f1)"

# Optional: Upload to dependency track
if [ -n "${DEPENDENCY_TRACK_URL}" ] && [ -n "${DEPENDENCY_TRACK_API_KEY}" ]; then
    echo "Uploading to Dependency Track..."
    curl -X POST \
        -H "X-API-Key: ${DEPENDENCY_TRACK_API_KEY}" \
        -F "bom=@${OUTPUT_FILE}" \
        "${DEPENDENCY_TRACK_URL}/api/v1/bom"
    echo "Uploaded to Dependency Track"
fi
