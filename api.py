#!/usr/bin/env python3
"""
Simple Flask API for Meeting Summarizer with Google Calendar and Tasks Integration
Single endpoint: /analyze - Takes transcript, creates summary, tasks, and calendar events
"""
import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from agent import MeetingAgent

app = Flask(__name__)

# Initialize agent
agent = None

# Session storage - in-memory for now
# Structure: {session_id: {metadata: {}, requests: [], created_at: timestamp, user_id: str}}
sessions = {}

def get_agent():
    """Get or create the MeetingAgent instance"""
    global agent
    if agent is None:
        agent = MeetingAgent()
    return agent

def get_user_id():
    """Get user ID from environment variable"""
    return os.getenv('USER_ID', 'default_user')

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Meeting Summarizer with Google Integration",
        "user_id": get_user_id()
    })

@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create a new session"""
    data = request.json or {}
    metadata = data.get('metadata', {})
    
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        'metadata': metadata,
        'requests': [],
        'created_at': datetime.now().isoformat(),
        'user_id': get_user_id()
    }
    
    return jsonify({
        'session_id': session_id,
        'created_at': sessions[session_id]['created_at'],
        'user_id': get_user_id()
    })

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session details"""
    if session_id not in sessions:
        return jsonify({
            "success": False,
            "error": "Session not found"
        }), 404
    
    session = sessions[session_id]
    return jsonify({
        'session_id': session_id,
        'metadata': session['metadata'],
        'created_at': session['created_at'],
        'total_requests': len(session['requests']),
        'user_id': session['user_id']
    })

@app.route('/api/session/<session_id>/history', methods=['GET'])
def get_session_history(session_id):
    """Get session request history"""
    if session_id not in sessions:
        return jsonify({
            "success": False,
            "error": "Session not found"
        }), 404
    
    session = sessions[session_id]
    return jsonify({
        'session_id': session_id,
        'total_requests': len(session['requests']),
        'requests': session['requests']
    })

@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """List all sessions for this user"""
    user_id = get_user_id()
    user_sessions = [
        {
            'session_id': sid,
            'metadata': data['metadata'],
            'created_at': data['created_at'],
            'total_requests': len(data['requests'])
        }
        for sid, data in sessions.items()
        if data['user_id'] == user_id
    ]
    
    return jsonify({
        'user_id': user_id,
        'total_sessions': len(user_sessions),
        'sessions': user_sessions
    })

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Get agent metrics"""
    agent = get_agent()
    metrics = agent.get_metrics()
    
    user_id = get_user_id()
    user_session_count = sum(1 for s in sessions.values() if s['user_id'] == user_id)
    
    return jsonify({
        'user_id': user_id,
        'total_requests': metrics['total_requests'],
        'avg_latency_ms': metrics['avg_latency_ms'],
        'total_sessions': user_session_count
    })

@app.route('/analyze', methods=['POST'])
def analyze_meeting():
    """
    Analyze meeting transcript and automatically create tasks and calendar events
    
    Request body:
    {
        "transcript": "Meeting transcript text...",
        "session_id": "uuid",  // Optional - for session tracking
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
        "session_id": "uuid",
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
    session_id = data.get('session_id')
    meeting_info = data.get('meeting_info', {})
    
    # Validate session if provided
    if session_id and session_id not in sessions:
        return jsonify({
            "success": False,
            "error": "Invalid session_id"
        }), 400
    
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
            "session_id": session_id,
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
        
        # Log request to session history if session_id provided
        if session_id:
            request_record = {
                'timestamp': datetime.now().isoformat(),
                'transcript_length': len(transcript.split()),
                'success': True,
                'latency_ms': response['latency_ms'],
                'decisions_count': len(summary.get('decisions', [])),
                'action_items_count': len(summary.get('action_items', [])),
                'risks_count': len(summary.get('risks', [])),
                'tasks_created_count': len(response['tasks_created']),
                'calendar_event_created': response['calendar_event'] is not None,
                'errors_count': len(response['errors'])
            }
            sessions[session_id]['requests'].append(request_record)
        
        return jsonify(response)
        
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        
        # Log error to session history if session_id provided
        if session_id:
            request_record = {
                'timestamp': datetime.now().isoformat(),
                'transcript_length': len(transcript.split()) if transcript else 0,
                'success': False,
                'error': str(e)
            }
            sessions[session_id]['requests'].append(request_record)
        
        return jsonify({
            "success": False,
            "session_id": session_id,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    user_id = get_user_id()
    
    print(f"\n{'='*60}")
    print("MEETING SUMMARIZER API WITH SESSION MANAGEMENT")
    print(f"{'='*60}")
    print(f"Port: {port}")
    print(f"User ID: {user_id}")
    print(f"Debug: {debug}")
    print(f"\nEndpoints:")
    print(f"  GET  /health")
    print(f"  POST /api/session/create")
    print(f"  GET  /api/session/<session_id>")
    print(f"  GET  /api/session/<session_id>/history")
    print(f"  GET  /api/sessions")
    print(f"  GET  /api/metrics")
    print(f"  POST /analyze (with optional session_id)")
    print(f"{'='*60}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
