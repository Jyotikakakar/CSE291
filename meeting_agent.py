#!/usr/bin/env python3
"""
Meeting Agent with context-aware summarization, local storage, and Google integration.
"""
import os
import json
import time
import sqlite3
import google.generativeai as genai
from typing import Dict, Any
from datetime import datetime, timedelta

from config import GEMINI_API_KEY, GEMINI_MODEL
from google_integration import GoogleIntegration


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

