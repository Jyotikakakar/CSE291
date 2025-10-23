# Quick Start - EC2 Deployment (5 Minutes)

This is a condensed version of [DEPLOYMENT.md](DEPLOYMENT.md) for quick reference.

## Prerequisites

- EC2 instance running Ubuntu 22.04
- SSH access to instance
- Gemini API key

## Setup Commands (On EC2)

```bash
# 1. Install Docker
sudo apt update && sudo apt install -y docker.io git
sudo systemctl start docker
sudo usermod -aG docker ubuntu
newgrp docker

# 2. Clone and setup
git clone https://github.com/Jyotikakakar/CSE291.git
cd CSE291

# 3. Set API key
export GEMINI_API_KEY="your_api_key_here"

# 4. Build image
docker build -t meeting-summarizer:latest .

# 5. Start containers (4 users)
docker run -d --name meeting-summarizer-user1 -p 5001:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e USER_ID="user_1" -e PORT=5000 \
  --restart unless-stopped meeting-summarizer:latest

docker run -d --name meeting-summarizer-user2 -p 5002:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e USER_ID="user_2" -e PORT=5000 \
  --restart unless-stopped meeting-summarizer:latest

docker run -d --name meeting-summarizer-user3 -p 5003:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e USER_ID="user_3" -e PORT=5000 \
  --restart unless-stopped meeting-summarizer:latest

docker run -d --name meeting-summarizer-user4 -p 5004:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e USER_ID="user_4" -e PORT=5000 \
  --restart unless-stopped meeting-summarizer:latest

# 6. Verify
docker ps
curl http://localhost:5001/health
```

## Load Data (On EC2)

```bash
# Load sample transcripts
python3 load_data.py
# Choose option 2 (synthetic samples)
```

## Run Evaluation (On Local Machine)

```bash
# Clone repo locally
git clone https://github.com/Jyotikakakar/CSE291.git
cd CSE291

# Install dependencies
pip install -r requirements.txt

# Copy data from EC2
export EC2_IP="your_ec2_public_ip"
scp -i your-key.pem -r ubuntu@$EC2_IP:~/CSE291/data ./

# Test single container
python3 client.py http://$EC2_IP:5001

# Run full evaluation (all 4 users)
python3 evaluate_api.py http://$EC2_IP:500
```

## EC2 Security Group

Allow inbound traffic:
- Port 22 (SSH) from your IP
- Ports 5001-5004 (API) from your IP or 0.0.0.0/0

## Common Commands

```bash
# Check status
docker ps

# View logs
docker logs meeting-summarizer-user1

# Restart container
docker restart meeting-summarizer-user1

# Stop all
docker stop $(docker ps -q -f name=meeting-summarizer)

# Remove all
docker rm -f $(docker ps -aq -f name=meeting-summarizer)
```

## Architecture

```
User 1 Container (Port 5001)
  ├── Session 1
  └── Session 2

User 2 Container (Port 5002)
  ├── Session 1
  └── Session 2

User 3 Container (Port 5003)
  ├── Session 1
  └── Session 2

User 4 Container (Port 5004)
  ├── Session 1
  └── Session 2
```

- **Same user, different sessions**: Same container
- **Different users**: Separate containers

## API Examples

```bash
# Health check
curl http://localhost:5001/health

# Create session
curl -X POST http://localhost:5001/api/session/create \
  -H "Content-Type: application/json" \
  -d '{"metadata": {"test": true}}'

# Summarize transcript
curl -X POST http://localhost:5001/api/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "transcript": "Alice: Lets plan Q4. Bob: I think mobile app is priority.",
    "session_id": "user_1_1234567890"
  }'

# Get session history
curl http://localhost:5001/api/session/user_1_1234567890/history

# List all sessions
curl http://localhost:5001/api/sessions

# Get metrics
curl http://localhost:5001/api/metrics
```

## Troubleshooting

**Container won't start**:
```bash
docker logs meeting-summarizer-user1
# Check GEMINI_API_KEY is set
```

**Can't connect from local**:
```bash
# On EC2, test locally first
curl http://localhost:5001/health

# Check security group allows ports 5001-5004
# Check EC2 firewall: sudo ufw status
```

**API errors**:
```bash
# Verify Gemini API key works
docker exec meeting-summarizer-user1 python3 -c "
import os
import google.generativeai as genai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash-live')
print(model.generate_content('test').text)
"
```

## Cost Estimate

- EC2 t2.medium: ~$35/month (or ~$10/month spot)
- Gemini API: Free tier (15 req/min)
- **Total: $10-35/month**

## Next Steps

After baseline evaluation, Phase 2 will add:
- Context management (vector database)
- Long-term memory
- Cross-session learning
- Advanced evaluation comparing with/without memory

---

For detailed documentation, see [DEPLOYMENT.md](DEPLOYMENT.md)

