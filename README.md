# Meeting Summarizer Agent

A Python application that uses Google's Gemini AI to analyze meeting transcripts and extract key information like decisions, action items, and risks. 

**Phase 1**: Baseline agent with user and session management, deployed on EC2 with Docker for evaluation.

## Features

- ✅ Meeting transcript summarization using Gemini AI
- ✅ Extracts decisions, action items, risks, and key points
- ✅ **Google Calendar integration** - Create and manage meeting events
- ✅ **Google Tasks integration** - Create and track action items
- ✅ Multi-user support with isolated containers
- ✅ Session management within user contexts
- ✅ REST API for programmatic access
- ✅ EC2 deployment ready
- ✅ Evaluation framework with visualization

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker and Docker Compose installed
- Google Gemini API key
- (Optional) Google OAuth credentials for Calendar/Tasks integration

### Quick Test

Test the integration locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set Gemini API key
export GEMINI_API_KEY="your_key_here"

# Run test suite
python test_tools.py

# Or test the agent directly
python agent.py
```

### Get Your API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the API key for the next step

### Run with Docker Compose

```bash
# Clone and navigate to the project
git clone https://github.com/Jyotikakakar/CSE291.git
cd CSE291

# Set your Gemini API key
export GEMINI_API_KEY="your-api-key-here"

# Start the application
docker-compose up

# The application will:
# 1. Connect to Gemini API
# 2. Load meeting transcripts
# 3. Run the meeting summarizer evaluation
```

### Manual Setup (Alternative)

### Step 1: Get Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the API key

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Set Environment Variable

```bash
# Set your API key
export GEMINI_API_KEY="your-api-key-here"

# Or create a .env file
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

### Step 4: Run Everything!

```bash
python3 run.py
```

## Docker Commands

```bash
# Build and run with Docker Compose
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up --build

# Clean up (removes volumes)
docker-compose down -v
```

## Configuration

### Environment Variables
- `GEMINI_API_KEY`: Your Google Gemini API key (required)
- `GOOGLE_CREDENTIALS_PATH`: Path to Google OAuth credentials JSON (optional, for Calendar/Tasks)
- `GOOGLE_TOKEN_PATH`: Path to store Google OAuth token (optional)

### Setting up API Key

**Option 1: Environment Variable**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

**Option 2: .env File**
```bash
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

**Option 3: Docker Compose**
```bash
GEMINI_API_KEY="your-api-key-here" docker-compose up
```

## Results

The application generates:
- `results/evaluation.json`: Detailed evaluation results
- `results/latency_cdf.png`: Latency distribution chart
- `results/extraction_counts.png`: Items extracted per meeting
- `results/success_rate.png`: Success vs failure rate

## EC2 Deployment

For deploying on AWS EC2 with Docker and multi-user support, see:

**📖 [DEPLOYMENT.md](DEPLOYMENT.md)** - Complete manual deployment guide

Quick overview:
- Deploy on EC2 with Docker (no IAM roles needed)
- Each user gets isolated container (ports 5001-5004)
- Multiple sessions per user in same container
- REST API for evaluation
- Manual steps provided (no scripts required)

### Local API Testing

```bash
# Install dependencies
pip install -r requirements.txt

# Test API connection (replace with your EC2 IP)
python3 client.py http://your-ec2-ip:5001

# Run multi-user evaluation
python3 evaluate_api.py http://your-ec2-ip:500
```

### API Endpoints

**Main Endpoint (Simple API):**
- `POST /analyze` - Analyze transcript (auto-creates session from transcript content)
  - Input: `{"transcript": "..."}`
  - Returns: Summary, session info, tasks, and calendar events
  - Session is automatically created with a meaningful name derived from transcript

**Health & Metrics:**
- `GET /health` - Health check
- `GET /api/metrics` - Get agent metrics

**Session Management (Advanced):**
- `GET /api/sessions` - List all sessions
- `GET /api/session/<id>` - Get session details
- `GET /api/session/<id>/history` - Get session history
- `POST /api/session/create` - Create new session manually (optional)

## Project Structure

```
CSE291/
├── agent.py              # Core meeting summarizer agent
├── api.py                # Flask REST API with user/session mgmt
├── client.py             # API client for testing
├── evaluate.py           # Local evaluation script
├── evaluate_api.py       # Multi-user API evaluation
├── load_data.py          # Data loading utilities
├── run.py                # Local execution script
├── Dockerfile            # Container configuration
├── docker-compose.yml    # Local Docker setup
├── manage_containers.sh  # Container management helper
├── requirements.txt      # Python dependencies
├── DEPLOYMENT.md         # EC2 deployment guide
├── data/                 # Meeting transcripts
└── results/              # Evaluation results
```

