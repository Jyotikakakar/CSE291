# EC2 Deployment Guide - Meeting Summarizer Agent

This guide provides **manual steps** to deploy the Meeting Summarizer Agent on AWS EC2 with Docker, implementing user and session management.

## Architecture Overview

- **User Isolation**: Each user gets a separate Docker container
- **Session Management**: Multiple sessions per user run in the same container
- **Port Mapping**: Each user container runs on a different port (5001, 5002, 5003, 5004)
- **No IAM Required**: Uses simple Docker-based deployment

```
┌─────────────────────────────────────────────┐
│         EC2 Instance (Ubuntu)               │
│                                             │
│  ┌──────────────┐  ┌──────────────┐        │
│  │ User 1       │  │ User 2       │        │
│  │ Container    │  │ Container    │  ...   │
│  │ Port: 5001   │  │ Port: 5002   │        │
│  │              │  │              │        │
│  │ Session 1    │  │ Session 1    │        │
│  │ Session 2    │  │ Session 2    │        │
│  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────┘
```

## Prerequisites

1. AWS Account with EC2 access
2. Google Gemini API Key ([Get it here](https://makersuite.google.com/app/apikey))
3. SSH client

---

## Phase 1: EC2 Instance Setup

### Step 1.1: Launch EC2 Instance

1. Log into AWS Console → EC2 Dashboard
2. Click **"Launch Instance"**
3. Configure:
   - **Name**: `meeting-summarizer-agent`
   - **OS**: Ubuntu Server 22.04 LTS (64-bit x86)
   - **Instance type**: `t2.medium` (minimum) or `t2.large` (recommended)
     - 2-4 vCPUs needed for multiple containers
     - 4-8 GB RAM
   - **Key pair**: Create new or select existing
     - Download `.pem` file if new
   - **Network settings**:
     - ✓ Allow SSH traffic (port 22) from your IP
     - ✓ Allow HTTP traffic (port 80)
     - Add Custom TCP Rules:
       - Port range: `5001-5010` (for user containers)
       - Source: `0.0.0.0/0` or your IP
   - **Storage**: 20 GB minimum

4. Click **"Launch Instance"**
5. Wait for instance to be in **"Running"** state
6. Note the **Public IPv4 address** (e.g., `54.123.45.67`)

### Step 1.2: Connect to Instance

```bash
# Set permissions on your key file
chmod 400 your-key.pem

# Connect via SSH
ssh -i your-key.pem ubuntu@54.123.45.67
```

---

## Phase 2: Install Dependencies

### Step 2.1: Update System

```bash
sudo apt update
sudo apt upgrade -y
```

### Step 2.2: Install Docker

```bash
# Install Docker
sudo apt install -y docker.io

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (avoid sudo)
sudo usermod -aG docker ubuntu

# Apply group changes
newgrp docker

# Verify Docker
docker --version
# Should output: Docker version 24.x.x
```

### Step 2.3: Install Docker Compose (Optional but helpful)

```bash
sudo apt install -y docker-compose

# Verify
docker-compose --version
```

### Step 2.4: Install Git

```bash
sudo apt install -y git

git --version
```

---

## Phase 3: Deploy Application

### Step 3.1: Clone Repository

```bash
# Clone your repository
git clone https://github.com/Jyotikakakar/CSE291.git
cd CSE291
```

### Step 3.2: Configure Environment

```bash
# Create .env file with your Gemini API key
nano .env
```

Add the following content (replace with your actual API key):

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash-live
```

Save with `Ctrl+X`, then `Y`, then `Enter`.

### Step 3.3: Build Docker Image

```bash
# Build the image (takes 2-3 minutes)
docker build -t meeting-summarizer:latest .

# Verify image was built
docker images | grep meeting-summarizer
```

---

## Phase 4: Deploy Multi-User Containers

### Step 4.1: Create User Containers

Run separate containers for each user on different ports:

```bash
# User 1 - Port 5001
docker run -d \
  --name meeting-summarizer-user1 \
  -p 5001:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e GEMINI_MODEL="gemini-2.5-flash-live" \
  -e USER_ID="user_1" \
  -e PORT=5000 \
  --restart unless-stopped \
  meeting-summarizer:latest

# User 2 - Port 5002
docker run -d \
  --name meeting-summarizer-user2 \
  -p 5002:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e GEMINI_MODEL="gemini-2.5-flash-live" \
  -e USER_ID="user_2" \
  -e PORT=5000 \
  --restart unless-stopped \
  meeting-summarizer:latest

# User 3 - Port 5003
docker run -d \
  --name meeting-summarizer-user3 \
  -p 5003:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e GEMINI_MODEL="gemini-2.5-flash-live" \
  -e USER_ID="user_3" \
  -e PORT=5000 \
  --restart unless-stopped \
  meeting-summarizer:latest

# User 4 - Port 5004
docker run -d \
  --name meeting-summarizer-user4 \
  -p 5004:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e GEMINI_MODEL="gemini-2.5-flash-live" \
  -e USER_ID="user_4" \
  -e PORT=5000 \
  --restart unless-stopped \
  meeting-summarizer:latest
```

### Step 4.2: Verify Containers are Running

```bash
# Check all containers
docker ps

# Should show 4 running containers
# NAME                          STATUS    PORTS
# meeting-summarizer-user1      Up        0.0.0.0:5001->5000/tcp
# meeting-summarizer-user2      Up        0.0.0.0:5002->5000/tcp
# meeting-summarizer-user3      Up        0.0.0.0:5003->5000/tcp
# meeting-summarizer-user4      Up        0.0.0.0:5004->5000/tcp
```

### Step 4.3: Test Health Endpoints

```bash
# Test each container
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health
curl http://localhost:5004/health

# Should return JSON like:
# {"status":"healthy","timestamp":"...","user_id":"user_1"}
```

---

## Phase 5: Load Data for Evaluation

### Step 5.1: Generate Sample Transcripts

```bash
# Run data loading script
python3 load_data.py
```

When prompted:
- Choose option `2` (create synthetic samples) for quick setup
- Or option `1` for real AMI dataset (requires HuggingFace access)

This creates:
- `data/transcripts/sample_001.txt` through `sample_005.txt`
- `data/metadata.json`

---

## Phase 6: Run Evaluation

### Step 6.1: From Your Local Machine

On your **local machine** (not EC2), install dependencies:

```bash
# Clone repo if not already
git clone https://github.com/Jyotikakakar/CSE291.git
cd CSE291

# Install Python dependencies
pip install -r requirements.txt
```

### Step 6.2: Test Single Container

```bash
# Replace with your EC2 public IP
export EC2_IP="54.123.45.67"

# Test client connection
python3 client.py http://$EC2_IP:5001

# Should output:
# ✓ Health check passed
# ✓ Session created
# ✓ Summarization successful
# ✓ All tests passed!
```

### Step 6.3: Run Full Multi-User Evaluation

```bash
# Copy data directory to local if needed
scp -i your-key.pem -r ubuntu@$EC2_IP:~/CSE291/data ./

# Run evaluation (connects to all 4 user containers)
python3 evaluate_api.py http://$EC2_IP:500

# This will:
# - Connect to user_1 on port 5001
# - Connect to user_2 on port 5002
# - Connect to user_3 on port 5003
# - Connect to user_4 on port 5004
# - Create multiple sessions per user
# - Process transcripts with varying context lengths
# - Generate evaluation plots
```

---

## Phase 7: Monitor and Manage

### Check Container Logs

```bash
# View logs for a specific user
docker logs meeting-summarizer-user1

# Follow logs in real-time
docker logs -f meeting-summarizer-user1

# Last 50 lines
docker logs --tail 50 meeting-summarizer-user1
```

### Restart Container

```bash
# Restart specific container
docker restart meeting-summarizer-user1

# Restart all containers
docker restart $(docker ps -q -f name=meeting-summarizer)
```

### Stop Containers

```bash
# Stop specific container
docker stop meeting-summarizer-user1

# Stop all containers
docker stop $(docker ps -q -f name=meeting-summarizer)
```

### Remove Containers

```bash
# Remove specific container
docker rm -f meeting-summarizer-user1

# Remove all meeting-summarizer containers
docker rm -f $(docker ps -aq -f name=meeting-summarizer)
```

### Update Code

```bash
# Pull latest changes
cd ~/CSE291
git pull

# Rebuild image
docker build -t meeting-summarizer:latest .

# Restart containers (they will use new image)
docker stop $(docker ps -q -f name=meeting-summarizer)
docker rm $(docker ps -aq -f name=meeting-summarizer)

# Re-run the docker run commands from Step 4.1
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs meeting-summarizer-user1

# Common issues:
# - GEMINI_API_KEY not set: Check .env file
# - Port already in use: Change port mapping
# - Out of memory: Upgrade instance type
```

### Can't Connect from Local Machine

```bash
# Check EC2 security group allows ports 5001-5004
# Check container is running: docker ps
# Check firewall on EC2: sudo ufw status
# Try from EC2 instance: curl http://localhost:5001/health
```

### API Returns Errors

```bash
# Check Gemini API key is valid
# Check logs: docker logs meeting-summarizer-user1
# Test Gemini directly:
docker exec meeting-summarizer-user1 python3 -c "
import os
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash-live')
print(model.generate_content('Hello').text)
"
```

---

## Architecture Justification

### Why This Agent?

**Meeting Summarizer Agent** is chosen because:

1. **Context Length Variance**: Meeting transcripts range from 100-5000+ words
   - Short daily standups (~200 words)
   - Regular meetings (~500-1000 words)
   - Long planning sessions (~2000-5000 words)

2. **Memory Requirements**: Extracting structured information requires:
   - Understanding who said what (speaker context)
   - Tracking decisions across conversation flow
   - Linking action items to owners mentioned earlier
   - Identifying implicit risks from past statements

3. **Multi-Session Scenarios**: Real-world usage patterns:
   - Same user processes multiple meetings (sessions)
   - Need to track performance across sessions
   - Potential for cross-meeting context (future phase)

4. **Baseline Without Memory Management**: Current implementation:
   - No conversation history retention
   - Each request is independent (stateless)
   - No cross-session learning
   - Perfect for baseline evaluation before adding memory

### User/Session Setup

**4 User Types** with different context patterns:

1. **User 1**: Short context (200-400 words)
   - Quick daily standups
   - Brief check-ins
   - Tests low-context performance

2. **User 2**: Medium context (400-800 words)
   - Regular team meetings
   - Sprint planning
   - Tests typical workload

3. **User 3**: Long context (800-2000+ words)
   - Quarterly planning
   - Design reviews
   - Tests high-context handling

4. **User 4**: Mixed context
   - Varied meeting types
   - Tests adaptability

**Sessions per User**: Each user has 2+ sessions to test:
- Session isolation
- Performance consistency
- Container resource sharing

### Benchmark

**AMI Dataset** (optional) or **Synthetic Transcripts**:
- Real meeting conversations
- Natural language with context dependencies
- Varying lengths and complexity
- Structured outputs (decisions, actions, risks)

**Evaluation Metrics**:
1. **Latency**: Processing time vs context length
2. **Success Rate**: Valid JSON extraction rate
3. **Extraction Quality**: Number of decisions/actions/risks found
4. **User Isolation**: Performance doesn't degrade across users
5. **Session Independence**: Each session performs consistently

---

## Next Steps (Phase 2)

This baseline deployment will be enhanced with:

1. **Context Management**: 
   - Store conversation history per session
   - Use vector database (ChromaDB/Pinecone)
   
2. **Memory Management**:
   - Long-term user preferences
   - Cross-session learning
   - Meeting templates based on history

3. **Advanced Evaluation**:
   - Compare with/without context management
   - Measure accuracy improvements
   - Evaluate memory retrieval effectiveness

---

## Cost Estimation

**EC2 t2.medium** (2 vCPU, 4GB RAM):
- On-demand: ~$0.047/hour (~$35/month)
- Spot instance: ~$0.014/hour (~$10/month)

**Gemini API**:
- Free tier: 15 requests/minute
- Flash model: Very low cost per request

**Total estimated cost**: $10-35/month for baseline evaluation

---

## Security Notes

1. **API Key**: Stored in environment variables, not in code
2. **Port Access**: Restrict to your IP in security group
3. **SSH Access**: Use key-based authentication only
4. **Container Isolation**: Each user has separate container
5. **No Persistent Data**: Containers are stateless (for baseline)

---

## Summary of Manual Steps

1. ✓ Launch EC2 instance (Ubuntu t2.medium)
2. ✓ Install Docker + dependencies
3. ✓ Clone repository
4. ✓ Configure Gemini API key
5. ✓ Build Docker image
6. ✓ Run 4 user containers (ports 5001-5004)
7. ✓ Load evaluation data
8. ✓ Run multi-user evaluation from local machine
9. ✓ Monitor and analyze results

**No IAM roles needed** - simple Docker deployment!
**No deployment scripts** - all manual commands provided!

