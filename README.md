# Meeting Summarizer Agent

A Python application that uses Google's Gemini AI to analyze meeting transcripts and extract key information like decisions, action items, and risks. This is a Phase 1 implementation focused on meeting summarization.

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker and Docker Compose installed
- Google Gemini API key

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

