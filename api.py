#!/usr/bin/env python3
"""
Flask API for Meeting Summarizer with User and Session Management
"""
import os
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify
from agent import MeetingAgent

app = Flask(__name__)

# In-memory storage for sessions (per user container)
# In production, use Redis or database
sessions = {}
agent = None

def get_or_create_agent():
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
        "user_id": os.getenv("USER_ID", "unknown")
    })

@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create a new session for a user"""
    data = request.json or {}
    user_id = os.getenv("USER_ID", "default")
    
    session_id = f"{user_id}_{int(time.time() * 1000)}"
    
    sessions[session_id] = {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "requests": [],
        "metadata": data.get("metadata", {})
    }
    
    return jsonify({
        "session_id": session_id,
        "user_id": user_id,
        "created_at": sessions[session_id]["created_at"]
    }), 201

@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session details"""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    
    session = sessions[session_id]
    return jsonify({
        "session_id": session["session_id"],
        "user_id": session["user_id"],
        "created_at": session["created_at"],
        "total_requests": len(session["requests"])
    })

@app.route('/api/summarize', methods=['POST'])
def summarize():
    """Summarize a meeting transcript"""
    data = request.json
    
    if not data or 'transcript' not in data:
        return jsonify({"error": "transcript field is required"}), 400
    
    transcript = data['transcript']
    session_id = data.get('session_id')
    focus_areas = data.get('focus_areas')
    
    # Validate session if provided
    if session_id and session_id not in sessions:
        return jsonify({"error": "Invalid session_id"}), 400
    
    try:
        agent = get_or_create_agent()
        result = agent.summarize(transcript, focus_areas)
        
        # Store request in session if session_id provided
        if session_id:
            sessions[session_id]["requests"].append({
                "timestamp": result.get("timestamp"),
                "success": result.get("success"),
                "latency_ms": result.get("latency_ms")
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/session/<session_id>/history', methods=['GET'])
def get_session_history(session_id):
    """Get session request history (for evaluation purposes)"""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    
    session = sessions[session_id]
    return jsonify({
        "session_id": session_id,
        "user_id": session["user_id"],
        "created_at": session["created_at"],
        "requests": session["requests"],
        "total_requests": len(session["requests"])
    })

@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """List all sessions for this user container"""
    user_id = os.getenv("USER_ID", "default")
    user_sessions = [
        {
            "session_id": sid,
            "created_at": s["created_at"],
            "total_requests": len(s["requests"])
        }
        for sid, s in sessions.items()
        if s["user_id"] == user_id
    ]
    
    return jsonify({
        "user_id": user_id,
        "sessions": user_sessions,
        "total_sessions": len(user_sessions)
    })

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Get agent metrics for this container"""
    agent = get_or_create_agent()
    return jsonify(agent.get_metrics())

# ==================== CALENDAR ENDPOINTS ====================

@app.route('/api/calendar/events', methods=['POST'])
def create_calendar_event():
    """Create a new calendar event"""
    data = request.json
    
    if not data or 'title' not in data or 'date' not in data:
        return jsonify({"error": "title and date fields are required"}), 400
    
    try:
        agent = get_or_create_agent()
        result = agent.add_calendar_event(
            title=data['title'],
            date=data['date'],
            time=data.get('time'),
            attendees=data.get('attendees', []),
            description=data.get('description')
        )
        
        if result.get('success'):
            return jsonify(result), 201
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/calendar/events', methods=['GET'])
def list_calendar_events():
    """Get calendar events"""
    date = request.args.get('date')
    attendee = request.args.get('attendee')
    
    try:
        agent = get_or_create_agent()
        result = agent.get_calendar_events(date=date, attendee=attendee)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/calendar/events/<event_id>', methods=['DELETE'])
def delete_calendar_event_endpoint(event_id):
    """Delete a calendar event"""
    try:
        agent = get_or_create_agent()
        result = agent.delete_calendar_event(event_id)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ==================== TASK ENDPOINTS ====================

@app.route('/api/tasks', methods=['POST'])
def create_task_endpoint():
    """Create a new task"""
    data = request.json
    
    if not data or 'title' not in data:
        return jsonify({"error": "title field is required"}), 400
    
    try:
        agent = get_or_create_agent()
        result = agent.create_task(
            title=data['title'],
            owner=data.get('owner'),
            due_date=data.get('due_date'),
            priority=data.get('priority', 'medium'),
            description=data.get('description')
        )
        
        if result.get('success'):
            return jsonify(result), 201
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/tasks', methods=['GET'])
def list_tasks_endpoint():
    """Get tasks"""
    owner = request.args.get('owner')
    status = request.args.get('status')
    priority = request.args.get('priority')
    
    try:
        agent = get_or_create_agent()
        result = agent.get_tasks(owner=owner, status=status, priority=priority)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/tasks/<task_id>', methods=['PATCH'])
def update_task_endpoint(task_id):
    """Update a task"""
    data = request.json or {}
    
    try:
        agent = get_or_create_agent()
        result = agent.update_task(task_id, **data)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/tasks/<task_id>/complete', methods=['POST'])
def complete_task_endpoint(task_id):
    """Mark a task as complete"""
    try:
        agent = get_or_create_agent()
        result = agent.mark_task_complete(task_id)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Meeting Summarizer API")
    print(f"User ID: {os.getenv('USER_ID', 'default')}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

