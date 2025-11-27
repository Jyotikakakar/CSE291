#!/usr/bin/env python3
"""
Enhanced Meeting Agent with Google Calendar and Tasks Integration
Demonstrates meeting summarization with automatic calendar event and task creation
"""
import os
import json
import time
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sqlite3

# Google Calendar and Tasks
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

# Google API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks'
]


class GoogleIntegration:
    """Handle Google Calendar and Tasks API interactions."""
    
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.calendar_service = None
        self.tasks_service = None
        self.authenticate()
    
    def authenticate(self):
        """Authenticate with Google APIs."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        "Download from Google Cloud Console: https://console.cloud.google.com/apis/credentials"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        # Build services
        self.calendar_service = build('calendar', 'v3', credentials=creds)
        self.tasks_service = build('tasks', 'v1', credentials=creds)
        
        print("✓ Authenticated with Google Calendar and Tasks")
    
    def create_calendar_event(
        self,
        summary: str,
        description: str = "",
        start_time: datetime = None,
        duration_minutes: int = 60,
        attendees: List[str] = None
    ) -> Optional[Dict]:
        """Create a calendar event."""
        try:
            if start_time is None:
                start_time = datetime.now() + timedelta(days=1)
            
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/Los_Angeles',
                },
            }
            
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            created_event = self.calendar_service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            print(f"✓ Created calendar event: {summary}")
            return created_event
            
        except HttpError as e:
            print(f"Calendar API error: {e}")
            return None
    
    def create_task(
        self,
        title: str,
        notes: str = "",
        due_date: datetime = None,
        task_list_id: str = '@default'
    ) -> Optional[Dict]:
        """Create a task in Google Tasks."""
        try:
            task = {
                'title': title,
                'notes': notes,
            }
            
            if due_date:
                # Google Tasks expects RFC 3339 format for due date (date only, no time)
                task['due'] = due_date.strftime('%Y-%m-%dT00:00:00.000Z')
            
            created_task = self.tasks_service.tasks().insert(
                tasklist=task_list_id,
                body=task
            ).execute()
            
            print(f"✓ Created task: {title}")
            return created_task
            
        except HttpError as e:
            print(f"Tasks API error: {e}")
            return None
    
    def list_task_lists(self) -> List[Dict]:
        """List all task lists."""
        try:
            results = self.tasks_service.tasklists().list().execute()
            return results.get('items', [])
        except HttpError as e:
            print(f"Tasks API error: {e}")
            return []
    
    def get_upcoming_events(self, days: int = 7) -> List[Dict]:
        """Get upcoming calendar events."""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            max_time = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
            
            events_result = self.calendar_service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=max_time,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except HttpError as e:
            print(f"Calendar API error: {e}")
            return []


class MCPMeetingAgent:
    """Meeting agent with context-aware summarization, local storage, and Google integration."""
    
    def __init__(self, thread_id: str = "default", enable_google: bool = True):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        
        self.thread_id = thread_id
        self.db_path = "./meetings.db"
        self.conn = None
        
        # Google integration
        self.google = None
        if enable_google:
            try:
                self.google = GoogleIntegration()
            except Exception as e:
                print(f"Warning: Google integration disabled - {e}")
        
        self.metrics = {
            "total_requests": 0,
            "total_latency_ms": 0
        }
        
        print(f"✓ Initialized agent (Thread: {thread_id})")
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            cursor = self.conn.cursor()
            
            # Create tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    tldr TEXT,
                    summary_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER,
                    task TEXT NOT NULL,
                    owner TEXT,
                    due_date TEXT,
                    google_task_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER,
                    decision TEXT NOT NULL,
                    owner TEXT,
                    context TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calendar_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meeting_id INTEGER,
                    google_event_id TEXT,
                    summary TEXT,
                    start_time TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
                )
            """)
            
            self.conn.commit()
            print(f"✓ Database initialized ({self.db_path})")
            
        except Exception as e:
            print(f"Warning: Database initialization error: {e}")
    
    def store_meeting_in_db(self, summary: Dict[str, Any], transcript: str):
        """Store meeting summary in database."""
        if not self.conn:
            return None
        
        try:
            cursor = self.conn.cursor()
            
            # Insert meeting
            cursor.execute("""
                INSERT INTO meetings (thread_id, timestamp, tldr, summary_json)
                VALUES (?, ?, ?, ?)
            """, (
                self.thread_id,
                datetime.now().isoformat(),
                summary.get('tldr', ''),
                json.dumps(summary)
            ))
            
            meeting_id = cursor.lastrowid
            
            # Store action items
            for action in summary.get('action_items', []):
                cursor.execute("""
                    INSERT INTO action_items (meeting_id, task, owner, due_date)
                    VALUES (?, ?, ?, ?)
                """, (
                    meeting_id,
                    action.get('task'),
                    action.get('owner'),
                    action.get('due_date')
                ))
            
            # Store decisions
            for decision in summary.get('decisions', []):
                cursor.execute("""
                    INSERT INTO decisions (meeting_id, decision, owner, context)
                    VALUES (?, ?, ?, ?)
                """, (
                    meeting_id,
                    decision.get('decision'),
                    decision.get('owner'),
                    decision.get('context')
                ))
            
            self.conn.commit()
            print(f"✓ Stored meeting in database (ID: {meeting_id})")
            return meeting_id
            
        except Exception as e:
            print(f"Error storing meeting: {e}")
            return None
    
    def sync_to_google(self, meeting_id: int, summary: Dict[str, Any], create_followup: bool = True):
        """Sync meeting data to Google Calendar and Tasks."""
        if not self.google:
            print("⚠ Google integration not available")
            return
        
        synced_count = 0
        
        # Create tasks for action items
        for action in summary.get('action_items', []):
            task_title = action.get('task', '')
            owner = action.get('owner', '')
            due_date_str = action.get('due_date')
            
            # Parse due date
            due_date = None
            if due_date_str:
                try:
                    # Try to parse common date formats
                    for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%B %d', '%b %d']:
                        try:
                            due_date = datetime.strptime(due_date_str, fmt)
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass
            
            # Create task
            notes = f"Owner: {owner}\nFrom meeting: {summary.get('tldr', '')}"
            task = self.google.create_task(
                title=task_title,
                notes=notes,
                due_date=due_date
            )
            
            if task:
                # Update database with Google task ID
                try:
                    cursor = self.conn.cursor()
                    cursor.execute("""
                        UPDATE action_items
                        SET google_task_id = ?
                        WHERE meeting_id = ? AND task = ?
                    """, (task['id'], meeting_id, task_title))
                    self.conn.commit()
                    synced_count += 1
                except Exception as e:
                    print(f"Error updating task ID: {e}")
        
        # Create follow-up meeting if requested
        if create_followup and summary.get('action_items'):
            followup_time = datetime.now() + timedelta(days=7)
            
            # Build description with action items
            description_parts = [summary.get('tldr', ''), "\n\nAction Items to Review:"]
            for action in summary.get('action_items', []):
                owner = action.get('owner', 'N/A')
                description_parts.append(f"• {action.get('task')} (Owner: {owner})")
            
            event = self.google.create_calendar_event(
                summary=f"Follow-up: {summary.get('tldr', 'Meeting')[:50]}",
                description="\n".join(description_parts),
                start_time=followup_time,
                duration_minutes=30
            )
            
            if event:
                # Store in database
                try:
                    cursor = self.conn.cursor()
                    cursor.execute("""
                        INSERT INTO calendar_events (meeting_id, google_event_id, summary, start_time)
                        VALUES (?, ?, ?, ?)
                    """, (meeting_id, event['id'], event['summary'], followup_time.isoformat()))
                    self.conn.commit()
                    synced_count += 1
                except Exception as e:
                    print(f"Error storing calendar event: {e}")
        
        print(f"✓ Synced {synced_count} items to Google")
    
    def get_context_from_db(self, max_meetings: int = 3) -> str:
        """Retrieve context from previous meetings."""
        if not self.conn:
            return "No previous meeting context available."
        
        try:
            cursor = self.conn.cursor()
            
            # Get recent meetings
            cursor.execute("""
                SELECT id, timestamp, tldr, summary_json
                FROM meetings
                WHERE thread_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (self.thread_id, max_meetings))
            
            meetings = cursor.fetchall()
            
            if not meetings:
                return "No previous meeting context available."
            
            context_parts = [f"PREVIOUS {len(meetings)} MEETINGS:"]
            
            for i, meeting in enumerate(reversed(meetings), 1):
                context_parts.append(f"\nMeeting {i} ({meeting['timestamp'][:10]}):")
                context_parts.append(f"  Summary: {meeting['tldr']}")
            
            # Get recent action items
            cursor.execute("""
                SELECT task, owner, due_date
                FROM action_items
                WHERE meeting_id IN (
                    SELECT id FROM meetings WHERE thread_id = ?
                )
                ORDER BY created_at DESC
                LIMIT 5
            """, (self.thread_id,))
            
            actions = cursor.fetchall()
            if actions:
                context_parts.append(f"\n\nRECENT ACTION ITEMS:")
                for action in actions:
                    owner = action['owner'] or 'N/A'
                    context_parts.append(f"  - {action['task']} (Owner: {owner})")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return "Error retrieving previous meeting context."
    
    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API."""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def summarize(
        self,
        transcript: str,
        use_context: bool = True,
        sync_google: bool = True,
        create_followup: bool = True
    ) -> Dict[str, Any]:
        """Summarize meeting with context from previous meetings and Google sync."""
        start_time = time.time()
        
        # Get context from database
        context_section = ""
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
        
        prompt = f"""{context_section}
You are an expert meeting summarizer. Analyze this meeting transcript and extract key information.

CURRENT MEETING TRANSCRIPT:
{transcript}

INSTRUCTIONS:
Extract the following information and return it as valid JSON with these exact fields:

1. "tldr": A concise 2-3 sentence summary of the meeting
2. "context_connections": Array of connections to previous meetings (if context provided), each with:
   - "connection": Description of the connection
   - "reference": What it refers to from previous meetings
3. "decisions": Array of decisions made, each with:
   - "decision": The decision made
   - "owner": Person responsible (if mentioned, otherwise null)
   - "context": Brief context explaining why
4. "action_items": Array of action items, each with:
   - "task": What needs to be done
   - "owner": Who is responsible (if mentioned, otherwise null)
   - "due_date": When it's due (if mentioned, otherwise null)
5. "risks": Array of risks or blockers identified (just strings)
6. "key_points": Array of main discussion points (strings)

Return ONLY the JSON object, no other text.
"""
        
        try:
            response_text = self._call_gemini(prompt)
            
            # Parse response
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            response_text = response_text.strip()
            
            try:
                summary = json.loads(response_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    summary = json.loads(json_match.group())
                else:
                    raise
            
            # Ensure all required fields
            summary.setdefault('tldr', 'No summary available')
            summary.setdefault('context_connections', [])
            summary.setdefault('decisions', [])
            summary.setdefault('action_items', [])
            summary.setdefault('risks', [])
            summary.setdefault('key_points', [])
            
            # Store in database
            meeting_id = self.store_meeting_in_db(summary, transcript)
            
            # Sync to Google if enabled
            if sync_google and meeting_id and self.google:
                self.sync_to_google(meeting_id, summary, create_followup)
            
            latency_ms = (time.time() - start_time) * 1000
            self.metrics["total_requests"] += 1
            self.metrics["total_latency_ms"] += latency_ms
            
            return {
                "success": True,
                "summary": summary,
                "meeting_id": meeting_id,
                "latency_ms": latency_ms,
                "timestamp": datetime.now().isoformat(),
                "used_context": use_context and "No previous" not in context_summary if use_context else False,
                "synced_to_google": sync_google and self.google is not None
            }
            
        except Exception as e:
            print(f"Error during summarization: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    def cleanup(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Demo: Analyze sample meetings with context awareness and Google sync."""
    print("\n" + "=" * 80)
    print("MEETING AGENT WITH GOOGLE CALENDAR & TASKS INTEGRATION")
    print("=" * 80)
    
    # Initialize agent (set enable_google=False to skip Google auth)
    agent = MCPMeetingAgent(thread_id="q4_planning", enable_google=True)
    
    # Read sample transcripts
    sample_files = [
        "data/transcripts/sample_001.txt",
        "data/transcripts/sample_002.txt",
        "data/transcripts/sample_003.txt"
    ]
    
    for i, file_path in enumerate(sample_files, 1):
        if not os.path.exists(file_path):
            print(f"\n⚠ Sample file not found: {file_path}")
            print(f"   Create sample transcripts in {os.path.dirname(file_path)}/")
            continue
        
        print(f"\n{'='*80}")
        print(f"MEETING {i}: {os.path.basename(file_path)}")
        print(f"{'='*80}")
        
        with open(file_path, 'r') as f:
            transcript = f.read()
        
        print(f"Transcript length: {len(transcript.split())} words")
        
        # Summarize with context (use context only after first meeting)
        # Set sync_google=True to create Google Tasks and Calendar events
        result = agent.summarize(
            transcript,
            use_context=(i > 1),
            sync_google=True,  # Enable Google sync
            create_followup=True  # Create follow-up meeting
        )
        
        if result["success"]:
            summary = result['summary']
            print(f"\n✓ Summarized in {result['latency_ms']:.0f}ms")
            print(f"  Used context: {result['used_context']}")
            print(f"  Synced to Google: {result['synced_to_google']}")
            print(f"  Meeting ID: {result['meeting_id']}")
            
            print(f"\nTL;DR:")
            print(f"  {summary['tldr']}")
            
            if summary.get('context_connections'):
                print(f"\nContext Connections ({len(summary['context_connections'])}):")
                for conn in summary['context_connections']:
                    print(f"  - {conn.get('connection')}")
            
            if summary.get('decisions'):
                print(f"\nDecisions ({len(summary['decisions'])}):")
                for d in summary['decisions'][:3]:
                    owner = d.get('owner', 'N/A')
                    print(f"  - {d.get('decision')} (Owner: {owner})")
            
            if summary.get('action_items'):
                print(f"\nAction Items ({len(summary['action_items'])}):")
                for a in summary['action_items'][:3]:
                    owner = a.get('owner', 'N/A')
                    due = a.get('due_date', 'N/A')
                    print(f"  - {a.get('task')} (Owner: {owner}, Due: {due})")
                    if result['synced_to_google']:
                        print(f"    → Synced to Google Tasks")
            
            if summary.get('risks'):
                print(f"\nRisks ({len(summary['risks'])}):")
                for risk in summary['risks']:
                    print(f"  - {risk}")
        else:
            print(f"\n✗ Error: {result['error']}")
        
        # Small delay between requests
        if i < len(sample_files):
            time.sleep(1)
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total meetings processed: {agent.metrics['total_requests']}")
    if agent.metrics['total_requests'] > 0:
        avg_latency = agent.metrics['total_latency_ms'] / agent.metrics['total_requests']
        print(f"Average latency: {avg_latency:.0f}ms")
    print(f"Database: {agent.db_path}")
    print(f"Thread: {agent.thread_id}")
    print(f"Google integration: {'Enabled' if agent.google else 'Disabled'}")
    
    # Cleanup
    agent.cleanup()
    
    print(f"\n{'='*80}")
    print("✓ Demo complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()