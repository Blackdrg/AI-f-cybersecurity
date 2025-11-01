#!/bin/bash

# Check if Docker daemon is running
if ! docker ps > /dev/null 2>&1; then
    echo "ERROR: Couldn't connect to Docker daemon. Is it running?"
    echo ""

    # Detect OS and provide platform-specific instructions
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        echo "🪟 For Windows:"
        echo "  - Open Docker Desktop from Start Menu."
        echo "  - Wait until you see 'Docker Engine running' in the status bar."
        echo "  - Then retry: ./scripts/run_poc.sh"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "🐧 For Linux:"
        echo "  - Start the Docker service: sudo systemctl start docker"
        echo "  - Check if it’s running: sudo systemctl status docker"
        echo "  - It should say 'active (running)'."
        echo "  - If not, enable it to auto-start: sudo systemctl enable docker"
        echo "  - Then retry: ./scripts/run_poc.sh"
        echo ""
        echo "🧾 Optional (Fix permission issue):"
        echo "  - If you see 'permission denied while trying to connect to the Docker daemon socket', run:"
        echo "    sudo usermod -aG docker \$USER"
        echo "    newgrp docker"
        echo "  - Then re-run the command."
    else
        echo "Please ensure Docker is installed and running on your system."
        echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
    fi

    echo ""
    echo "🧪 Verify Docker is running with: docker ps"
    echo "If you get a list of containers (even empty), the daemon is running fine."
    exit 1
fi

# Run POC with docker-compose
cd infra
docker-compose up --build
