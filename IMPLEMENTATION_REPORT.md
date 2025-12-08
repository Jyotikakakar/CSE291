# Meeting Summarizer Agent - Implementation Report

## CSE 291 Project Evaluation Criteria Documentation

---

## Table of Contents
1. [Repository Organization](#1-repository-organization)
2. [Setup and Running Instructions](#2-setup-and-running-instructions)
3. [Context-Related Component Implementation](#3-context-related-component-implementation)
   - [Context Extraction](#31-context-extraction-from-conversations-and-tool-outputs)
   - [Storage System](#32-storage-system)
   - [Tool Call Optimization](#33-tool-call-optimization-based-on-context)
   - [Error Handling & Resource Management](#34-error-handling-and-resource-management)
4. [Architecture Summary](#4-architecture-summary)

---

## 1. Repository Organization

### Project Structure

```
CSE291/
├── run.py                  # Main entry point with 3 operational modes
├── meeting_agent.py        # Core agent with Gemini AI + context management
├── google_integration.py   # Google Calendar/Tasks API wrapper
├── config.py               # Configuration and environment variables
├── requirements.txt        # Python dependencies with version pinning
├── Dockerfile              # Container support
├── docker-compose.yml      # Multi-container orchestration
├── README.md               # Comprehensive documentation (570+ lines)
├── IMPLEMENTATION_REPORT.md # This document
├── data/
│   ├── transcripts/        # Input meeting transcripts by user
│   │   ├── mike_eng/
│   │   ├── priya_design/
│   │   └── sarah_pm/
│   ├── extracted_data.json # Extracted meeting data cache
│   └── sync_state.json     # Sync tracking for idempotent operations
└── meetings.db             # SQLite database for persistent storage
```

### README Quality

The README includes:
- **Quick Start Guide** - 5-step setup process with copy-paste commands
- **Feature List** - Clear enumeration of agent capabilities
- **Usage Examples** - All three operational modes documented
- **Architecture Diagrams** - ASCII art flow diagrams for context and sync flows
- **Database Schema** - Complete ERD with field descriptions
- **Environment Variables** - Required/optional configuration table
- **Docker Support** - Full container deployment instructions

---

## 2. Setup and Running Instructions

### Prerequisites
- Python 3.10+
- Google Gemini API key ([Get from AI Studio](https://makersuite.google.com/app/apikey))
- Google OAuth credentials (for Calendar/Tasks integration)

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/Jyotikakakar/CSE291.git
cd CSE291

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API keys
export GEMINI_API_KEY="your-api-key-here"

# 5. Place Google OAuth credentials.json in project root
```

### Running the Agent

| Mode | Command | Description |
|------|---------|-------------|
| **Full Pipeline** | `python run.py` | Extract + Save JSON + Sync to Google |
| **Extract Only** | `python run.py --extract` | AI extraction only (no Google sync) |
| **Sync Only** | `python run.py --sync` | Sync from saved JSON (no Gemini needed) |
| **User Filter** | `python run.py --user sarah_pm` | Process single user's transcripts |

### Verification

```bash
# Expected output after successful run:
================================================================================
MEETING AGENT - Extract Mode (Cross-User Context)
================================================================================

Found 3 user(s): ['mike_eng', 'priya_design', 'sarah_pm']
✓ Initialized agent (Thread: mike_eng)
✓ Database initialized (./meetings.db)
✓ Authenticated with Google Calendar and Tasks

  Meeting 1: daily_standup.txt
  ✓ Summarized in 2847ms
  ✓ Synced 4 items to Google
```

---

## 3. Context-Related Component Implementation

### 3.1 Context Extraction from Conversations and Tool Outputs

#### What Context is Extracted

The agent extracts structured context from meeting transcripts:

| Context Type | Description | Storage Location |
|--------------|-------------|------------------|
| **TL;DR Summaries** | 2-3 sentence meeting overview | `meetings.tldr` |
| **Decisions** | Decisions with owner and context | `decisions` table |
| **Action Items** | Tasks with owner and due date | `action_items` table |
| **Context Connections** | Links to previous meetings | `summary_json` field |
| **Risks & Blockers** | Identified issues | `summary_json` field |
| **Cross-User Context** | Team-wide shared context | Global thread entries |

#### Implementation: Context Injection Flow

```python
# meeting_agent.py - Context injection into LLM prompt
def summarize(self, transcript: str, use_context: bool = True, ...):
    context_section = ""
    if use_context:
        context_summary = self.get_context_from_db()
        if "No previous" not in context_summary:
            context_section = f"""
PREVIOUS MEETING CONTEXT:
{context_summary}

IMPORTANT: You MUST identify connections to the context above.
- If TEAM CONTEXT exists, reference those items using the [username] tag shown
- Reference any ongoing action items or decisions
"""
```

#### Context Retrieval Query

```python
# meeting_agent.py - Multi-source context retrieval
def get_context_from_db(self, max_meetings: int = 3) -> str:
    # 1. Get user's recent meetings
    cursor.execute("""
        SELECT id, timestamp, tldr, summary_json
        FROM meetings WHERE thread_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (self.thread_id, max_meetings))
    
    # 2. Get user's recent action items
    cursor.execute("""
        SELECT task, owner, due_date FROM action_items
        WHERE meeting_id IN (SELECT id FROM meetings WHERE thread_id = ?)
        ORDER BY created_at DESC LIMIT 5
    """, (self.thread_id,))
    
    # 3. Get cross-user context from global thread
    if self.global_thread_id:
        cursor.execute("""
            SELECT tldr, summary_json FROM meetings
            WHERE thread_id = ? AND tldr NOT LIKE ?
            ORDER BY created_at DESC LIMIT 5
        """, (self.global_thread_id, f"[{self.thread_id}]%"))
```

#### Context Connection Output Example

```json
{
  "context_connections": [
    {
      "connection": "Mobile app development relates to Q4 priorities",
      "reference": "[sarah_pm] Mobile app set as Q4 priority"
    },
    {
      "connection": "SSO implementation continues from previous sprint",
      "reference": "Meeting 2 - SSO task assigned to Mike"
    }
  ]
}
```

---

### 3.2 Storage System

The agent implements a **hybrid storage architecture** with three tiers:

#### Storage Tier Overview

| Tier | Technology | Data Type | Persistence | Use Case |
|------|------------|-----------|-------------|----------|
| **Relational** | SQLite | Structured records | Persistent | Meetings, actions, decisions |
| **File System** | JSON files | Data snapshots | Persistent | Extracted data, sync state |
| **In-Memory** | Python objects | Session metrics | Session-only | Thread context, latency tracking |

#### SQLite Database Schema

```sql
-- meetings.db schema

-- Primary meeting records
CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,        -- User/session isolation
    timestamp TEXT NOT NULL,         -- Meeting date
    tldr TEXT,                       -- Quick summary
    summary_json TEXT,               -- Full extracted JSON
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Action items with Google sync tracking
CREATE TABLE action_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,              -- FK to meetings
    task TEXT NOT NULL,
    owner TEXT,
    due_date TEXT,
    google_task_id TEXT,             -- Sync tracking
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
);

-- Decisions with context
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    decision TEXT NOT NULL,
    owner TEXT,
    context TEXT,                    -- Why decision was made
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
);

-- Calendar events with Google sync tracking
CREATE TABLE calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER,
    google_event_id TEXT,            -- Sync tracking
    summary TEXT,
    start_time TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
);
```

#### JSON File Storage

| File | Purpose | Structure |
|------|---------|-----------|
| `data/extracted_data.json` | Cache of all extracted meetings | `{ "user/filename": {...summary...} }` |
| `data/sync_state.json` | Track synced Google resources | `{ "task_ids": [...], "event_ids": [...] }` |

**Example sync_state.json:**
```json
{
  "task_ids": ["task_abc123", "task_def456", "task_ghi789"],
  "event_ids": ["event_xyz001", "event_xyz002"]
}
```

#### Thread-Based Isolation

```python
# meeting_agent.py - Thread isolation for multi-user support
agent = MCPMeetingAgent(
    thread_id="sarah_pm",           # User's private context
    global_thread_id="global",      # Shared team context
    enable_google=True
)

# Context queries are automatically scoped
cursor.execute("""
    SELECT ... FROM meetings WHERE thread_id = ?
""", (self.thread_id,))
```

This enables:
- **Intra-session memory**: Context within a single run
- **Inter-session memory**: Context persists across runs (same thread_id)
- **Cross-user context**: Team-wide shared context via global_thread_id

---

### 3.3 Tool Call Optimization Based on Context

#### Smart Calendar Scheduling

The agent optimizes Google Calendar API calls by checking for conflicts before creating events:

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
# google_integration.py - Smart conflict resolution
def create_calendar_event_smart(self, summary, description, preferred_time, duration_minutes):
    # Step 1: Check for conflict at preferred time
    if self.check_conflict(preferred_time, duration_minutes):
        print(f"⚠ Conflict detected at {preferred_time}, finding alternative...")
        
        # Step 2: Find alternative slot on same day (9 AM - 6 PM)
        alternative_time = self.find_free_slot(
            preferred_time, duration_minutes,
            start_hour=9, end_hour=18
        )
        
        if alternative_time:
            preferred_time = alternative_time
        else:
            # Step 3: Try next day if no slot found
            next_day = preferred_time + timedelta(days=1)
            alternative_time = self.find_free_slot(next_day, duration_minutes)
            if alternative_time:
                preferred_time = alternative_time
    
    # Step 4: Create event at final determined time
    return self.create_calendar_event(summary, description, preferred_time, duration_minutes)
```

**Free Slot Finding Algorithm:**

```python
# google_integration.py - Efficient slot discovery
def find_free_slot(self, target_date, duration_minutes=60, start_hour=9, end_hour=17):
    # Get all events on target day (single API call)
    events = self.get_events_on_date(target_date)
    
    # Build busy periods list
    busy_periods = [(parse(event['start']), parse(event['end'])) for event in events]
    busy_periods.sort(key=lambda x: x[0])
    
    # Try each 30-minute slot
    for hour in range(start_hour, end_hour):
        for minute in [0, 30]:
            slot_start = datetime.combine(target_date.date(), time(hour, minute))
            slot_end = slot_start + timedelta(minutes=duration_minutes)
            
            # Check against all busy periods
            if not any(overlaps(slot_start, slot_end, busy) for busy in busy_periods):
                return slot_start
    
    return None  # No free slot found
```

#### Idempotent Sync Operations

The agent tracks all created resources to enable safe re-sync:

```python
# run.py - Delete previous sync before creating new items
def delete_previous_sync(agent):
    sync_state = load_sync_state()
    
    # Delete all previously created tasks
    if sync_state.get("task_ids"):
        agent.google.delete_multiple_tasks(sync_state["task_ids"])
    
    # Delete all previously created events
    if sync_state.get("event_ids"):
        agent.google.delete_multiple_events(sync_state["event_ids"])
    
    # Clear sync state
    save_sync_state({"task_ids": [], "event_ids": []})
```

---

### 3.4 Error Handling and Resource Management

#### Database Connection Management

```python
# meeting_agent.py - Safe database lifecycle
class MCPMeetingAgent:
    def __init__(self, ...):
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Dict-like access
            # Create tables...
            self.conn.commit()
        except Exception as e:
            print(f"Warning: Database initialization error: {e}")
    
    def cleanup(self):
        """Close database connection - called at end of processing."""
        if self.conn:
            self.conn.close()
```

#### Google API Error Handling

| Error Type | HTTP Code | Handling Strategy |
|------------|-----------|-------------------|
| Resource Not Found | 404 | Return success (already deleted) |
| Resource Gone | 410 | Return success (already deleted) |
| Token Expired | 401 | Automatic refresh via refresh_token |
| Credentials Missing | N/A | Descriptive error with setup URL |
| API Errors | Various | Log and continue (graceful degradation) |

```python
# google_integration.py - Resilient delete operations
def delete_calendar_event(self, event_id: str) -> bool:
    try:
        self.calendar_service.events().delete(
            calendarId='primary',
            eventId=event_id
        ).execute()
        return True
    except HttpError as e:
        if e.resp.status in [404, 410]:
            return True  # Already deleted - success
        print(f"Error deleting event {event_id}: {e}")
        return False

def delete_task(self, task_id: str, task_list_id: str = '@default') -> bool:
    try:
        self.tasks_service.tasks().delete(
            tasklist=task_list_id,
            task=task_id
        ).execute()
        return True
    except HttpError as e:
        if e.resp.status == 404:
            return True  # Already deleted - success
        print(f"Error deleting task {task_id}: {e}")
        return False
```

#### Token Refresh Flow

```python
# google_integration.py - Automatic credential refresh
def authenticate(self):
    creds = None
    
    # Load existing token
    if os.path.exists(self.token_file):
        creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
    
    # Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"Token refresh failed: {e}")
            creds = None
    
    # Get new credentials if needed
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
        creds = flow.run_local_server(port=0)
    
    # Persist token
    with open(self.token_file, 'w') as token:
        token.write(creds.to_json())
```

#### Instance Constraints

| Resource | Constraint | Management |
|----------|------------|------------|
| SQLite Connections | 1 per agent | Cleanup via `agent.cleanup()` |
| Google API Tokens | Single `token.json` | Automatic refresh |
| Context History | Last 3 meetings + 5 actions | Configurable via `max_meetings` |
| Gemini API | Rate limited | Fast-fail (no retry) |
| File Handles | Auto-managed | Context managers for JSON I/O |

#### Graceful Degradation

```python
# meeting_agent.py - Optional Google integration
def __init__(self, thread_id, enable_google=True, require_gemini=True):
    # Gemini is optional for sync-only mode
    self.model = None
    if require_gemini:
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
    
    # Google integration is optional
    self.google = None
    if enable_google:
        try:
            self.google = GoogleIntegration()
        except Exception as e:
            print(f"Warning: Google integration disabled - {e}")
            # Agent continues to work without Google sync
```

---

## 4. Architecture Summary

### Complete Data Flow

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
│          │                    Google Sync Layer                     │        │
│          │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │        │
│          │  │ Tasks API   │  │ Calendar API│  │ Conflict Check  │  │        │
│          │  │ (Actions)   │  │ (Meetings)  │  │ + Smart Schedule│  │        │
│          │  └─────────────┘  └─────────────┘  └─────────────────┘  │        │
│          └─────────────────────────────────────────────────────────┘        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Implementation Highlights

| Criterion | Implementation |
|-----------|----------------|
| **Context Extraction** | LLM-based extraction with structured JSON output; cross-user context sharing via global thread |
| **Storage System** | Hybrid: SQLite (relational) + JSON files (snapshots) + In-memory (metrics) |
| **Tool Optimization** | Smart scheduling with conflict detection; idempotent sync with state tracking |
| **Error Handling** | Graceful degradation, automatic token refresh, 404/410 handling for deletes |
| **Resource Management** | Cleanup methods, connection limits, configurable context windows |

---

## Appendix: Quick Reference

### Run Commands
```bash
python run.py                    # Full pipeline
python run.py --extract          # Extract only
python run.py --sync             # Sync only
python run.py --user sarah_pm    # Single user
```

### Environment Variables
```bash
export GEMINI_API_KEY="your-key"
export GEMINI_MODEL="gemini-2.0-flash-exp"  # Optional
```

### Key Files
- `meeting_agent.py:269-336` - Context retrieval logic
- `meeting_agent.py:346-458` - Summarization with context injection
- `google_integration.py:275-327` - Smart scheduling
- `run.py:168-199` - Sync state cleanup

---

*Document generated for CSE 291 Project Evaluation*

