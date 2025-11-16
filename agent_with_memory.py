import os
import json
import time
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import re
import pickle

from dotenv import load_dotenv
load_dotenv()

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-live")

GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "client_secret_130532461983-u14cum0vnpc454no2n5k736uj60m203d.apps.googleusercontent.com.json")
GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.json")

MEMORY_STORAGE_PATH = os.getenv("MEMORY_STORAGE_PATH", "memory_store")


class ConversationMemory:
    """Manages conversation history and context across multiple meetings with thread support."""
    
    def __init__(self, storage_path: str = MEMORY_STORAGE_PATH, thread_id: str = "default"):
        self.thread_id = thread_id
        self.storage_path = os.path.join(storage_path, thread_id)
        os.makedirs(self.storage_path, exist_ok=True)
        
        self.conversation_history: List[Dict[str, str]] = []
        self.meeting_summaries: List[Dict[str, Any]] = []
        self.persistent_context: Dict[str, Any] = {
            "ongoing_projects": [],
            "key_people": [],
            "recurring_topics": [],
            "action_items_history": [],
            "decisions_history": []
        }
        
        # Load existing memory if available
        self._load_memory()
    
    def _load_memory(self):
        """Load persistent memory from disk."""
        memory_file = os.path.join(self.storage_path, "persistent_memory.pkl")
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'rb') as f:
                    data = pickle.load(f)
                    self.persistent_context = data.get('persistent_context', self.persistent_context)
                    self.meeting_summaries = data.get('meeting_summaries', [])
                print(f"✓ Loaded memory: {len(self.meeting_summaries)} previous meetings")
            except Exception as e:
                print(f"Warning: Could not load memory: {e}")
    
    def _save_memory(self):
        memory_file = os.path.join(self.storage_path, "persistent_memory.pkl")
        try:
            with open(memory_file, 'wb') as f:
                pickle.dump({
                    'persistent_context': self.persistent_context,
                    'meeting_summaries': self.meeting_summaries
                }, f)
            
            json_file = os.path.join(self.storage_path, "persistent_memory.json")
            with open(json_file, 'w') as f:
                json.dump({
                    'persistent_context': self.persistent_context,
                    'meeting_summaries': self.meeting_summaries
                }, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save memory: {e}")
    
    def add_meeting_summary(self, summary: Dict[str, Any], transcript: str):
        meeting_record = {
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "transcript_preview": transcript[:500]  # Store preview for context
        }
        
        self.meeting_summaries.append(meeting_record)
        self._update_persistent_context(summary)
        
        # Keep only last 20 meetings in memory 
        if len(self.meeting_summaries) > 20:
            self.meeting_summaries = self.meeting_summaries[-20:]
        
        self._save_memory()
    
    def _update_persistent_context(self, summary: Dict[str, Any]):
       
        for action in summary.get('action_items', []):
            self.persistent_context['action_items_history'].append({
                "task": action.get('task'),
                "owner": action.get('owner'),
                "due_date": action.get('due_date'),
                "timestamp": datetime.now().isoformat()
            })
        
        for decision in summary.get('decisions', []):
            self.persistent_context['decisions_history'].append({
                "decision": decision.get('decision'),
                "owner": decision.get('owner'),
                "context": decision.get('context'),
                "timestamp": datetime.now().isoformat()
            })
        
        for action in summary.get('action_items', []):
            owner = action.get('owner')
            if owner and owner not in self.persistent_context['key_people']:
                self.persistent_context['key_people'].append(owner)
        
        if len(self.persistent_context['action_items_history']) > 100:
            self.persistent_context['action_items_history'] = \
                self.persistent_context['action_items_history'][-100:]
        
        if len(self.persistent_context['decisions_history']) > 50:
            self.persistent_context['decisions_history'] = \
                self.persistent_context['decisions_history'][-50:]
    
    def get_context_summary(self, max_meetings: int = 5) -> str:
        if not self.meeting_summaries:
            return "No previous meeting context available."
        
        context_parts = []
        
        # Recent meetings summary
        recent_meetings = self.meeting_summaries[-max_meetings:]
        context_parts.append(f"PREVIOUS {len(recent_meetings)} MEETINGS CONTEXT:")
        
        for i, meeting in enumerate(recent_meetings, 1):
            summary = meeting['summary']
            context_parts.append(f"\nMeeting {i} ({meeting['timestamp'][:10]}):")
            context_parts.append(f"  Summary: {summary.get('tldr', 'N/A')}")
            
            if summary.get('decisions'):
                context_parts.append(f"  Key Decisions: {len(summary['decisions'])}")
            if summary.get('action_items'):
                context_parts.append(f"  Action Items: {len(summary['action_items'])}")
        
        # Ongoing action items
        recent_actions = self.persistent_context['action_items_history'][-10:]
        if recent_actions:
            context_parts.append(f"\n\nRECENT ACTION ITEMS ({len(recent_actions)}):")
            for action in recent_actions:
                context_parts.append(f"  - {action['task']} (Owner: {action.get('owner', 'N/A')})")
        
        # Key people
        if self.persistent_context['key_people']:
            context_parts.append(f"\n\nKEY PEOPLE INVOLVED:")
            context_parts.append(f"  {', '.join(self.persistent_context['key_people'][:10])}")
        
        return "\n".join(context_parts)
    
    def add_conversation_turn(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "parts": [content]
        })
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        return self.conversation_history
    
    def clear_conversation(self):
        self.conversation_history = []
    
    def reset_all_memory(self):
        self.conversation_history = []
        self.meeting_summaries = []
        self.persistent_context = {
            "ongoing_projects": [],
            "key_people": [],
            "recurring_topics": [],
            "action_items_history": [],
            "decisions_history": []
        }
        self._save_memory()


class MeetingAgent:
    def __init__(self, use_memory: bool = True, thread_id: str = "default"):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Initialize memory system with thread support
        self.use_memory = use_memory
        self.thread_id = thread_id
        self.memory = ConversationMemory(thread_id=thread_id) if use_memory else None
        
        self.metrics = {
            "total_requests": 0,
            "total_latency_ms": 0,
            "total_tool_calls": 0
        }
        
        self._check_gemini()
    
    def _check_gemini(self):
        try:
            response = self.model.generate_content("Hello")
            if response.text:
                print(f"✓ Gemini {GEMINI_MODEL} is working")
                if self.use_memory:
                    print(f"✓ Memory system enabled")
            else:
                raise Exception("No response from Gemini")
        except Exception as e:
            print(f"Error connecting to Gemini: {str(e)}")
            raise
    
    def _call_gemini_with_context(self, prompt: str) -> str:
        try:
            if self.use_memory and self.memory.conversation_history:
                # Use chat with history
                chat = self.model.start_chat(history=self.memory.conversation_history)
                response = chat.send_message(prompt)
                return response.text
            else:
                # Simple generation without history
                response = self.model.generate_content(prompt)
                return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    def _call_gemini(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    
    def _get_google_credentials(self):
        SCOPES = [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/tasks'
        ]
        creds = None
        
        if os.path.exists(GOOGLE_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_PATH, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
                    print(f"Warning: Google credentials file not found at {GOOGLE_CREDENTIALS_PATH}")
                    print("Tools will not be available. Set GOOGLE_CREDENTIALS_PATH environment variable.")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(
                    GOOGLE_CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(GOOGLE_TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        
        return creds
    
    def _get_calendar_service(self):
        creds = self._get_google_credentials()
        if not creds:
            return None
        return build('calendar', 'v3', credentials=creds)
    
    def _get_tasks_service(self):
        """Get authenticated Google Tasks service."""
        creds = self._get_google_credentials()
        if not creds:
            return None
        return build('tasks', 'v1', credentials=creds)
    
    def _parse_time(self, time_str: str) -> str:
        """Convert time string to 24-hour format HH:MM:SS."""
        if not time_str:
            return "09:00:00"
        
        # If already in HH:MM:SS format, return as is
        if ':' in time_str and ('AM' not in time_str.upper() and 'PM' not in time_str.upper()):
            parts = time_str.split(':')
            if len(parts) == 2:
                return f"{time_str}:00"
            return time_str
        
        # Parse 12-hour format (e.g., "2:00 PM")
        try:
            dt = datetime.strptime(time_str.strip(), "%I:%M %p")
            return dt.strftime("%H:%M:%S")
        except ValueError:
            try:
                dt = datetime.strptime(time_str.strip(), "%I %p")
                return dt.strftime("%H:%M:%S")
            except ValueError:
                return "09:00:00"  # Default fallback
    
    def _parse_date_for_tasks(self, date_str: str) -> str:
        """Parse natural language dates and convert to RFC 3339 format for Google Tasks."""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        now = datetime.now()
        
        # Handle relative dates
        date_str_lower = date_str.lower()
        
        # "this week" - end of this week (Friday)
        if "this week" in date_str_lower:
            days_until_friday = (4 - now.weekday()) % 7
            if days_until_friday == 0:
                days_until_friday = 7
            target_date = now + timedelta(days=days_until_friday)
            return target_date.strftime("%Y-%m-%dT00:00:00.000Z")
        
        # "next week" - next Monday
        if "next week" in date_str_lower:
            days_until_monday = (7 - now.weekday()) % 7 + 7
            target_date = now + timedelta(days=days_until_monday)
            return target_date.strftime("%Y-%m-%dT00:00:00.000Z")
        
        # "next [day of week]"
        if "next" in date_str_lower:
            weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            for i, day in enumerate(weekdays):
                if day in date_str_lower:
                    days_ahead = i - now.weekday()
                    if days_ahead <= 0:  # Target day already happened this week
                        days_ahead += 7
                    target_date = now + timedelta(days=days_ahead)
                    return target_date.strftime("%Y-%m-%dT00:00:00.000Z")
        
        # Try parsing with dateutil
        try:
            parsed_date = date_parser.parse(date_str, default=now)
            # If year wasn't specified and the date is in the past, assume next year
            if parsed_date < now and date_str_lower.count('20') == 0:
                parsed_date = parsed_date.replace(year=now.year + 1)
            return parsed_date.strftime("%Y-%m-%dT00:00:00.000Z")
        except (ValueError, TypeError):
            pass
        
        return None
    
    
    def add_calendar_event(self, title: str, date: str, time: str = None, 
                          attendees: List[str] = None, description: str = None) -> Dict[str, Any]:
        """Add an event to Google Calendar."""
        try:
            service = self._get_calendar_service()
            if not service:
                return {"success": False, "error": "Google Calendar service not available"}
            
            # Parse date and time
            start_time = self._parse_time(time)
            # Calculate end time (1 hour later)
            start_hour = int(start_time.split(':')[0])
            end_hour = (start_hour + 1) % 24
            end_time = f"{end_hour:02d}:{start_time.split(':')[1]}:{start_time.split(':')[2]}"
            
            start_datetime = f"{date}T{start_time}"
            end_datetime = f"{date}T{end_time}"
            
            event = {
                'summary': title,
                'description': description or '',
                'start': {
                    'dateTime': start_datetime,
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'dateTime': end_datetime,
                    'timeZone': 'America/Los_Angeles',
                },
                'attendees': [{'email': email} for email in (attendees or []) if '@' in email],
            }
            
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            
            self.metrics["total_tool_calls"] += 1
            return {"success": True, "event": created_event}
            
        except HttpError as error:
            return {"success": False, "error": f"Calendar API error: {error}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_calendar_events(self, date: str = None, attendee: str = None) -> Dict[str, Any]:
        """Retrieve events from Google Calendar."""
        try:
            service = self._get_calendar_service()
            if not service:
                return {"success": False, "error": "Google Calendar service not available"}
            
            # Build time range filter
            time_min = f"{date}T00:00:00Z" if date else None
            time_max = f"{date}T23:59:59Z" if date else None
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Filter by attendee if specified
            if attendee:
                events = [e for e in events 
                         if any(attendee.lower() in attendee_info.get('email', '').lower() 
                               for attendee_info in e.get('attendees', []))]
            
            self.metrics["total_tool_calls"] += 1
            return {"success": True, "events": events, "count": len(events)}
            
        except HttpError as error:
            return {"success": False, "error": f"Calendar API error: {error}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_calendar_event(self, event_id: str) -> Dict[str, Any]:
        """Delete a calendar event by Google Calendar event ID."""
        try:
            service = self._get_calendar_service()
            if not service:
                return {"success": False, "error": "Google Calendar service not available"}
            
            service.events().delete(calendarId='primary', eventId=event_id).execute()
            
            self.metrics["total_tool_calls"] += 1
            return {"success": True, "deleted_event_id": event_id}
            
        except HttpError as error:
            return {"success": False, "error": f"Calendar API error: {error}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    
    def create_task(self, title: str, owner: str = None, due_date: str = None,
                   priority: str = "medium", description: str = None) -> Dict[str, Any]:
        """Create a new task in Google Tasks."""
        try:
            service = self._get_tasks_service()
            if not service:
                return {"success": False, "error": "Google Tasks service not available"}
            
            # Get the default task list
            tasklists = service.tasklists().list().execute()
            tasklist_id = tasklists['items'][0]['id']
            
            task = {
                'title': title,
                'notes': description or '',
                'status': 'needsAction'
            }
            
            # Add due date if provided
            if due_date:
                parsed_date = self._parse_date_for_tasks(due_date)
                if parsed_date:
                    task['due'] = parsed_date
            
            created_task = service.tasks().insert(tasklist=tasklist_id, body=task).execute()
            
            self.metrics["total_tool_calls"] += 1
            return {"success": True, "task": created_task}
            
        except HttpError as error:
            return {"success": False, "error": f"Tasks API error: {error}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_task(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """Update an existing task in Google Tasks."""
        try:
            service = self._get_tasks_service()
            if not service:
                return {"success": False, "error": "Google Tasks service not available"}
            
            tasklists = service.tasklists().list().execute()
            tasklist_id = tasklists['items'][0]['id']
            
            task = service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
            
            for key, value in kwargs.items():
                if key == 'status' and value == 'completed':
                    task['status'] = 'completed'
                elif key == 'title':
                    task['title'] = value
                elif key == 'notes':
                    task['notes'] = value
            
            updated_task = service.tasks().update(tasklist=tasklist_id, task=task_id, body=task).execute()
            
            self.metrics["total_tool_calls"] += 1
            return {"success": True, "task": updated_task}
            
        except HttpError as error:
            return {"success": False, "error": f"Tasks API error: {error}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_tasks(self, owner: str = None, status: str = None, priority: str = None) -> Dict[str, Any]:
        """Retrieve tasks from Google Tasks."""
        try:
            service = self._get_tasks_service()
            if not service:
                return {"success": False, "error": "Google Tasks service not available"}
            
            tasklists = service.tasklists().list().execute()
            tasklist_id = tasklists['items'][0]['id']
            
            tasks_result = service.tasks().list(tasklist=tasklist_id).execute()
            tasks = tasks_result.get('items', [])
            
            # Filter by status if specified
            if status:
                if status == 'completed':
                    tasks = [t for t in tasks if t.get('status') == 'completed']
                elif status == 'pending':
                    tasks = [t for t in tasks if t.get('status') == 'needsAction']
            
            self.metrics["total_tool_calls"] += 1
            return {"success": True, "tasks": tasks, "count": len(tasks)}
            
        except HttpError as error:
            return {"success": False, "error": f"Tasks API error: {error}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def mark_task_complete(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as complete."""
        return self.update_task(task_id, status="completed")
    
    
    def summarize(self, transcript: str, focus_areas: List[str] = None, 
                  use_context: bool = True) -> Dict[str, Any]:
        """
        Summarize meeting with memory/context from previous meetings.
        
        Args:
            transcript: Meeting transcript text
            focus_areas: Optional areas to focus on
            use_context: Whether to use context from previous meetings
        """
        if focus_areas is None:
            focus_areas = ["decisions", "action_items"]
        
        start_time = time.time()
        
        # Build context-aware prompt
        context_section = ""
        if self.use_memory and use_context:
            context_summary = self.memory.get_context_summary()
            context_section = f"""
PREVIOUS MEETING CONTEXT:
{context_summary}

IMPORTANT: Consider the context from previous meetings when analyzing this transcript.
- Reference any ongoing action items or decisions from previous meetings
- Identify connections between this meeting and previous discussions
- Note any updates on previously mentioned topics or tasks

"""
        
        prompt = f"""{context_section}You are an expert meeting summarizer. Analyze this meeting transcript and extract key information.

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
   - "related_to_previous": Boolean indicating if this relates to previous meetings
5. "risks": Array of risks or blockers identified (just strings)
6. "key_points": Array of main discussion points (strings)
7. "people_mentioned": Array of people mentioned in the meeting

Return ONLY the JSON object, no other text. Make sure the JSON is valid and properly formatted.

Example format:
{{
  "tldr": "Team discussed Q4 priorities...",
  "context_connections": [{{"connection": "Follow-up on mobile app from last meeting", "reference": "Previous decision to prioritize mobile"}}],
  "decisions": [{{"decision": "Prioritize mobile app", "owner": "Bob", "context": "User demand"}}],
  "action_items": [{{"task": "Create spec", "owner": "Bob", "due_date": "Friday", "related_to_previous": false}}],
  "risks": ["Budget constraints"],
  "key_points": ["Q4 planning", "Resource allocation"],
  "people_mentioned": ["Bob", "Alice", "Carol"]
}}"""

        try:
            # Use context-aware Gemini call if memory enabled
            if self.use_memory:
                response_text = self._call_gemini_with_context(prompt)
                # Store this conversation turn
                self.memory.add_conversation_turn("user", f"Analyze this meeting: {transcript[:200]}...")
                self.memory.add_conversation_turn("model", response_text)
            else:
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
            
            if not isinstance(summary, dict):
                raise ValueError("Response is not a dictionary")
            
            summary.setdefault('tldr', 'No summary available')
            summary.setdefault('context_connections', [])
            summary.setdefault('decisions', [])
            summary.setdefault('action_items', [])
            summary.setdefault('risks', [])
            summary.setdefault('key_points', [])
            summary.setdefault('people_mentioned', [])
            
            if self.use_memory:
                self.memory.add_meeting_summary(summary, transcript)
                print(f"✓ Stored meeting in memory (Total meetings: {len(self.memory.meeting_summaries)})")
            
            latency_ms = (time.time() - start_time) * 1000
            self.metrics["total_requests"] += 1
            self.metrics["total_latency_ms"] += latency_ms
            
            return {
                "success": True,
                "summary": summary,
                "latency_ms": latency_ms,
                "timestamp": datetime.now().isoformat(),
                "used_context": self.use_memory and use_context
            }
            
        except Exception as e:
            print(f"Error during summarization: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get a summary of what's in memory."""
        if not self.use_memory:
            return {"memory_enabled": False}
        
        return {
            "memory_enabled": True,
            "thread_id": self.thread_id,
            "total_meetings": len(self.memory.meeting_summaries),
            "key_people": self.memory.persistent_context['key_people'],
            "recent_action_items": len(self.memory.persistent_context['action_items_history']),
            "recent_decisions": len(self.memory.persistent_context['decisions_history'])
        }
    
    def clear_conversation_memory(self):
        """Clear conversation history but keep meeting summaries."""
        if self.use_memory:
            self.memory.clear_conversation()
            print("✓ Cleared conversation history")
    
    def reset_all_memory(self):
        """Reset all memory (use with caution)."""
        if self.use_memory:
            self.memory.reset_all_memory()
            print("✓ Reset all memory")
    
    def get_metrics(self) -> Dict[str, Any]:
        avg_latency = (
            self.metrics["total_latency_ms"] / self.metrics["total_requests"]
            if self.metrics["total_requests"] > 0 else 0
        )
        
        metrics = {
            "total_requests": self.metrics["total_requests"],
            "avg_latency_ms": avg_latency
        }
        
        if self.use_memory:
            metrics.update(self.get_memory_summary())
        
        return metrics


if __name__ == "__main__":
    # Demo with memory
    agent = MeetingAgent(use_memory=True)
    
    print("=" * 80)
    print("DEMO: Meeting Summarizer with Memory/Context Management")
    print("=" * 80)
    
    # First meeting
    meeting_1 = """
    Alice: Let's start the Q4 planning meeting. We need to prioritize features.
    
    Bob: I think we should focus on the mobile app. Users have been requesting it.
    
    Alice: Good point. Bob, can you lead the mobile app project?
    
    Bob: Yes, I'll create a spec by next Friday.
    
    Carol: We also need to implement SSO for enterprise customers.
    
    Alice: That's critical. Carol, you own SSO. Target is November 30th.
    """
    
    print("\nMEETING 1: Q4 Planning")
    print("-" * 80)
    result1 = agent.summarize(meeting_1)
    
    if result1["success"]:
        print(f"✓ Summarized in {result1['latency_ms']:.0f}ms")
        print(f"  TL;DR: {result1['summary']['tldr']}")
        print(f"  Decisions: {len(result1['summary']['decisions'])}")
        print(f"  Action Items: {len(result1['summary']['action_items'])}")
    
    # Second meeting - should reference first
    meeting_2 = """
    Alice: Status update on our Q4 initiatives.
    
    Bob: I've finished the mobile app spec we discussed. Ready for review.
    
    Alice: Excellent! Let's schedule a review for tomorrow.
    
    Carol: SSO implementation is underway. I'm 30% complete.
    
    David: I noticed a security concern with our auth service that might affect SSO.
    
    Alice: David, document that and share with Carol by end of day.
    """
    
    print("\n\nMEETING 2: Status Update (with context from Meeting 1)")
    print("-" * 80)
    result2 = agent.summarize(meeting_2, use_context=True)
    
    if result2["success"]:
        print(f"Summarized in {result2['latency_ms']:.0f}ms")
        print(f"  Used Context: {result2['used_context']}")
        print(f"  TL;DR: {result2['summary']['tldr']}")
        
        if result2['summary'].get('context_connections'):
            print(f"\n  Context Connections:")
            for conn in result2['summary']['context_connections']:
                print(f"    - {conn.get('connection')}")
    
    print("\n\nMEMORY SUMMARY")
    memory_info = agent.get_memory_summary()
    print(f"Total Meetings Stored: {memory_info.get('total_meetings', 0)}")
    print(f"Key People: {', '.join(memory_info.get('key_people', []))}")
    print(f"Recent Action Items: {memory_info.get('recent_action_items', 0)}")
    print(f"Recent Decisions: {memory_info.get('recent_decisions', 0)}")
    
    print("\n" + "=" * 80)
    print("Demo complete! Memory persisted to disk.")
    print(f"  Location: {MEMORY_STORAGE_PATH}/")