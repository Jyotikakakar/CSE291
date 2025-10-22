# Meeting Summarizer Agent

A Python application that uses Ollama (local LLM) to analyze meeting transcripts and extract key information like decisions, action items, and risks.

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker and Docker Compose installed
- At least 8GB RAM available for the LLM model

### Run with Docker Compose

```bash
# Clone and navigate to the project
git clone <repository-url>
cd CSE291

# Start the application (this will automatically download the LLM model)
docker-compose up

# The application will:
# 1. Start Ollama service
# 2. Download the llama3.1:8b model (~4.7GB)
# 3. Run the meeting summarizer evaluation
```

### Manual Setup (Alternative)

### Step 1: Install Ollama
```bash
curl -L https://ollama.com/download/Ollama-darwin.zip -o Ollama.zip
unzip Ollama.zip
mv Ollama.app /Applications/
rm Ollama.zip

echo 'export PATH="/Applications/Ollama.app/Contents/Resources:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Step 2: Start Ollama & Pull Model

```bash
# Start Ollama (keeps running in background)
ollama serve &

# Pull the AI model (4.7GB download, one-time)
ollama pull llama3.1:8b

# Test it works
ollama run llama3.1:8b "Hello!"
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
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

Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

Environment variables:
- `OLLAMA_HOST`: Ollama service URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: LLM model to use (default: llama3.1:8b)

## Results

The application generates:
- `results/evaluation.json`: Detailed evaluation results
- `results/latency_cdf.png`: Latency distribution chart
- `results/extraction_counts.png`: Items extracted per meeting
- `results/success_rate.png`: Success vs failure rate

