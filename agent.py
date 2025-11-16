import os
import json
import time
import google.generativeai as genai
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import re

# Load API key
from dotenv import load_dotenv
load_dotenv()

# Google API imports for Calendar and Tasks
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-live")

# Google API configuration
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "client_secret_130532461983-u14cum0vnpc454no2n5k736uj60m203d.apps.googleusercontent.com.json")
GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.json")


class MeetingAgent:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        
        self.metrics = {
            "total_requests": 0,
            "total_latency_ms": 0,
            "total_tool_calls": 0
        }
        
        self._check_gemini()
    
    def _check_gemini(self):
        try:
            # Test the Gemini API with a simple request
            response = self.model.generate_content("Hello")
            if response.text:
                print(f"✓ Gemini {GEMINI_MODEL} is working")
            else:
                raise Exception("No response from Gemini")
        except Exception as e:
            print(f"Error connecting to Gemini: {str(e)}")
            raise
    
    def _call_gemini(self, prompt: str) -> str:
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    # ==================== GOOGLE API HELPERS ====================
    
    def _get_google_credentials(self):
        """Get authenticated Google credentials with all required scopes."""
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
        """Get authenticated Google Calendar service."""
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
        """Parse natural language dates and convert to RFC 3339 format for Google Tasks.
        
        Args:
            date_str: Natural language date like "next Friday", "November 30th", "this week", "2025-11-30"
            
        Returns:
            RFC 3339 formatted date string like "2025-11-30T00:00:00.000Z"
        """
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
        
        # Try parsing with dateutil for dates like "November 30th", "Nov 30", "2025-11-30"
        try:
            parsed_date = date_parser.parse(date_str, default=now)
            # If year wasn't specified and the date is in the past, assume next year
            if parsed_date < now and date_str_lower.count('20') == 0:
                parsed_date = parsed_date.replace(year=now.year + 1)
            return parsed_date.strftime("%Y-%m-%dT00:00:00.000Z")
        except (ValueError, TypeError):
            pass
        
        # If all parsing fails, return None
        return None
    
    # ==================== CALENDAR TOOL ====================
    
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
    
    # ==================== TASK TRACKER TOOL ====================
    
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
            
            # Add due date if provided, parse natural language dates
            if due_date:
                parsed_date = self._parse_date_for_tasks(due_date)
                if parsed_date:
                    task['due'] = parsed_date
                # If parsing fails, we skip the due date rather than causing an error
            
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
    
    # ==================== MEETING SUMMARIZER ====================
    
    def summarize(self, transcript: str, focus_areas: List[str] = None) -> Dict[str, Any]:
        if focus_areas is None:
            focus_areas = ["decisions", "action_items"]
        
        start_time = time.time()
        prompt = f"""You are an expert meeting summarizer. Analyze this meeting transcript and extract key information.

TRANSCRIPT:
{transcript}

INSTRUCTIONS:
Extract the following information and return it as valid JSON with these exact fields:

1. "tldr": A concise 2-3 sentence summary of the meeting
2. "decisions": Array of decisions made, each with:
   - "decision": The decision made
   - "owner": Person responsible (if mentioned, otherwise null)
   - "context": Brief context explaining why
3. "action_items": Array of action items, each with:
   - "task": What needs to be done
   - "owner": Who is responsible (if mentioned, otherwise null)
   - "due_date": When it's due (if mentioned, otherwise null)
4. "risks": Array of risks or blockers identified (just strings)
5. "key_points": Array of main discussion points (strings)

Return ONLY the JSON object, no other text. Make sure the JSON is valid and properly formatted.

Example format:
{{
  "tldr": "Team discussed Q4 priorities...",
  "decisions": [{{"decision": "Prioritize mobile app", "owner": "Bob", "context": "User demand"}}],
  "action_items": [{{"task": "Create spec", "owner": "Bob", "due_date": "Friday"}}],
  "risks": ["Budget constraints"],
  "key_points": ["Q4 planning", "Resource allocation"]
}}"""

        try:
            response_text = self._call_gemini(prompt)
            
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
            summary.setdefault('decisions', [])
            summary.setdefault('action_items', [])
            summary.setdefault('risks', [])
            summary.setdefault('key_points', [])
            
            latency_ms = (time.time() - start_time) * 1000
            self.metrics["total_requests"] += 1
            self.metrics["total_latency_ms"] += latency_ms
            self.metrics["total_tool_calls"] += 0  # Phase 1: no tools
            
            return {
                "success": True,
                "summary": summary,
                "latency_ms": latency_ms,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error during summarization: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "latency_ms": (time.time() - start_time) * 1000
            }
    
    def get_metrics(self) -> Dict[str, Any]:
        avg_latency = (
            self.metrics["total_latency_ms"] / self.metrics["total_requests"]
            if self.metrics["total_requests"] > 0 else 0
        )
        
        return {
            "total_requests": self.metrics["total_requests"],
            "avg_latency_ms": avg_latency
        }


if __name__ == "__main__":
    agent = MeetingAgent()
    sample_transcript_path = "samples/sample_transcript.txt"
    if os.path.exists(sample_transcript_path):
        try:
            with open(sample_transcript_path, "r") as fh:
                sample_transcript = fh.read()
        except Exception:
            sample_transcript = None
    print("Testing Gemini agent with Google Calendar and Tasks integration")
    print("=" * 80)
    result = agent.summarize(sample_transcript)
    
    if result["success"]:
        print("\nMEETING SUMMARY")
        print("=" * 80)
        print(json.dumps(result["summary"], indent=2))
        print(f"\nProcessing time: {result['latency_ms']:.0f}ms")
    else:
        print(f"Error: {result['error']}")
    
    # Demo: Using the calendar and task tracker tools
    print("\n\nDEMO: Calendar & Task Tracker Tools")
    print("=" * 80)
    
    # Add calendar event
    print("\n1. Creating calendar event...")
    event = agent.add_calendar_event(
        title="Q4 Planning Follow-up",
        date="2025-10-25",
        time="2:00 PM",
        attendees=["alice@example.com", "bob@example.com"],
        description="Follow-up meeting for Q4 planning"
    )
    if event.get('success'):
        print(f"   ✓ Created event: {event['event']['summary']}")
        print(f"   Event ID: {event['event']['id']}")
    else:
        print(f"   ✗ Failed to create event: {event.get('error', 'Unknown error')}")
    
    # Create tasks from action items
    print("\n2. Creating tasks from action items...")
    task1 = agent.create_task(
        title="Create mobile app spec",
        owner="Bob",
        due_date="Friday",
        priority="high",
        description="Create detailed specification for mobile app project"
    )
    if task1.get('success'):
        print(f"   ✓ Created task: {task1['task']['title']}")
        print(f"   Task ID: {task1['task']['id']}")
    else:
        print(f"   ✗ Failed to create task: {task1.get('error', 'Unknown error')}")
    
    task2 = agent.create_task(
        title="Audit auth service",
        owner="David",
        due_date="This week",
        priority="high",
        description="Security audit of authentication service"
    )
    if task2.get('success'):
        print(f"   ✓ Created task: {task2['task']['title']}")
        print(f"   Task ID: {task2['task']['id']}")
    else:
        print(f"   ✗ Failed to create task: {task2.get('error', 'Unknown error')}")
    
    # Get all tasks
    print("\n3. Retrieving all tasks...")
    all_tasks = agent.get_tasks()
    if all_tasks.get('success'):
        print(f"   ✓ Total tasks: {all_tasks['count']}")
        for task in all_tasks['tasks'][:3]:  # Show first 3
            print(f"   - {task.get('title', 'Untitled')}: {task.get('status', 'unknown')}")
    else:
        print(f"   ✗ Failed to get tasks: {all_tasks.get('error', 'Unknown error')}")
    
    # Mark task complete (if task1 was created successfully)
    if task1.get('success'):
        print("\n4. Marking task as complete...")
        result = agent.mark_task_complete(task1['task']['id'])
        if result.get('success'):
            print(f"   ✓ Marked task complete: {task1['task']['title']}")
        else:
            print(f"   ✗ Failed to mark task complete: {result.get('error', 'Unknown error')}")
    
    # Get calendar events
    print("\n5. Retrieving calendar events for today...")
    from datetime import date
    today = date.today().isoformat()
    events = agent.get_calendar_events(date=today)
    if events.get('success'):
        print(f"   ✓ Found {events['count']} events")
        for event in events['events'][:3]:  # Show first 3
            print(f"   - {event.get('summary', 'Untitled')}")
    else:
        print(f"   ✗ Failed to get events: {events.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print("✓ Demo complete!")
    print("\nMetrics:")
    metrics = agent.get_metrics()
    print(f"  Total requests: {metrics['total_requests']}")
    print(f"  Avg latency: {metrics['avg_latency_ms']:.0f}ms")
    print(f"  Tool calls: {agent.metrics['total_tool_calls']}")