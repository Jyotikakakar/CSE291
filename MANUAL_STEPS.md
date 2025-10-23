# Manual Deployment Steps - Copy/Paste Ready

This document contains all commands ready to copy and paste. Follow in order.

---

## Part 1: EC2 Setup (First Time)

### 1. Launch EC2 Instance (AWS Console)

**Configuration:**
- Name: `meeting-summarizer-agent`
- AMI: Ubuntu Server 22.04 LTS
- Instance Type: `t2.medium`
- Key Pair: Create/Select and download `.pem` file
- Security Group:
  - SSH (22) from your IP
  - Custom TCP (5001-5004) from 0.0.0.0/0
- Storage: 20 GB

Click Launch → Wait for Running state → Note Public IP

---

### 2. Connect to EC2

**On your local machine:**

```bash
# Replace with your actual key file and EC2 IP
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

**You are now on EC2 instance for the remaining steps...**

---

### 3. Install Docker and Git

```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Verify Docker
docker --version

# Install Git
sudo apt install -y git
```

---

### 4. Clone Repository

```bash
# Clone the repository
git clone https://github.com/Jyotikakakar/CSE291.git

# Enter directory
cd CSE291

# Verify files
ls -la
```

---

### 5. Set API Key

```bash
# Set your Gemini API key (get from: https://makersuite.google.com/app/apikey)
export GEMINI_API_KEY="paste_your_actual_api_key_here"

# Verify it's set
echo $GEMINI_API_KEY
```

⚠️ **Important:** Replace `paste_your_actual_api_key_here` with your real API key!

---

### 6. Build Docker Image

```bash
# Build the image (takes 2-3 minutes)
docker build -t meeting-summarizer:latest .

# Verify image was created
docker images | grep meeting-summarizer
```

You should see `meeting-summarizer` with tag `latest`.

---

## Part 2: Start User Containers

Copy and paste each command one at a time:

### User 1 Container (Port 5001)

```bash
docker run -d \
  --name meeting-summarizer-user1 \
  -p 5001:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e GEMINI_MODEL="gemini-2.5-flash-live" \
  -e USER_ID="user_1" \
  -e PORT=5000 \
  --restart unless-stopped \
  meeting-summarizer:latest
```

### User 2 Container (Port 5002)

```bash
docker run -d \
  --name meeting-summarizer-user2 \
  -p 5002:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e GEMINI_MODEL="gemini-2.5-flash-live" \
  -e USER_ID="user_2" \
  -e PORT=5000 \
  --restart unless-stopped \
  meeting-summarizer:latest
```

### User 3 Container (Port 5003)

```bash
docker run -d \
  --name meeting-summarizer-user3 \
  -p 5003:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e GEMINI_MODEL="gemini-2.5-flash-live" \
  -e USER_ID="user_3" \
  -e PORT=5000 \
  --restart unless-stopped \
  meeting-summarizer:latest
```

### User 4 Container (Port 5004)

```bash
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

---

### Verify All Containers Running

```bash
# Check all containers are up
docker ps

# Should show 4 containers with names:
# - meeting-summarizer-user1 (0.0.0.0:5001->5000/tcp)
# - meeting-summarizer-user2 (0.0.0.0:5002->5000/tcp)
# - meeting-summarizer-user3 (0.0.0.0:5003->5000/tcp)
# - meeting-summarizer-user4 (0.0.0.0:5004->5000/tcp)
```

---

### Test Health Endpoints

```bash
# Test each container (should return JSON with "status":"healthy")
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health
curl http://localhost:5004/health
```

Each should return something like:
```json
{"status":"healthy","timestamp":"2025-10-23T...","user_id":"user_1"}
```

---

## Part 3: Load Data

Still on EC2 instance:

```bash
# Make sure you're in the CSE291 directory
cd ~/CSE291

# Run data loading script
python3 load_data.py
```

**When prompted:**
- Press `2` and Enter (for synthetic samples - quick)
- OR Press `1` and Enter (for real AMI dataset - slower)

**Verify data loaded:**

```bash
# Check transcript files
ls -l data/transcripts/

# Should show multiple .txt files
# Check metadata
cat data/metadata.json
```

---

## Part 4: Local Machine Evaluation

**On your LOCAL machine** (not EC2):

### 1. Install Dependencies

```bash
# Clone repo if not already
git clone https://github.com/Jyotikakakar/CSE291.git
cd CSE291

# Install Python packages
pip install -r requirements.txt
```

---

### 2. Copy Data from EC2

```bash
# Set your EC2 IP
export EC2_IP="YOUR_EC2_PUBLIC_IP"

# Copy data directory (replace with your key file)
scp -i your-key.pem -r ubuntu@$EC2_IP:~/CSE291/data ./

# Verify data copied
ls data/transcripts/
```

---

### 3. Test Single Container

```bash
# Test connection to user 1 container
python3 client.py http://$EC2_IP:5001
```

**Expected output:**
```
Testing connection to http://YOUR_EC2_IP:5001
✓ Health check passed: {...}
Creating session...
✓ Session created: user_1_...
Testing summarization...
✓ Summarization successful
  Latency: XXXms
  Decisions: X
  Action items: X
Getting session history...
✓ Total requests in session: 1
✓ All tests passed!
```

---

### 4. Run Full Multi-User Evaluation

```bash
# Run evaluation across all 4 user containers
# Note: URL pattern is http://EC2_IP:500 (without last digit)
python3 evaluate_api.py http://$EC2_IP:500
```

**This will:**
- Connect to all 4 user containers (ports 5001-5004)
- Create 2 sessions per user
- Process all transcripts
- Generate evaluation results

**Expected output:**
```
================================================================================
MEETING SUMMARIZER API EVALUATION
Multi-User, Multi-Session Benchmark
================================================================================

Loading transcripts...
✓ Loaded X transcripts

Assigning transcripts to users...
  user_1: X transcripts (avg XXX words)
  user_2: X transcripts (avg XXX words)
  user_3: X transcripts (avg XXX words)
  user_4: X transcripts (avg XXX words)

================================================================================
Evaluating user_1
================================================================================
...
✓ EVALUATION COMPLETE!
```

---

### 5. Review Results

```bash
# View JSON results
cat results/api_evaluation.json

# Open generated plots (on Mac)
open results/latency_vs_context.png
open results/success_rate_by_user.png
open results/latency_cdf_by_user.png

# Or view in file explorer
ls -l results/
```

**Files generated:**
- `api_evaluation.json` - Raw evaluation data
- `latency_vs_context.png` - Latency scaling plot
- `success_rate_by_user.png` - Success rate comparison
- `latency_cdf_by_user.png` - Performance distributions

---

## Part 5: Monitoring and Management

**On EC2 instance:**

### View Logs

```bash
# View logs for specific user
docker logs meeting-summarizer-user1

# Follow logs in real-time
docker logs -f meeting-summarizer-user1

# Last 50 lines
docker logs --tail 50 meeting-summarizer-user1
```

### Check Container Status

```bash
# List all running containers
docker ps

# Check specific container
docker ps -f name=meeting-summarizer-user1
```

### Restart Container

```bash
# Restart specific container
docker restart meeting-summarizer-user1

# Restart all
docker restart $(docker ps -q -f name=meeting-summarizer)
```

### Stop Containers

```bash
# Stop specific container
docker stop meeting-summarizer-user1

# Stop all
docker stop $(docker ps -q -f name=meeting-summarizer)
```

### Remove Containers

```bash
# Remove specific container (must be stopped first)
docker rm meeting-summarizer-user1

# Force remove (stops and removes)
docker rm -f meeting-summarizer-user1

# Remove all
docker rm -f $(docker ps -aq -f name=meeting-summarizer)
```

---

## Part 6: Update and Redeploy

If you make code changes:

```bash
# Pull latest changes
cd ~/CSE291
git pull

# Rebuild image
docker build -t meeting-summarizer:latest .

# Stop and remove old containers
docker rm -f $(docker ps -aq -f name=meeting-summarizer)

# Restart containers (copy commands from Part 2)
# ... user1 docker run command ...
# ... user2 docker run command ...
# ... user3 docker run command ...
# ... user4 docker run command ...
```

---

## Quick Reference: All Containers at Once

### Start All (copy entire block)

```bash
docker run -d --name meeting-summarizer-user1 -p 5001:5000 -e GEMINI_API_KEY="$GEMINI_API_KEY" -e USER_ID="user_1" --restart unless-stopped meeting-summarizer:latest && \
docker run -d --name meeting-summarizer-user2 -p 5002:5000 -e GEMINI_API_KEY="$GEMINI_API_KEY" -e USER_ID="user_2" --restart unless-stopped meeting-summarizer:latest && \
docker run -d --name meeting-summarizer-user3 -p 5003:5000 -e GEMINI_API_KEY="$GEMINI_API_KEY" -e USER_ID="user_3" --restart unless-stopped meeting-summarizer:latest && \
docker run -d --name meeting-summarizer-user4 -p 5004:5000 -e GEMINI_API_KEY="$GEMINI_API_KEY" -e USER_ID="user_4" --restart unless-stopped meeting-summarizer:latest
```

### Stop All

```bash
docker stop $(docker ps -q -f name=meeting-summarizer)
```

### Remove All

```bash
docker rm -f $(docker ps -aq -f name=meeting-summarizer)
```

### Check All Health

```bash
for port in 5001 5002 5003 5004; do echo "Port $port:"; curl -s http://localhost:$port/health | python3 -m json.tool; echo ""; done
```

---

## Troubleshooting Commands

### Container won't start

```bash
# Check logs for errors
docker logs meeting-summarizer-user1

# Check if port is in use
sudo netstat -tulpn | grep 5001

# Verify API key is set
echo $GEMINI_API_KEY
```

### Can't connect from local machine

```bash
# On EC2, test locally first
curl http://localhost:5001/health

# Check if containers are running
docker ps

# Check EC2 firewall
sudo ufw status

# Test from EC2 to itself
curl http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5001/health
```

### API returns errors

```bash
# Test Gemini API directly
docker exec meeting-summarizer-user1 python3 -c "
import os
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash-live')
print(model.generate_content('Hello').text)
"
```

---

## Complete Cleanup

When completely done with the project:

```bash
# Stop and remove all containers
docker rm -f $(docker ps -aq -f name=meeting-summarizer)

# Remove image (optional)
docker rmi meeting-summarizer:latest

# Remove data (optional)
rm -rf ~/CSE291

# Then terminate EC2 instance via AWS Console
```

---

## Cost Management

### Stop Instance (Keep for Later)

In AWS Console:
- Select instance
- Instance State → Stop
- Costs: Only storage (~$2/month)

### Terminate Instance (Done Forever)

In AWS Console:
- Select instance
- Instance State → Terminate
- Costs: $0 (everything deleted)

---

**End of Manual Steps**

For detailed explanations, see `DEPLOYMENT.md`
For quick reference, see `QUICKSTART_EC2.md`
For troubleshooting, see `DEPLOYMENT.md` Section "Troubleshooting"

