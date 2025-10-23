#!/bin/bash
# Helper script to manage user containers on EC2
# This provides convenient commands but all can be done manually

set -e

GEMINI_API_KEY="${GEMINI_API_KEY:-}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash-live}"
IMAGE_NAME="meeting-summarizer:latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_usage() {
    echo "Usage: $0 {start|stop|restart|status|logs|clean}"
    echo ""
    echo "Commands:"
    echo "  start    - Start all user containers"
    echo "  stop     - Stop all user containers"
    echo "  restart  - Restart all user containers"
    echo "  status   - Show status of all containers"
    echo "  logs     - Show logs from all containers"
    echo "  clean    - Stop and remove all containers"
    echo ""
    echo "Environment variables:"
    echo "  GEMINI_API_KEY  - Your Gemini API key (required)"
    echo "  GEMINI_MODEL    - Gemini model to use (default: gemini-2.5-flash-live)"
}

function check_api_key() {
    if [ -z "$GEMINI_API_KEY" ]; then
        echo -e "${RED}Error: GEMINI_API_KEY environment variable not set${NC}"
        echo "Set it with: export GEMINI_API_KEY='your-key-here'"
        exit 1
    fi
}

function start_containers() {
    check_api_key
    
    echo -e "${GREEN}Starting user containers...${NC}"
    
    # User 1
    echo "Starting user_1 on port 5001..."
    docker run -d \
        --name meeting-summarizer-user1 \
        -p 5001:5000 \
        -e GEMINI_API_KEY="$GEMINI_API_KEY" \
        -e GEMINI_MODEL="$GEMINI_MODEL" \
        -e USER_ID="user_1" \
        -e PORT=5000 \
        --restart unless-stopped \
        $IMAGE_NAME
    
    # User 2
    echo "Starting user_2 on port 5002..."
    docker run -d \
        --name meeting-summarizer-user2 \
        -p 5002:5000 \
        -e GEMINI_API_KEY="$GEMINI_API_KEY" \
        -e GEMINI_MODEL="$GEMINI_MODEL" \
        -e USER_ID="user_2" \
        -e PORT=5000 \
        --restart unless-stopped \
        $IMAGE_NAME
    
    # User 3
    echo "Starting user_3 on port 5003..."
    docker run -d \
        --name meeting-summarizer-user3 \
        -p 5003:5000 \
        -e GEMINI_API_KEY="$GEMINI_API_KEY" \
        -e GEMINI_MODEL="$GEMINI_MODEL" \
        -e USER_ID="user_3" \
        -e PORT=5000 \
        --restart unless-stopped \
        $IMAGE_NAME
    
    # User 4
    echo "Starting user_4 on port 5004..."
    docker run -d \
        --name meeting-summarizer-user4 \
        -p 5004:5000 \
        -e GEMINI_API_KEY="$GEMINI_API_KEY" \
        -e GEMINI_MODEL="$GEMINI_MODEL" \
        -e USER_ID="user_4" \
        -e PORT=5000 \
        --restart unless-stopped \
        $IMAGE_NAME
    
    echo -e "${GREEN}✓ All containers started${NC}"
    echo ""
    sleep 2
    show_status
}

function stop_containers() {
    echo -e "${YELLOW}Stopping all containers...${NC}"
    docker stop $(docker ps -q -f name=meeting-summarizer) 2>/dev/null || echo "No running containers"
    echo -e "${GREEN}✓ Containers stopped${NC}"
}

function restart_containers() {
    echo -e "${YELLOW}Restarting all containers...${NC}"
    docker restart $(docker ps -q -f name=meeting-summarizer) 2>/dev/null || echo "No containers to restart"
    echo -e "${GREEN}✓ Containers restarted${NC}"
}

function show_status() {
    echo -e "${GREEN}Container Status:${NC}"
    docker ps -f name=meeting-summarizer --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo -e "${GREEN}Health Check:${NC}"
    for port in 5001 5002 5003 5004; do
        response=$(curl -s http://localhost:$port/health 2>/dev/null || echo "failed")
        if [[ $response == *"healthy"* ]]; then
            echo -e "Port $port: ${GREEN}✓ Healthy${NC}"
        else
            echo -e "Port $port: ${RED}✗ Not responding${NC}"
        fi
    done
}

function show_logs() {
    echo -e "${GREEN}Recent logs from all containers:${NC}"
    echo ""
    for container in meeting-summarizer-user1 meeting-summarizer-user2 meeting-summarizer-user3 meeting-summarizer-user4; do
        if docker ps -a -f name=$container | grep -q $container; then
            echo -e "${YELLOW}=== $container ===${NC}"
            docker logs --tail 10 $container 2>&1
            echo ""
        fi
    done
}

function clean_containers() {
    echo -e "${YELLOW}Stopping and removing all containers...${NC}"
    docker rm -f $(docker ps -aq -f name=meeting-summarizer) 2>/dev/null || echo "No containers to remove"
    echo -e "${GREEN}✓ All containers cleaned up${NC}"
}

# Main script
case "${1:-}" in
    start)
        start_containers
        ;;
    stop)
        stop_containers
        ;;
    restart)
        restart_containers
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    clean)
        clean_containers
        ;;
    *)
        print_usage
        exit 1
        ;;
esac

