#!/bin/bash
# AI-f Air-Gapped Enterprise Installer
# Version: 1.0
# Usage: sudo ./install-airgap.sh [--k8s|--docker]

set -e

MODE="docker"
INSTALL_DIR="/opt/ai-f"
DATA_DIR="/var/lib/ai-f"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --k8s)
            MODE="k8s"
            shift
            ;;
        --docker)
            MODE="docker"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "========================================"
echo "AI-f Air-Gapped Enterprise Installer"
echo "Mode: $MODE"
echo "========================================"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

# Check prerequisites
check_prerequisites() {
    echo "[1/6] Checking prerequisites..."
    
    if [[ "$MODE" == "docker" ]]; then
        if ! command -v docker &> /dev/null; then
            echo "ERROR: Docker is not installed"
            echo "Install Docker: apt-get install docker.io"
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            echo "ERROR: Docker Compose is not installed"
            echo "Install Docker Compose: apt-get install docker-compose"
            exit 1
        fi
    fi
    
    if [[ "$MODE" == "k8s" ]]; then
        if ! command -v kubectl &> /dev/null; then
            echo "ERROR: kubectl is not installed"
            exit 1
        fi
        
        if ! command -v helm &> /dev/null; then
            echo "ERROR: Helm is not installed"
            exit 1
        fi
    fi
    
    echo "Prerequisites OK"
}

# Create directories
create_directories() {
    echo "[2/6] Creating directories..."
    
    mkdir -p "$INSTALL_DIR"/{config,models,logs}
    mkdir -p "$DATA_DIR"/{postgres,redis,embeddings}
    
    # Set permissions
    chown -R 1000:1000 "$DATA_DIR"
    chmod 750 "$INSTALL_DIR"
    
    echo "Directories created"
}

# Load Docker images
load_images() {
    echo "[3/6] Loading Docker images..."
    
    if [[ -d "docker-images" ]]; then
        for image in docker-images/*.tar; do
            if [[ -f "$image" ]]; then
                echo "Loading $image..."
                docker load -i "$image"
            fi
        done
    else
        echo "WARNING: docker-images directory not found"
        echo "Using pre-pulled images or public registry"
    fi
    
    echo "Images loaded"
}

# Generate TLS certificates
generate_certs() {
    echo "[4/6] Generating TLS certificates..."
    
    # Check for existing certs
    if [[ -f "$INSTALL_DIR/config/cert.pem" ]]; then
        echo "Certificates already exist, skipping..."
        return
    fi
    
    mkdir -p "$INSTALL_DIR/config"
    
    # Generate self-signed certificate
    openssl req -x509 -newkey rsa:4096 \
        -keyout "$INSTALL_DIR/config/key.pem" \
        -out "$INSTALL_DIR/config/cert.pem" \
        -days 365 \
        -nodes \
        -subj "/CN=ai-f.local/O=AI-f/OU=AirGap" \
        2>/dev/null
    
    chmod 600 "$INSTALL_DIR/config/key.pem"
    chmod 644 "$INSTALL_DIR/config/cert.pem"
    
    echo "Certificates generated"
}

# Start services
start_services() {
    echo "[5/6] Starting services..."
    
    if [[ "$MODE" == "docker" ]]; then
        # Create environment file
        cat > "$INSTALL_DIR/config/.env" <<EOF
# AI-f Air-Gap Configuration
ENVIRONMENT=airgap
OFFLINE_MODE=true
DISABLE_EXTERNAL_APIS=true
DB_HOST=localhost
DB_PORT=5432
DB_USER=ai_f
DB_NAME=face_recognition
REDIS_HOST=localhost
REDIS_PORT=6379
MODEL_PATH=/opt/ai-f/models
TLS_CERT=/opt/ai-f/config/cert.pem
TLS_KEY=/opt/ai-f/config/key.pem
EOF
        
        # Check for compose file
        if [[ -f "docker-compose.airgap.yml" ]]; then
            docker-compose -f docker-compose.airgap.yml up -d
        else
            docker-compose up -d
        fi
        
        echo "Waiting for services to start..."
        sleep 10
        
        # Verify services
        docker-compose ps
    fi
    
    if [[ "$MODE" == "k8s" ]]; then
        # Load Kubernetes images
        if [[ -d "k8s-images" ]]; then
            for image in k8s-images/*.tar; do
                if [[ -f "$image" ]]; then
                    kind load docker-image "$image" --name ai-f || true
                fi
            done
        fi
        
        # Apply Kubernetes manifests
        if [[ -d "manifests" ]]; then
            kubectl apply -f manifests/airgap/
            kubectl wait --for=condition=available --timeout=300s deployment -n ai-f-system --all || true
        fi
    fi
    
    echo "Services started"
}

# Verify installation
verify_installation() {
    echo "[6/6] Verifying installation..."
    
    if [[ "$MODE" == "docker" ]]; then
        # Check if API is responding
        sleep 5
        if curl -k https://localhost:8443/api/health 2>/dev/null | grep -q "healthy"; then
            echo "✓ API is healthy"
        else
            echo "⚠ API health check failed, checking logs..."
            docker-compose logs --tail=20
        fi
    fi
    
    if [[ "$MODE" == "k8s" ]]; then
        kubectl get pods -n ai-f-system
    fi
    
    echo ""
    echo "========================================"
    echo "Installation Complete!"
    echo "========================================"
    echo "API URL: https://$(hostname -I | awk '{print $1}'):8443"
    echo "Logs: $INSTALL_DIR/logs"
    echo "Data: $DATA_DIR"
    echo "========================================"
}

# Main installation flow
main() {
    check_prerequisites
    create_directories
    load_images
    generate_certs
    start_services
    verify_installation
}

main "$@"