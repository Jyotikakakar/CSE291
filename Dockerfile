# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/transcripts results

# Set environment variables
ENV PYTHONPATH=/app
ENV OLLAMA_HOST=http://ollama:11434
ENV OLLAMA_MODEL=llama3.1:8b

# Expose port (if needed for web interface in future)
EXPOSE 8000

# Default command
CMD ["python", "run.py"]
