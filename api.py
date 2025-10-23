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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Meeting Summarizer API")
    print(f"User ID: {os.getenv('USER_ID', 'default')}")
    print(f"Port: {port}")
    print(f"Debug: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

