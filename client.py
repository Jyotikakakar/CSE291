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
    
    def summarize(
        self,
        transcript: str,
        session_id: Optional[str] = None,
        focus_areas: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Summarize a meeting transcript"""
        payload = {
            "transcript": transcript,
            "session_id": session_id or self.session_id,
            "focus_areas": focus_areas
        }
        
        response = requests.post(
            f"{self.base_url}/api/summarize",
            json=payload
        )
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
        print(f"✓ Health check passed: {health}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        sys.exit(1)
    
    # Create session
    print("\nCreating session...")
    session_id = client.create_session(metadata={"test": True})
    print(f"✓ Session created: {session_id}")
    
    # Test summarization
    print("\nTesting summarization...")
    test_transcript = """
    Alice: Let's start the Q4 planning meeting.
    Bob: I think we should focus on the mobile app.
    Alice: Good idea. Bob, can you lead this?
    Bob: Yes, I'll have a spec by Friday.
    """
    
    result = client.summarize(test_transcript)
    if result.get("success"):
        print(f"✓ Summarization successful")
        print(f"  Latency: {result.get('latency_ms', 0):.0f}ms")
        summary = result.get("summary", {})
        print(f"  Decisions: {len(summary.get('decisions', []))}")
        print(f"  Action items: {len(summary.get('action_items', []))}")
    else:
        print(f"✗ Summarization failed: {result.get('error')}")
    
    # Get session history
    print("\nGetting session history...")
    history = client.get_session_history()
    print(f"✓ Total requests in session: {history['total_requests']}")
    
    print("\n✓ All tests passed!")

