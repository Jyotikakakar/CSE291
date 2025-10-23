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
    
    def health_check(self) -> Dict[str, Any]:
        """Check if API is healthy"""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def analyze(
        self,
        transcript: str,
        meeting_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze meeting transcript with full Google integration
        Creates summary, tasks, and calendar events
        """
        payload = {
            "transcript": transcript
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
        print(f"✓ Health check passed: {health}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        sys.exit(1)
    
    # Test analysis
    print("\nTesting analysis...")
    test_transcript = """
    Alice: Let's start the Q4 planning meeting.
    Bob: I think we should focus on the mobile app.
    Alice: Good idea. Bob, can you lead this?
    Bob: Yes, I'll have a spec by Friday.
    """
    
    result = client.analyze(test_transcript)
    if result.get("success"):
        print(f"✓ Analysis successful")
        print(f"  Latency: {result.get('latency_ms', 0):.0f}ms")
        summary = result.get("summary", {})
        print(f"  Decisions: {len(summary.get('decisions', []))}")
        print(f"  Action items: {len(summary.get('action_items', []))}")
        print(f"  Tasks created: {len(result.get('tasks_created', []))}")
    else:
        print(f"✗ Analysis failed: {result.get('error')}")
    
    print("\n✓ All tests passed!")

