#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed. Please install docker-compose first.${NC}"
    exit 1
fi

# Check if NVIDIA Docker runtime is available
if ! docker info | grep -q "Runtimes:.*nvidia"; then
    echo -e "${YELLOW}Warning: NVIDIA Docker runtime not detected. GPU acceleration may not work.${NC}"
    echo -e "${YELLOW}Please ensure you have installed the NVIDIA Container Toolkit:${NC}"
    echo -e "${YELLOW}https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html${NC}"
    
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Parse command line arguments
BUILD=false
DETACH=false
LOGS=false
STOP=false
RESTART=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD=true
            shift
            ;;
        --detach|-d)
            DETACH=true
            shift
            ;;
        --logs|-l)
            LOGS=true
            shift
            ;;
        --stop)
            STOP=true
            shift
            ;;
        --restart)
            RESTART=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --build    Build the Docker image before starting"
            echo "  --detach   Run in detached mode"
            echo "  --logs     Follow the logs after starting"
            echo "  --stop     Stop the running container"
            echo "  --restart  Restart the container"
            echo "  --help     Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help to see available options"
            exit 1
            ;;
    esac
done

# Stop the container if requested
if [ "$STOP" = true ]; then
    echo -e "${YELLOW}Stopping TTS-v3 container...${NC}"
    docker-compose down
    echo -e "${GREEN}Container stopped.${NC}"
    exit 0
fi

# Restart the container if requested
if [ "$RESTART" = true ]; then
    echo -e "${YELLOW}Restarting TTS-v3 container...${NC}"
    docker-compose restart
    echo -e "${GREEN}Container restarted.${NC}"
    
    if [ "$LOGS" = true ]; then
        echo -e "${YELLOW}Following logs...${NC}"
        docker-compose logs -f
    fi
    
    exit 0
fi

# Build the image if requested
if [ "$BUILD" = true ]; then
    echo -e "${YELLOW}Building TTS-v3 Docker image...${NC}"
    docker-compose build
    echo -e "${GREEN}Build completed.${NC}"
fi

# Start the container
echo -e "${YELLOW}Starting TTS-v3 container...${NC}"

if [ "$DETACH" = true ]; then
    docker-compose up -d
    echo -e "${GREEN}Container started in detached mode.${NC}"
    echo -e "${GREEN}Access the application at http://localhost:5000${NC}"
else
    if [ "$LOGS" = true ]; then
        docker-compose up
    else
        docker-compose up -d
        echo -e "${GREEN}Container started in detached mode.${NC}"
        echo -e "${GREEN}Access the application at http://localhost:5000${NC}"
    fi
fi

# Follow logs if requested and in detached mode
if [ "$DETACH" = true ] && [ "$LOGS" = true ]; then
    echo -e "${YELLOW}Following logs...${NC}"
    docker-compose logs -f
fi