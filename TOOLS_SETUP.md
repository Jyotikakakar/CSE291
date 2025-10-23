# Google Calendar and Tasks Integration Setup

This guide explains how to set up Google Calendar and Google Tasks integration for the Meeting Summarizer Agent.

## Overview

The agent now integrates with:
- **Google Calendar** - Automatically create events from meeting decisions
- **Google Tasks** - Automatically create tasks from action items

## Prerequisites

- Google Account
- Google Cloud Console access

---

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your Project ID

---

## Step 2: Enable APIs

1. In Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for and enable:
   - **Google Calendar API**
   - **Google Tasks API**

---

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Configure OAuth consent screen if prompted:
   - User Type: **External** (or Internal if using Google Workspace)
   - App name: `Meeting Summarizer Agent`
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Add the following scopes:
     - `https://www.googleapis.com/auth/calendar`
     - `https://www.googleapis.com/auth/tasks`
   - Test users: Add your email address
4. Create OAuth client ID:
   - Application type: **Desktop app**
   - Name: `Meeting Summarizer`
5. Download the JSON file
6. Rename it to something memorable (e.g., `client_secret.json`)

---

## Step 4: Configure Your Project

### Option 1: Use Existing Credentials (from tools-setup folder)

The project includes sample credentials in `tools-setup/`. To use them:

```bash
# No additional setup needed - files are already in place
# tools-setup/client_secret_*.json
# tools-setup/token.json
```

**Note:** These credentials are for demonstration. For production, use your own credentials.

### Option 2: Use Your Own Credentials

1. Place your downloaded `client_secret.json` in the `tools-setup/` directory
2. Set environment variables:

```bash
export GOOGLE_CREDENTIALS_PATH="/path/to/your/client_secret.json"
export GOOGLE_TOKEN_PATH="/path/to/your/token.json"
```

Or add to `.env` file:

```env
GOOGLE_CREDENTIALS_PATH=tools-setup/client_secret.json
GOOGLE_TOKEN_PATH=tools-setup/token.json
```

---

## Step 5: First-Time Authentication

When you first run the agent with Google tools:

1. Run the agent:
   ```bash
   python agent.py
   ```

2. A browser window will open
3. Sign in to your Google account
4. Grant permissions for:
   - Google Calendar access
   - Google Tasks access
5. The token will be saved to `token.json`

**For subsequent runs**, the agent will use the saved token automatically.

---

## Step 6: Verify Setup

Test the integration locally:

```bash
# Run the agent demo
python agent.py
```

Expected output:
```
Testing Gemini agent with Google Calendar and Tasks integration
================================================================================
✓ Gemini gemini-2.5-flash-live is working

MEETING SUMMARY
================================================================================
{
  "tldr": "Team discussed Q4 priorities...",
  ...
}

DEMO: Calendar & Task Tracker Tools
================================================================================

1. Creating calendar event...
   ✓ Created event: Q4 Planning Follow-up
   Event ID: xyz123...

2. Creating tasks from action items...
   ✓ Created task: Create mobile app spec
   Task ID: abc456...
   ✓ Created task: Audit auth service
   Task ID: def789...

3. Retrieving all tasks...
   ✓ Total tasks: 2
   - Create mobile app spec: needsAction
   - Audit auth service: needsAction

4. Marking task as complete...
   ✓ Marked task complete: Create mobile app spec

5. Retrieving calendar events for today...
   ✓ Found 1 events
   - Q4 Planning Follow-up

================================================================================
✓ Demo complete!
```

---

## Using Tools via API

### Create Calendar Event

```bash
curl -X POST http://localhost:5000/api/calendar/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Q4 Planning Meeting",
    "date": "2025-10-25",
    "time": "2:00 PM",
    "attendees": ["alice@example.com", "bob@example.com"],
    "description": "Quarterly planning session"
  }'
```

### Get Calendar Events

```bash
# All events
curl http://localhost:5000/api/calendar/events

# Events on specific date
curl "http://localhost:5000/api/calendar/events?date=2025-10-25"

# Events with specific attendee
curl "http://localhost:5000/api/calendar/events?attendee=alice@example.com"
```

### Create Task

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Create mobile app spec",
    "owner": "Bob",
    "due_date": "2025-10-30",
    "priority": "high",
    "description": "Detailed specification for mobile app"
  }'
```

### Get Tasks

```bash
# All tasks
curl http://localhost:5000/api/tasks

# Filter by status
curl "http://localhost:5000/api/tasks?status=pending"
curl "http://localhost:5000/api/tasks?status=completed"
```

### Mark Task Complete

```bash
curl -X POST http://localhost:5000/api/tasks/{task_id}/complete
```

### Delete Calendar Event

```bash
curl -X DELETE http://localhost:5000/api/calendar/events/{event_id}
```

---

## EC2 Deployment with Tools

### Copy Credentials to EC2

```bash
# Copy your credentials to EC2
scp -i your-key.pem tools-setup/client_secret.json ubuntu@your-ec2-ip:~/CSE291/tools-setup/
scp -i your-key.pem tools-setup/token.json ubuntu@your-ec2-ip:~/CSE291/tools-setup/
```

### Build Docker Image with Tools

```bash
# On EC2
cd ~/CSE291

# Build image (credentials will be included)
docker build -t meeting-summarizer:latest .

# Run container with credentials
docker run -d \
  --name meeting-summarizer-user1 \
  -p 5001:5000 \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e USER_ID="user_1" \
  -e GOOGLE_CREDENTIALS_PATH="/app/tools-setup/client_secret.json" \
  -e GOOGLE_TOKEN_PATH="/app/tools-setup/token.json" \
  --restart unless-stopped \
  meeting-summarizer:latest
```

---

## Troubleshooting

### "Google credentials file not found"

**Solution:** Check that credentials file exists:
```bash
ls tools-setup/client_secret*.json
```

Set environment variable:
```bash
export GOOGLE_CREDENTIALS_PATH="tools-setup/client_secret.json"
```

### "Token has expired and can't be refreshed"

**Solution:** Delete token and re-authenticate:
```bash
rm tools-setup/token.json
python agent.py
# Follow browser prompts to re-authenticate
```

### "Access blocked: This app's request is invalid"

**Solution:** Check OAuth consent screen configuration:
1. Go to Google Cloud Console → APIs & Services → OAuth consent screen
2. Add your email to Test users
3. Ensure scopes are correctly configured

### "Calendar/Tasks API error: 403"

**Solution:** Ensure APIs are enabled:
1. Go to Google Cloud Console → APIs & Services → Library
2. Verify "Google Calendar API" and "Google Tasks API" are enabled

### Tools not working in Docker

**Solution:** Ensure credentials are copied into the container:
```bash
# Check if files exist in container
docker exec meeting-summarizer-user1 ls -la /app/tools-setup/

# If missing, rebuild image or mount as volume
docker run -d \
  -v $(pwd)/tools-setup:/app/tools-setup \
  ...
```

---

## Security Notes

### Credential Protection

⚠️ **Important Security Considerations:**

1. **Never commit credentials to git**
   - Add to `.gitignore`:
     ```
     tools-setup/client_secret*.json
     tools-setup/token.json
     ```

2. **Use environment variables in production**
   - Don't hardcode paths
   - Use secrets management (AWS Secrets Manager, etc.)

3. **Limit OAuth scopes**
   - Only request necessary permissions
   - Review periodically

4. **Rotate credentials regularly**
   - Generate new OAuth clients
   - Revoke old tokens

### OAuth Token Storage

The `token.json` file contains:
- Access token (short-lived)
- Refresh token (long-lived)
- Expiry information

**Protect this file** - it grants access to your Google account!

---

## Optional: Disable Tools

If you don't need Calendar/Tasks integration:

1. The agent will work without credentials
2. Tool endpoints will return error messages
3. Summarization still works normally

To disable tools:
```bash
# Don't set GOOGLE_CREDENTIALS_PATH
# Or set to non-existent path
export GOOGLE_CREDENTIALS_PATH=""
```

The agent logs:
```
Warning: Google credentials file not found
Tools will not be available. Set GOOGLE_CREDENTIALS_PATH environment variable.
```

---

## Advanced: Service Account (Headless Authentication)

For production deployments without browser access:

1. Create a Service Account in Google Cloud Console
2. Enable Domain-Wide Delegation
3. Download service account key
4. Modify `agent.py` to use service account authentication

**Note:** This requires Google Workspace and additional setup.

---

## Support

For issues:
1. Check Google Cloud Console quotas
2. Verify API enablement
3. Review OAuth consent screen configuration
4. Check token expiration
5. Test with `agent.py` directly before trying API

---

## Summary Checklist

- [ ] Google Cloud project created
- [ ] Calendar and Tasks APIs enabled
- [ ] OAuth credentials downloaded
- [ ] Credentials placed in `tools-setup/`
- [ ] Environment variables set
- [ ] First-time authentication completed
- [ ] `token.json` generated
- [ ] Tools tested locally
- [ ] Tools working via API
- [ ] Credentials secured (not in git)

Once all items are checked, your tools are ready to use! 🎉

