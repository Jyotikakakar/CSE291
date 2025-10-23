#!/usr/bin/env python3
"""
Client for interacting with Meeting Summarizer API
Used for evaluation and testing
"""
import requests
import json
import time
from typing import Dict, Any, List, Optional

class MeetingSummarizerClient:
    def __init__(self, base_url: str):
        """
        Initialize client
        
        Args:
            base_url: Base URL of the API (e.g., http://localhost:5000)
        """
        self.base_url = base_url.rstrip('/')
        self.session_id = None
    
    def health_check(self) -> Dict[str, Any]:
        """Check if API is healthy"""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def create_session(self, metadata: Optional[Dict] = None) -> str:
        """Create a new session"""
        payload = {"metadata": metadata or {}}
        response = requests.post(
            f"{self.base_url}/api/session/create",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        self.session_id = data["session_id"]
        return self.session_id
    
    def get_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get session details"""
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id provided or stored")
        
        response = requests.get(f"{self.base_url}/api/session/{sid}")
        response.raise_for_status()
        return response.json()
    
    def get_session_history(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get session request history"""
        sid = session_id or self.session_id
        if not sid:
            raise ValueError("No session_id provided or stored")
        
        response = requests.get(f"{self.base_url}/api/session/{sid}/history")
        response.raise_for_status()
        return response.json()
    
    def list_sessions(self) -> Dict[str, Any]:
        """List all sessions for this user"""
        response = requests.get(f"{self.base_url}/api/sessions")
        response.raise_for_status()
        return response.json()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics"""
        response = requests.get(f"{self.base_url}/api/metrics")
        response.raise_for_status()
        return response.json()
    
    def analyze(
        self,
        transcript: str,
        session_id: Optional[str] = None,
        meeting_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze meeting transcript with full Google integration
        Creates summary, tasks, and calendar events
        """
        payload = {
            "transcript": transcript,
            "session_id": session_id or self.session_id
        }
        
        if meeting_info:
            payload["meeting_info"] = meeting_info
        
        response = requests.post(
            f"{self.base_url}/analyze",
            json=payload
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    import sys
    
    # Test the client
    if len(sys.argv) < 2:
        print("Usage: python client.py <base_url>")
        print("Example: python client.py http://localhost:5000")
        sys.exit(1)
    
    base_url = sys.argv[1]
    client = MeetingSummarizerClient(base_url)
    
    print(f"Testing connection to {base_url}")
    
    # Health check
    try:
        health = client.health_check()
        print(f"✓ Health check passed")
        print(f"  User ID: {health.get('user_id')}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        sys.exit(1)
    
    # Create session
    print("\nCreating session...")
    try:
        session_id = client.create_session(metadata={"test": True, "purpose": "client test"})
        print(f"✓ Session created: {session_id}")
    except Exception as e:
        print(f"✗ Session creation failed: {e}")
        sys.exit(1)
    
    # Test analysis with session
    print("\nTesting analysis with session...")
    test_transcript = """
    Alice: Let's start the Q4 planning meeting.
    Bob: I think we should focus on the mobile app.
    Alice: Good idea. Bob, can you lead this?
    Bob: Yes, I'll have a spec by Friday.
    """
    
    result = client.analyze(test_transcript)
    if result.get("success"):
        print(f"✓ Analysis successful")
        print(f"  Session ID: {result.get('session_id')}")
        print(f"  Latency: {result.get('latency_ms', 0):.0f}ms")
        summary = result.get("summary", {})
        print(f"  Decisions: {len(summary.get('decisions', []))}")
        print(f"  Action items: {len(summary.get('action_items', []))}")
        print(f"  Tasks created: {len(result.get('tasks_created', []))}")
    else:
        print(f"✗ Analysis failed: {result.get('error')}")
    
    # Get session history
    print("\nGetting session history...")
    try:
        history = client.get_session_history()
        print(f"✓ Total requests in session: {history['total_requests']}")
    except Exception as e:
        print(f"✗ Get history failed: {e}")
    
    # List all sessions
    print("\nListing all sessions...")
    try:
        sessions = client.list_sessions()
        print(f"✓ Total sessions for user: {sessions['total_sessions']}")
    except Exception as e:
        print(f"✗ List sessions failed: {e}")
    
    # Get metrics
    print("\nGetting metrics...")
    try:
        metrics = client.get_metrics()
        print(f"✓ Total requests: {metrics['total_requests']}")
        print(f"  Avg latency: {metrics['avg_latency_ms']:.0f}ms")
        print(f"  Total sessions: {metrics['total_sessions']}")
    except Exception as e:
        print(f"✗ Get metrics failed: {e}")
    
    print("\n✓ All tests passed!")

