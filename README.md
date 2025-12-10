# Meeting Summarizer Agent


A Python application that uses Google's Gemini AI to analyze meeting transcripts and automatically sync extracted information to Google Calendar and Tasks.

---

## 🚀 Steps to Run

```bash
# 1. Clone and setup
git clone https://github.com/Jyotikakakar/CSE291.git
cd CSE291
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Set Gemini API Key
export GEMINI_API_KEY="your-api-key-here"

# 3. Place Google OAuth credentials.json in project root
# (Download from Google Cloud Console)

# 4. Run the agent
python run.py
```

> **Note:** The context-free meeting agent is available on the `main` branch.

---

## Features

- **AI-Powered Summarization** - Uses Gemini 2.0 Flash to extract decisions, action items, risks, and key points
- **Google Calendar Integration** - Automatically creates calendar events for scheduled meetings
- **Google Tasks Integration** - Creates tasks for action items with owners and due dates
- **Smart Scheduling** - Detects conflicts and finds free time slots automatically
- **Context-Aware** - Maintains context across multiple meetings for better summaries
- **Local Storage** - SQLite database stores all meeting data locally
- **Cleanup Support** - Automatically removes previously synced items before re-syncing

---

## Phase 2: Context & Memory Implementation

This section documents the context and memory architecture that enables the Meeting Summarizer Agent to maintain state across sessions and provide intelligent, context-aware processing.

### Overview

The agent implements a **multi-layer memory system** that captures, stores, and retrieves context from:
- Individual meeting transcripts (intra-session)
- Historical meeting data across sessions (inter-session)
- Active action items and decisions (persistent memory)

### 1. Context Extraction from Conversations and Tool Outputs

#### What Context Matters

For a meeting summarization agent, the following context is critical:

| Context Type | Description | Extraction Method |
|--------------|-------------|-------------------|
| **Meeting Summaries (TL;DR)** | High-level overview of past meetings | LLM-based extraction |
| **Action Items** | Tasks with owners and due dates | Structured JSON extraction |
| **Decisions** | Decisions made with ownership and context | Structured JSON extraction |
| **Context Connections** | Links between current and past meetings | LLM inference with context injection |
| **Risks & Blockers** | Identified issues that persist across meetings | Array extraction |

#### Context Extraction Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Transcript    │────▶│   Gemini LLM     │────▶│  Structured     │
│   (Raw Text)    │     │   with Context   │     │  JSON Output    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  Previous        │
                    │  Meeting Context │
                    │  (from SQLite)   │
                    └──────────────────┘
```

**Implementation Details:**

1. **First Meeting**: Processed without context (baseline extraction)
2. **Subsequent Meetings**: Previous meetings are injected into the prompt:

```python
# From meeting_agent.py - Context injection
if use_context:
    context_summary = self.get_context_from_db()
    if "No previous" not in context_summary:
        context_section = f"""
PREVIOUS MEETING CONTEXT:
{context_summary}

IMPORTANT: Consider the context from previous meetings when analyzing this transcript.
- Reference any ongoing action items or decisions from previous meetings
- Identify connections between this meeting and previous discussions
"""
```

3. **Extraction Prompt**: The LLM is instructed to identify `context_connections` that link the current meeting to prior discussions:

```json
{
  "context_connections": [
    {
      "connection": "Mobile app development discussed in Q4 planning",
      "reference": "Meeting 1 - Priority set for Q4"
    }
  ]
}
```

### 2. Storage System Architecture

The agent uses a **hybrid storage approach** combining:

| Storage Type | Technology | Purpose | Persistence |
|--------------|------------|---------|-------------|
| **Relational DB** | SQLite | Structured meeting data, relationships | Persistent (file) |
| **JSON Files** | File System | Extracted data snapshots, sync state | Persistent (file) |
| **In-Memory** | Python objects | Thread context, session metrics | Session-only |

#### SQLite Database Schema

```
┌─────────────────────────────────────────────────────────────────┐
│                         meetings.db                              │
├─────────────────────────────────────────────────────────────────┤
│  meetings                                                        │
│  ├── id (PK)           INTEGER                                   │
│  ├── thread_id         TEXT          -- User/session grouping    │
│  ├── timestamp         TEXT          -- Meeting date             │
│  ├── tldr              TEXT          -- Quick summary            │
│  ├── summary_json      TEXT          -- Full extracted data      │
│  └── created_at        DATETIME                                  │
│                                                                  │
│  action_items                                                    │
│  ├── id (PK)           INTEGER                                   │
│  ├── meeting_id (FK)   INTEGER       -- Links to meetings        │
│  ├── task              TEXT                                      │
│  ├── owner             TEXT                                      │
│  ├── due_date          TEXT                                      │
│  ├── google_task_id    TEXT          -- Sync tracking            │
│  └── created_at        DATETIME                                  │
│                                                                  │
│  decisions                                                       │
│  ├── id (PK)           INTEGER                                   │
│  ├── meeting_id (FK)   INTEGER                                   │
│  ├── decision          TEXT                                      │
│  ├── owner             TEXT                                      │
│  ├── context           TEXT          -- Why decision was made    │
│  └── created_at        DATETIME                                  │
│                                                                  │
│  calendar_events                                                 │
│  ├── id (PK)           INTEGER                                   │
│  ├── meeting_id (FK)   INTEGER                                   │
│  ├── google_event_id   TEXT          -- Sync tracking            │
│  ├── summary           TEXT                                      │
│  ├── start_time        TEXT                                      │
│  └── created_at        DATETIME                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### JSON File Storage

| File | Purpose |
|------|---------|
| `data/extracted_data.json` | Snapshot of all extracted meeting data for sync-only mode |
| `data/sync_state.json` | Tracks Google Task/Event IDs for cleanup on re-sync |

#### Thread-Based Session Management

The agent uses `thread_id` to isolate user sessions:

```python
# Each agent instance has its own thread
agent = MCPMeetingAgent(thread_id="meetings", enable_google=True)

# Context retrieval is scoped to the thread
cursor.execute("""
    SELECT id, timestamp, tldr, summary_json
    FROM meetings
    WHERE thread_id = ?
    ORDER BY created_at DESC
    LIMIT ?
""", (self.thread_id, max_meetings))
```

This enables:
- **Intra-session memory**: Context within a single run
- **Inter-session memory**: Context persists across runs (same thread_id)
- **User isolation**: Different thread_ids maintain separate contexts

### 3. Tool Call Optimization Based on Context

The agent optimizes external tool calls (Google API) using stored context:

#### Smart Calendar Scheduling

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Preferred     │────▶│  Check Conflict  │────▶│  Create Event   │
│   Time Slot     │     │  (API Call)      │     │  (Final Slot)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
            No Conflict              Conflict Detected
                    │                     │
                    ▼                     ▼
            Use Preferred         Find Free Slot
                                  (Same Day → Next Day)
```

**Implementation:**

```python
def create_calendar_event_smart(self, summary, description, preferred_time, duration_minutes):
    # Check for conflict at preferred time
    if self.check_conflict(preferred_time, duration_minutes):
        # Find alternative slot on the same day
        alternative_time = self.find_free_slot(preferred_time, duration_minutes)
        
        if not alternative_time:
            # Try the next day if no slot found
            alternative_time = self.find_free_slot(preferred_time + timedelta(days=1), duration_minutes)
    
    return self.create_calendar_event(summary, description, preferred_time, duration_minutes)
```

#### Sync State Tracking

The agent tracks all created Google resources to enable:
- **Idempotent re-syncs**: Delete previous items before creating new ones
- **Resource cleanup**: No orphaned tasks/events on re-run

```python
# Sync state structure
{
    "task_ids": ["task_abc123", "task_def456"],
    "event_ids": ["event_xyz789"]
}
```

### 4. Error Handling and Resource Management

#### Database Connection Management

```python
class MCPMeetingAgent:
    def __init__(self, ...):
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Dict-like access
            # ... table creation ...
        except Exception as e:
            print(f"Warning: Database initialization error: {e}")
    
    def cleanup(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
```

#### Google API Error Handling

| Error Type | Handling Strategy |
|------------|-------------------|
| `HttpError 404/410` | Resource already deleted → Return success |
| `Token Expired` | Automatic refresh using refresh_token |
| `Credentials Missing` | Descriptive error with setup instructions |
| `API Quota Exceeded` | Graceful degradation (skip sync) |

```python
def delete_calendar_event(self, event_id):
    try:
        self.calendar_service.events().delete(...).execute()
        return True
    except HttpError as e:
        if e.resp.status in [404, 410]:
            return True  # Already deleted
        print(f"Error deleting event: {e}")
        return False
```

#### Instance Constraints

The agent operates within the following constraints:

| Resource | Constraint | Handling |
|----------|------------|----------|
| SQLite connections | 1 per agent instance | Cleanup on exit |
| Google API tokens | Single token.json | Automatic refresh |
| Memory (context) | Last 3 meetings + 5 action items | Configurable limits |
| Gemini API | Rate limited | No retry (fast-fail) |

### Context Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Meeting Summarizer Agent                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌───────────┐        ┌─────────────┐        ┌───────────────────┐         │
│   │ Transcript│───────▶│   Gemini    │───────▶│ Structured Output │         │
│   │  Input    │        │   + Context │        │ (JSON Summary)    │         │
│   └───────────┘        └──────▲──────┘        └────────┬──────────┘         │
│                               │                        │                     │
│                    ┌──────────┴──────────┐             │                     │
│                    │                     │             ▼                     │
│          ┌─────────┴─────────┐  ┌────────┴────────┐  ┌───────────────┐      │
│          │   SQLite DB       │  │  Previous       │  │  Store in DB  │      │
│          │   (Persistent)    │◀─│  Meeting TL;DRs │  │  + JSON File  │      │
│          │                   │  │  + Action Items │  │               │      │
│          └─────────┬─────────┘  └─────────────────┘  └───────┬───────┘      │
│                    │                                          │              │
│                    ▼                                          ▼              │
│          ┌─────────────────────────────────────────────────────────┐        │
│          │                    Google Sync                           │        │
│          │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │        │
│          │  │ Tasks API   │  │ Calendar API│  │ Conflict Check  │  │        │
│          │  │ (Actions)   │  │ (Meetings)  │  │ + Smart Schedule│  │        │
│          │  └─────────────┘  └─────────────┘  └─────────────────┘  │        │
│          └─────────────────────────────────────────────────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Summary: Memory Types Implemented

| Memory Type | Scope | Storage | Retrieval |
|-------------|-------|---------|-----------|
| **Intra-session** | Single run | In-memory + DB | Automatic per meeting |
| **Inter-session** | Across runs | SQLite DB | By thread_id lookup |
| **Cross-user** (Future) | Multiple users | Would require distributed DB | Not implemented |

### Future Enhancements (Cross-User Memory)

For cross-user context sharing, the architecture would need:

1. **Distributed Storage**: PostgreSQL or MongoDB cluster
2. **User Authentication**: OAuth for user identification
3. **Permission Model**: Define what context is shareable
4. **Conflict Resolution**: Handle concurrent updates

---

## Quick Start

### Prerequisites
- Python 3.10+
- Google Gemini API key
- Google OAuth credentials (for Calendar/Tasks integration)

### Installation

```bash
# Clone the repository
git clone https://github.com/Jyotikakakar/CSE291.git
cd CSE291

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

#### 1. Set up Gemini API Key

Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey):

```bash
# Option 1: Environment variable
export GEMINI_API_KEY="your-api-key-here"

# Option 2: .env file
echo "GEMINI_API_KEY=your-api-key-here" > .env
```

#### 2. Set up Google OAuth (for Calendar/Tasks)

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select an existing one
3. Enable the **Google Calendar API** and **Google Tasks API**
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials and save as `credentials.json` in the project root

On first run, a browser window will open for authentication. The token is saved to `token.json` for future use.

## Usage

Process transcripts with Gemini AI and sync results to Google:

```bash
python run.py
```

## What Gets Extracted

The agent analyzes meeting transcripts and extracts:

| Field | Description |
|-------|-------------|
| **TL;DR** | 2-3 sentence summary of the meeting |
| **Decisions** | Decisions made with owners and context |
| **Action Items** | Tasks with owners and due dates → synced to Google Tasks |
| **Meetings to Schedule** | Follow-up meetings → synced to Google Calendar |
| **Risks** | Identified blockers and risks |
| **Key Points** | Main discussion points |
| **Context Connections** | Links to previous meetings (when context is enabled) |

## Example Output

After running the agent on sample transcripts:

```
================================================================================
MEETING 1: sample_001.txt
================================================================================
Transcript length: 217 words

✓ Summarized in 2847ms
  Meeting ID: 1

TL;DR:
  The Q4 planning meeting prioritized mobile app development and SSO implementation...

Decisions (8):
  - Mobile app development is the top priority for Q4. (Owner: Speaker A)
  - Speaker B will lead the mobile app project. (Owner: Speaker A)
  ...

Action Items (5):
  - Lead the mobile app development project. (Owner: Speaker B, Due: N/A)
  - Own the SSO implementation. (Owner: Speaker C, Due: 2025-11-30)
  ...

📅 Meetings Scheduled (1):
  - Q4 Mobile App & SSO Progress Review: 2025-12-10 at 14:00 (60 min)

Risks (1):
  - Our current authentication service is outdated.

✓ Created task: Lead the mobile app development project.
✓ Created task: Own the SSO implementation.
✓ Created calendar event: Q4 Mobile App & SSO Progress Review
✓ Synced 6 items to Google
```

## Data Files

| File | Description |
|------|-------------|
| `data/transcripts/<user>/` | User-specific transcript folders (e.g., `sarah_pm/`, `mike_eng/`) |
| `data/extracted_data.json` | Extracted meeting data (JSON) |
| `data/sync_state.json` | Tracks synced items for cleanup |
| `meetings.db` | SQLite database with all meeting data |

## Project Structure

```
CSE291/
├── run.py                  # Main entry point (3 modes)
├── meeting_agent.py        # Core agent with Gemini + Google integration
├── google_integration.py   # Google Calendar/Tasks API wrapper
├── config.py               # Configuration and environment setup
├── requirements.txt        # Python dependencies
├── credentials.json        # Google OAuth credentials (not in git)
├── token.json              # Google OAuth token (not in git)
├── meetings.db             # SQLite database
├── data/
│   ├── transcripts/        # User-organized transcript folders
│   │   ├── sarah_pm/       # Each user has their own folder
│   │   │   ├── q4_planning.txt
│   │   │   └── roadmap_planning.txt
│   │   ├── mike_eng/
│   │   │   ├── daily_standup.txt
│   │   │   └── sprint_retro.txt
│   │   └── priya_design/
│   │       └── ux_review.txt
│   ├── extracted_data.json # Extracted meeting data
│   └── sync_state.json     # Sync tracking state
└── README.md
```

## Smart Scheduling

The Google integration includes intelligent conflict handling:

1. **Conflict Detection** - Checks if preferred time slot is busy
2. **Free Slot Finder** - Searches for available 30-minute slots (9 AM - 6 PM)
3. **Fallback** - Tries the next day if no slots available today
4. **Calendar Event Creation** - Creates events with attendees and descriptions

Example:
```
⚠ Conflict detected at 2025-12-10 14:00, finding alternative...
✓ Found free slot at 15:00
✓ Created calendar event: Q4 Mobile App & SSO Progress Review
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `GEMINI_MODEL` | No | Model name (default: `gemini-2.0-flash-exp`) |

## Docker Support

```bash
# Build and run
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild after changes
docker-compose up --build
```

## Deployment Architecture

The application supports a **multi-container deployment** model where data is shared across instances via volume mapping.

### Volume-Mapped Data Sharing

```
┌─────────────────────────────────────────────────────────────────┐
│                    Host File System                              │
│                                                                  │
│   /path/to/shared/data/transcripts/                             │
│   ├── sarah_pm/                                                  │
│   │   ├── q4_planning.txt                                        │
│   │   └── roadmap_planning.txt                                   │
│   ├── mike_eng/                                                  │
│   │   └── daily_standup.txt                                      │
│   └── <new_user>/                                                │
│       └── <uploaded_transcript>.txt                              │
│                                                                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Container 1 │ │  Container 2 │ │  Container N │
│  (Instance)  │ │  (Instance)  │ │  (Instance)  │
│              │ │              │ │              │
│  /app/data/  │ │  /app/data/  │ │  /app/data/  │
│  transcripts │ │  transcripts │ │  transcripts │
└──────────────┘ └──────────────┘ └──────────────┘
```

### How It Works

1. **Shared Volume**: The `data/transcripts` directory is volume-mapped into each container instance
2. **User Upload**: Users upload transcript files directly to the shared folder on the host
3. **Automatic Context**: Each container instance automatically detects and processes new files
4. **Context Awareness**: The SQLite database and context injection ensure each instance has access to meeting history

### Docker Compose Configuration

```yaml
services:
  app:
    build: .
    container_name: meeting-summarizer
    volumes:
      - ./data:/app/data
      - ./meetings.db:/app/meetings.db
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
```

### Cross-User Context Sharing

The agent supports **cross-user context** via a global thread. When processing meetings, each user's key decisions and action items are shared to a global context, enabling team-wide awareness:

```python
# Each user agent shares condensed summaries to the global thread
agent = MCPMeetingAgent(
    thread_id="sarah_pm",           # User-specific context
    global_thread_id="global",      # Shared team context
    enable_google=True
)
```

This enables:
- **Team Context Injection**: When summarizing, the agent includes relevant context from other users' meetings
- **Cross-Functional Awareness**: Decisions made by `sarah_pm` are visible when processing `mike_eng`'s meetings
- **Source Attribution**: Cross-user context is tagged with `[username]` for traceability

### Scaling Considerations

| Aspect | Handling |
|--------|----------|
| **Transcript Access** | All containers read from same volume-mapped directory |
| **Database Locking** | SQLite handles concurrent reads; write operations are serialized |
| **Context Sharing** | Each instance queries the same `meetings.db` for historical context |
| **User Isolation** | Each user folder creates a separate `thread_id` for isolated context |
| **Cross-User Context** | Global thread aggregates key insights across all users |

### Usage

```bash
# Start the container
docker-compose up -d

# Upload a transcript for a specific user (on host machine)
mkdir -p ./data/transcripts/john_dev
cp new_meeting.txt ./data/transcripts/john_dev/

# Each container instance will automatically detect new user folders and process their transcripts
```

## License

MIT License
