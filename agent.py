import os
import json
import time
import google.generativeai as genai
from typing import Dict, Any, List
from datetime import datetime

# Load API key
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


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
        
        # Initialize tool data storage
        self.calendar_events = []
        self.tasks = []
        
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
    
    # ==================== CALENDAR TOOL ====================
    def add_calendar_event(self, title: str, date: str, time: str = None, 
                          attendees: List[str] = None, description: str = None) -> Dict[str, Any]:
        """Add an event to the calendar."""
        event = {
            "id": len(self.calendar_events) + 1,
            "title": title,
            "date": date,
            "time": time,
            "attendees": attendees or [],
            "description": description,
            "created_at": datetime.now().isoformat()
        }
        self.calendar_events.append(event)
        self.metrics["total_tool_calls"] += 1
        return {"success": True, "event": event}
    
    def get_calendar_events(self, date: str = None, attendee: str = None) -> Dict[str, Any]:
        """Retrieve calendar events, optionally filtered by date or attendee."""
        events = self.calendar_events
        
        if date:
            events = [e for e in events if e["date"] == date]
        if attendee:
            events = [e for e in events if attendee in e.get("attendees", [])]
        
        self.metrics["total_tool_calls"] += 1
        return {"success": True, "events": events, "count": len(events)}
    
    def delete_calendar_event(self, event_id: int) -> Dict[str, Any]:
        """Delete a calendar event by ID."""
        for i, event in enumerate(self.calendar_events):
            if event["id"] == event_id:
                deleted_event = self.calendar_events.pop(i)
                self.metrics["total_tool_calls"] += 1
                return {"success": True, "deleted_event": deleted_event}
        
        return {"success": False, "error": f"Event {event_id} not found"}
    
    # ==================== TASK TRACKER TOOL ====================
    def create_task(self, title: str, owner: str = None, due_date: str = None,
                   priority: str = "medium", description: str = None) -> Dict[str, Any]:
        """Create a new task in the task tracker."""
        task = {
            "id": len(self.tasks) + 1,
            "title": title,
            "owner": owner,
            "due_date": due_date,
            "priority": priority,
            "status": "pending",
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.tasks.append(task)
        self.metrics["total_tool_calls"] += 1
        return {"success": True, "task": task}
    
    def update_task(self, task_id: int, **kwargs) -> Dict[str, Any]:
        """Update an existing task. Accepts any task field as keyword argument."""
        for task in self.tasks:
            if task["id"] == task_id:
                for key, value in kwargs.items():
                    if key in task:
                        task[key] = value
                task["updated_at"] = datetime.now().isoformat()
                self.metrics["total_tool_calls"] += 1
                return {"success": True, "task": task}
        
        return {"success": False, "error": f"Task {task_id} not found"}
    
    def get_tasks(self, owner: str = None, status: str = None, priority: str = None) -> Dict[str, Any]:
        """Retrieve tasks, optionally filtered by owner, status, or priority."""
        tasks = self.tasks
        
        if owner:
            tasks = [t for t in tasks if t.get("owner") == owner]
        if status:
            tasks = [t for t in tasks if t.get("status") == status]
        if priority:
            tasks = [t for t in tasks if t.get("priority") == priority]
        
        self.metrics["total_tool_calls"] += 1
        return {"success": True, "tasks": tasks, "count": len(tasks)}
    
    def mark_task_complete(self, task_id: int) -> Dict[str, Any]:
        """Mark a task as complete."""
        return self.update_task(task_id, status="completed")
    
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
    
    sample_transcript = """
    Alice: Let's start the Q4 planning meeting. We need to prioritize features.
    
    Bob: I think we should focus on the mobile app. Users have been requesting it.
    
    Alice: Good point. Bob, can you lead the mobile app project?
    
    Bob: Yes, I'll create a spec by next Friday.
    
    Carol: We also need to implement SSO for enterprise customers.
    
    Alice: That's critical. Carol, you own SSO. Target is November 30th.
    
    Carol: Got it. I'll need David's help on backend.
    
    David: Happy to help. I see a risk though - our auth service is outdated.
    
    Alice: Let's address that. David, audit the auth service this week.
    """
    
    print("Testing Gemini agent")
    result = agent.summarize(sample_transcript)
    
    if result["success"]:
        print("MEETING SUMMARY")
        print("=" * 80)
        print(json.dumps(result["summary"], indent=2))
        print(f"\nProcessing time: {result['latency_ms']:.0f}ms")
    else:
        print(f"Error: {result['error']}")
    
    # Demo: Using the calendar and task tracker tools
    print("\n\nDEMO: Calendar & Task Tracker Tools")
    print("=" * 80)
    
    # Add calendar event
    event = agent.add_calendar_event(
        title="Q4 Planning Follow-up",
        date="2025-10-25",
        time="2:00 PM",
        attendees=["Alice", "Bob", "Carol"],
        description="Follow-up meeting for Q4 planning"
    )
    print(f"✓ Created event: {event['event']['title']}")
    
    # Create tasks from action items
    task1 = agent.create_task(
        title="Create mobile app spec",
        owner="Bob",
        due_date="Friday",
        priority="high"
    )
    print(f"✓ Created task: {task1['task']['title']}")
    
    task2 = agent.create_task(
        title="Audit auth service",
        owner="David",
        due_date="This week",
        priority="high"
    )
    print(f"✓ Created task: {task2['task']['title']}")
    
    # Get all tasks
    all_tasks = agent.get_tasks()
    print(f"\nTotal tasks: {all_tasks['count']}")
    
    # Mark task complete
    agent.mark_task_complete(task1['task']['id'])
    print(f"✓ Marked task {task1['task']['id']} as complete")