import os
import json
import time
import requests
from typing import Dict, Any, List
from datetime import datetime

# Load API key
from dotenv import load_dotenv
load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


class MeetingAgent:
    def __init__(self):
        self.host = OLLAMA_HOST
        self.model = OLLAMA_MODEL
        self.metrics = {
            "total_requests": 0,
            "total_latency_ms": 0,
            "total_tool_calls": 0
        }
        
        self._check_ollama()
    
    def _check_ollama(self):
        try:
            response = requests.get(f"{self.host}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                if not any(self.model in name for name in model_names):
                    print(f"Model {self.model} not found")
                    print(f"   Available models: {', '.join(model_names)}")
                    print(f"\n   To install: ollama pull {self.model}")
        except requests.exceptions.ConnectionError:
            print("Ollama is not running!")
            raise
    
    def _call_ollama(self, prompt: str) -> str:
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        return response.json()['response']
    
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
            response_text = self._call_ollama(prompt)
            
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
    
    print("Testing Ollama agent")
    result = agent.summarize(sample_transcript)
    
    if result["success"]:
        print("MEETING SUMMARY")
        print("=" * 80)
        print(json.dumps(result["summary"], indent=2))
        print(f"\nProcessing time: {result['latency_ms']:.0f}ms")
    else:
        print(f"Error: {result['error']}")