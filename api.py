#!/usr/bin/env python3
"""
Simple Flask API for Meeting Summarizer with Google Calendar and Tasks Integration
Single endpoint: /analyze - Takes transcript, creates summary, tasks, and calendar events
"""
import os
from datetime import datetime
from flask import Flask, request, jsonify
from agent import MeetingAgent

app = Flask(__name__)

# Initialize agent
agent = None

def get_agent():
    """Get or create the MeetingAgent instance"""
    global agent
    if agent is None:
        agent = MeetingAgent()
    return agent

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Meeting Summarizer with Google Integration"
    })

@app.route('/analyze', methods=['POST'])
def analyze_meeting():
    """
    Analyze meeting transcript and automatically create tasks and calendar events
    
    Request body:
    {
        "transcript": "Meeting transcript text...",
        "meeting_info": {  // Optional
            "title": "Follow-up Meeting",
            "date": "2025-10-30",
            "time": "2:00 PM",
            "attendees": ["email1@example.com", "email2@example.com"]
        }
    }
    
    Returns:
    {
        "success": true,
        "summary": { ... },
        "tasks_created": [ ... ],
        "calendar_event": { ... },
        "errors": [ ... ]
    }
    """
    data = request.json
    
    # Validate input
    if not data or 'transcript' not in data:
        return jsonify({
            "success": False,
            "error": "transcript field is required"
        }), 400
    
    transcript = data['transcript']
    meeting_info = data.get('meeting_info', {})
    
    try:
        agent = get_agent()
        
        # Step 1: Summarize the transcript with Gemini
        print(f"\n{'='*60}")
        print("ANALYZING MEETING TRANSCRIPT")
        print(f"{'='*60}")
        
        summary_result = agent.summarize(transcript)
        
        if not summary_result.get('success'):
            return jsonify({
                "success": False,
                "error": f"Summarization failed: {summary_result.get('error')}"
            }), 500
        
        summary = summary_result.get('summary', {})
        print(f"✓ Meeting summarized successfully")
        print(f"  - {len(summary.get('action_items', []))} action items found")
        print(f"  - {len(summary.get('decisions', []))} decisions identified")
        
        # Prepare response
        response = {
            "success": True,
            "summary": summary,
            "latency_ms": summary_result.get('latency_ms', 0),
            "tasks_created": [],
            "calendar_event": None,
            "errors": []
        }
        
        # Step 2: Create tasks from action items
        action_items = summary.get('action_items', [])
        
        if action_items:
            print(f"\n{'='*60}")
            print(f"CREATING TASKS ({len(action_items)} items)")
            print(f"{'='*60}")
            
            for idx, action in enumerate(action_items, 1):
                task_title = action.get('task', 'Untitled task')
                task_owner = action.get('owner')
                task_due = action.get('due_date')
                
                try:
                    task_result = agent.create_task(
                        title=task_title,
                        owner=task_owner,
                        due_date=task_due,
                        priority='high',
                        description=f"From meeting: {summary.get('tldr', 'Meeting summary')}"
                    )
                    
                    if task_result.get('success'):
                        task = task_result.get('task', {})
                        task_info = {
                            'id': task.get('id'),
                            'title': task.get('title'),
                            'owner': task_owner,
                            'due_date': task_due,
                            'status': task.get('status')
                        }
                        response['tasks_created'].append(task_info)
                        print(f"  [{idx}] ✓ Created: {task_title}")
                        if task_owner:
                            print(f"       Owner: {task_owner}")
                        if task_due:
                            print(f"       Due: {task_due}")
                    else:
                        error_msg = f"Failed to create task '{task_title}': {task_result.get('error')}"
                        response['errors'].append(error_msg)
                        print(f"  [{idx}] ✗ {error_msg}")
                        
                except Exception as e:
                    error_msg = f"Exception creating task '{task_title}': {str(e)}"
                    response['errors'].append(error_msg)
                    print(f"  [{idx}] ✗ {error_msg}")
        else:
            print("\nNo action items found - skipping task creation")
        
        # Step 3: Create calendar event if meeting info provided
        if meeting_info and meeting_info.get('date'):
            print(f"\n{'='*60}")
            print("CREATING CALENDAR EVENT")
            print(f"{'='*60}")
            
            try:
                event_result = agent.add_calendar_event(
                    title=meeting_info.get('title', 'Follow-up Meeting'),
                    date=meeting_info.get('date'),
                    time=meeting_info.get('time', '10:00 AM'),
                    attendees=meeting_info.get('attendees', []),
                    description=summary.get('tldr', 'Meeting follow-up')
                )
                
                if event_result.get('success'):
                    event = event_result.get('event', {})
                    response['calendar_event'] = {
                        'id': event.get('id'),
                        'title': event.get('summary'),
                        'date': meeting_info.get('date'),
                        'time': meeting_info.get('time'),
                        'link': event.get('htmlLink')
                    }
                    print(f"  ✓ Event created: {event.get('summary')}")
                    print(f"    Date: {meeting_info.get('date')} at {meeting_info.get('time')}")
                else:
                    error_msg = f"Failed to create calendar event: {event_result.get('error')}"
                    response['errors'].append(error_msg)
                    print(f"  ✗ {error_msg}")
                    
            except Exception as e:
                error_msg = f"Exception creating calendar event: {str(e)}"
                response['errors'].append(error_msg)
                print(f"  ✗ {error_msg}")
        else:
            print("\nNo meeting info provided - skipping calendar event creation")
        
        # Print summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Tasks created: {len(response['tasks_created'])}")
        print(f"Calendar event: {'Yes' if response['calendar_event'] else 'No'}")
        print(f"Errors: {len(response['errors'])}")
        print(f"{'='*60}\n")
        
        return jsonify(response)
        
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"\n{'='*60}")
    print("MEETING SUMMARIZER API")
    print(f"{'='*60}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    print(f"Endpoint: POST /analyze")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
