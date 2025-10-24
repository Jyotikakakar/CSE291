How to Use on EC2:

SSH into your EC2 and run:


ssh -i your-key.pem ubuntu@<public_ip>


export AWS_ACCESS_KEY_ID="ASIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="IQoJb3JpZ2luX2VjE..."
export AWS_DEFAULT_REGION="us-west-2"

# Stop old container
docker stop meeting-summarizer-user1
docker rm meeting-summarizer-user1

# Start with ALL THREE credential variables
docker run -d \
  --name meeting-summarizer-user1 \
  -p 5001:5000 \
  -e GEMINI_API_KEY="" \
  -e GEMINI_MODEL="gemini-2.5-flash-lite" \
  -e USER_ID="user_1" \
  -e AWS_ACCESS_KEY_ID="" \
  -e AWS_SECRET_ACCESS_KEY="" \
   -e AWS_SESSION_TOKEN="" \
  -e AWS_DEFAULT_REGION="us-west-2" \
  --restart unless-stopped \
  meeting-summarizer:latest
  

# Test it
curl -X POST http://<public_ip>:5001/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_url": "s3://<bucket_name>/meeting_01.txt"
  }'