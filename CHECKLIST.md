# Deployment Checklist

Use this checklist to track your deployment progress.

## Pre-Deployment

### Prerequisites
- [ ] AWS account with EC2 access
- [ ] SSH key pair created/downloaded
- [ ] Google Gemini API key obtained ([Get it here](https://makersuite.google.com/app/apikey))
- [ ] Git repository accessible

### Local Setup (Optional - for testing)
- [ ] Docker installed locally
- [ ] Python 3.11+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Local test successful: `docker build -t meeting-summarizer:latest .`

---

## EC2 Setup

### Step 1: Launch Instance
- [ ] Launch EC2 instance
  - [ ] Ubuntu Server 22.04 LTS selected
  - [ ] Instance type: t2.medium or t2.large
  - [ ] Key pair selected/created
  - [ ] Security group configured:
    - [ ] Port 22 (SSH) allowed from your IP
    - [ ] Ports 5001-5004 allowed from 0.0.0.0/0 (or your IP)
  - [ ] 20 GB storage allocated
- [ ] Instance state: Running
- [ ] Public IP noted: `________________`

### Step 2: Connect to Instance
- [ ] Key file permissions set: `chmod 400 your-key.pem`
- [ ] SSH connection successful: `ssh -i your-key.pem ubuntu@<IP>`
- [ ] Connected as ubuntu user

### Step 3: Install Dependencies
- [ ] System updated: `sudo apt update && sudo apt upgrade -y`
- [ ] Docker installed: `sudo apt install -y docker.io`
- [ ] Docker started: `sudo systemctl start docker`
- [ ] Docker enabled: `sudo systemctl enable docker`
- [ ] User added to docker group: `sudo usermod -aG docker ubuntu`
- [ ] Group applied: `newgrp docker`
- [ ] Docker verified: `docker --version`
- [ ] Git installed: `sudo apt install -y git`

---

## Application Deployment

### Step 4: Clone and Configure
- [ ] Repository cloned: `git clone https://github.com/Jyotikakakar/CSE291.git`
- [ ] Directory entered: `cd CSE291`
- [ ] API key set: `export GEMINI_API_KEY="your_key"`
- [ ] API key verified: `echo $GEMINI_API_KEY`

### Step 5: Build Image
- [ ] Image built: `docker build -t meeting-summarizer:latest .`
- [ ] Build completed without errors
- [ ] Image verified: `docker images | grep meeting-summarizer`

### Step 6: Start Containers
- [ ] User 1 container started (port 5001)
  ```bash
  docker run -d --name meeting-summarizer-user1 -p 5001:5000 \
    -e GEMINI_API_KEY="$GEMINI_API_KEY" -e USER_ID="user_1" \
    --restart unless-stopped meeting-summarizer:latest
  ```
- [ ] User 2 container started (port 5002)
  ```bash
  docker run -d --name meeting-summarizer-user2 -p 5002:5000 \
    -e GEMINI_API_KEY="$GEMINI_API_KEY" -e USER_ID="user_2" \
    --restart unless-stopped meeting-summarizer:latest
  ```
- [ ] User 3 container started (port 5003)
  ```bash
  docker run -d --name meeting-summarizer-user3 -p 5003:5000 \
    -e GEMINI_API_KEY="$GEMINI_API_KEY" -e USER_ID="user_3" \
    --restart unless-stopped meeting-summarizer:latest
  ```
- [ ] User 4 container started (port 5004)
  ```bash
  docker run -d --name meeting-summarizer-user4 -p 5004:5000 \
    -e GEMINI_API_KEY="$GEMINI_API_KEY" -e USER_ID="user_4" \
    --restart unless-stopped meeting-summarizer:latest
  ```

### Step 7: Verify Deployment
- [ ] All containers running: `docker ps`
  - [ ] meeting-summarizer-user1 (Up)
  - [ ] meeting-summarizer-user2 (Up)
  - [ ] meeting-summarizer-user3 (Up)
  - [ ] meeting-summarizer-user4 (Up)
- [ ] Health checks passing:
  - [ ] Port 5001: `curl http://localhost:5001/health`
  - [ ] Port 5002: `curl http://localhost:5002/health`
  - [ ] Port 5003: `curl http://localhost:5003/health`
  - [ ] Port 5004: `curl http://localhost:5004/health`
- [ ] All health checks return `{"status":"healthy",...}`

---

## Data Loading

### Step 8: Load Transcripts
- [ ] Data loading script run: `python3 load_data.py`
- [ ] Option selected (1 for AMI, 2 for synthetic)
- [ ] Data files created:
  - [ ] `data/transcripts/*.txt` files exist
  - [ ] `data/metadata.json` exists
- [ ] File count verified: `ls data/transcripts/ | wc -l`

---

## Local Evaluation Setup

### Step 9: Local Machine Setup
- [ ] Repository cloned locally: `git clone ...`
- [ ] Python dependencies installed: `pip install -r requirements.txt`
- [ ] EC2 IP exported: `export EC2_IP="your_ec2_ip"`
- [ ] Data copied from EC2:
  ```bash
  scp -i your-key.pem -r ubuntu@$EC2_IP:~/CSE291/data ./
  ```

### Step 10: Test Connection
- [ ] Single container test successful:
  ```bash
  python3 client.py http://$EC2_IP:5001
  ```
- [ ] Test output shows:
  - [ ] ✓ Health check passed
  - [ ] ✓ Session created
  - [ ] ✓ Summarization successful
  - [ ] ✓ All tests passed

---

## Full Evaluation

### Step 11: Run Multi-User Evaluation
- [ ] Evaluation started:
  ```bash
  python3 evaluate_api.py http://$EC2_IP:500
  ```
- [ ] Evaluation completed without errors
- [ ] Results generated:
  - [ ] `results/api_evaluation.json`
  - [ ] `results/latency_vs_context.png`
  - [ ] `results/success_rate_by_user.png`
  - [ ] `results/latency_cdf_by_user.png`

### Step 12: Review Results
- [ ] JSON results reviewed: `cat results/api_evaluation.json`
- [ ] Summary statistics noted:
  - Total requests: `____`
  - Success rate: `____%`
  - Mean latency: `____ms`
  - P95 latency: `____ms`
- [ ] Plots reviewed and saved
- [ ] Findings documented

---

## Post-Evaluation

### Step 13: Monitoring (Optional)
- [ ] Container logs reviewed:
  ```bash
  docker logs meeting-summarizer-user1
  docker logs meeting-summarizer-user2
  docker logs meeting-summarizer-user3
  docker logs meeting-summarizer-user4
  ```
- [ ] Resource usage checked: `docker stats`
- [ ] No errors in logs

### Step 14: Documentation
- [ ] Baseline performance documented
- [ ] Plots added to write-up
- [ ] Limitations identified for Phase 2
- [ ] Cost tracking started

---

## Cleanup (When Done)

### Stop Containers (Keep for Later)
- [ ] Containers stopped: `docker stop $(docker ps -q -f name=meeting-summarizer)`
- [ ] Containers preserved for restart

### Remove Containers (Complete Cleanup)
- [ ] Containers removed: `docker rm -f $(docker ps -aq -f name=meeting-summarizer)`
- [ ] Images removed (optional): `docker rmi meeting-summarizer:latest`

### Terminate EC2 (When Completely Done)
- [ ] Instance stopped (if keeping for later)
- [ ] Instance terminated (if done with project)
- [ ] Elastic IP released (if used)
- [ ] Billing verified

---

## Troubleshooting Notes

### Common Issues Encountered:
1. Issue: `________________________________`
   Solution: `________________________________`

2. Issue: `________________________________`
   Solution: `________________________________`

3. Issue: `________________________________`
   Solution: `________________________________`

---

## Timing Log

- EC2 launch: `________` (time)
- Docker setup: `________` (time)
- Image build: `________` (time)
- Containers started: `________` (time)
- Data loaded: `________` (time)
- Evaluation completed: `________` (time)
- **Total time**: `________`

---

## Cost Tracking

- Instance type: `________`
- Hours running: `________`
- Estimated cost: `$________`
- Actual cost: `$________` (after billing)

---

## Success Criteria

- [x] ✓ 4 user containers running
- [x] ✓ All health checks passing
- [x] ✓ 20+ transcripts processed
- [x] ✓ Evaluation completed
- [x] ✓ Results generated and visualized
- [x] ✓ Baseline metrics documented
- [x] ✓ Ready for Phase 2

---

## Notes

Space for additional notes:

```
_____________________________________________________

_____________________________________________________

_____________________________________________________

_____________________________________________________

_____________________________________________________
```

---

**Completion Date**: `________________`

**Deployed By**: `________________`

**Status**: ☐ In Progress  ☐ Completed  ☐ Issues

---

## Next Phase

After completing this checklist, proceed to Phase 2:
- [ ] Review baseline limitations
- [ ] Design context management solution
- [ ] Plan vector database integration
- [ ] Design memory architecture
- [ ] Plan comparative evaluation

