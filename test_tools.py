#!/usr/bin/env python3
"""
Quick test script to verify Google Calendar and Tasks integration
"""
import os
from agent import MeetingAgent

def test_agent_initialization():
    """Test that agent initializes correctly"""
    print("1. Testing agent initialization...")
    try:
        agent = MeetingAgent()
        print("   ✓ Agent initialized successfully")
        return agent
    except Exception as e:
        print(f"   ✗ Failed to initialize agent: {e}")
        return None

def test_meeting_summarization(agent):
    """Test Gemini summarization (core functionality)"""
    print("\n2. Testing meeting summarization...")
    
    transcript = """
    Alice: Let's discuss the Q3 results.
    Bob: Sales are up 15% this quarter.
    Alice: Great! Let's plan a celebration event next Friday.
    Bob: I'll send out calendar invites.
    Carol: I'll create a task to order food.
    """
    
    try:
        result = agent.summarize(transcript)
        if result.get('success'):
            print("   ✓ Summarization successful")
            print(f"   Latency: {result.get('latency_ms', 0):.0f}ms")
            summary = result.get('summary', {})
            print(f"   Decisions: {len(summary.get('decisions', []))}")
            print(f"   Action items: {len(summary.get('action_items', []))}")
            return True
        else:
            print(f"   ✗ Summarization failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"   ✗ Exception during summarization: {e}")
        return False

def test_calendar_tools(agent):
    """Test Google Calendar integration"""
    print("\n3. Testing Google Calendar tools...")
    
    # Check if credentials are configured
    if not os.path.exists(os.getenv("GOOGLE_CREDENTIALS_PATH", "tools-setup/client_secret.json")):
        print("   ⚠️  Google credentials not found - skipping Calendar tests")
        print("   To enable: Follow TOOLS_SETUP.md guide")
        return None
    
    try:
        # Test creating event
        print("   Testing create_calendar_event...")
        result = agent.add_calendar_event(
            title="Test Event",
            date="2025-10-30",
            time="10:00 AM",
            description="Test event from integration test"
        )
        
        if result.get('success'):
            event_id = result['event']['id']
            print(f"   ✓ Event created: {event_id}")
            
            # Test retrieving events
            print("   Testing get_calendar_events...")
            events = agent.get_calendar_events(date="2025-10-30")
            if events.get('success'):
                print(f"   ✓ Retrieved {events.get('count', 0)} events")
            else:
                print(f"   ✗ Failed to retrieve events: {events.get('error')}")
            
            # Test deleting event
            print("   Testing delete_calendar_event...")
            delete_result = agent.delete_calendar_event(event_id)
            if delete_result.get('success'):
                print(f"   ✓ Event deleted: {event_id}")
            else:
                print(f"   ✗ Failed to delete event: {delete_result.get('error')}")
            
            return True
        else:
            print(f"   ✗ Failed to create event: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ✗ Exception during calendar tests: {e}")
        return False

def test_task_tools(agent):
    """Test Google Tasks integration"""
    print("\n4. Testing Google Tasks tools...")
    
    # Check if credentials are configured
    if not os.path.exists(os.getenv("GOOGLE_CREDENTIALS_PATH", "tools-setup/client_secret.json")):
        print("   ⚠️  Google credentials not found - skipping Tasks tests")
        print("   To enable: Follow TOOLS_SETUP.md guide")
        return None
    
    try:
        # Test creating task
        print("   Testing create_task...")
        result = agent.create_task(
            title="Test Task",
            priority="high",
            description="Test task from integration test"
        )
        
        if result.get('success'):
            task_id = result['task']['id']
            print(f"   ✓ Task created: {task_id}")
            
            # Test retrieving tasks
            print("   Testing get_tasks...")
            tasks = agent.get_tasks()
            if tasks.get('success'):
                print(f"   ✓ Retrieved {tasks.get('count', 0)} tasks")
            else:
                print(f"   ✗ Failed to retrieve tasks: {tasks.get('error')}")
            
            # Test marking complete
            print("   Testing mark_task_complete...")
            complete_result = agent.mark_task_complete(task_id)
            if complete_result.get('success'):
                print(f"   ✓ Task marked complete: {task_id}")
            else:
                print(f"   ✗ Failed to mark complete: {complete_result.get('error')}")
            
            return True
        else:
            print(f"   ✗ Failed to create task: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ✗ Exception during task tests: {e}")
        return False

def test_metrics(agent):
    """Test metrics tracking"""
    print("\n5. Testing metrics...")
    try:
        metrics = agent.get_metrics()
        print(f"   Total requests: {metrics.get('total_requests', 0)}")
        print(f"   Avg latency: {metrics.get('avg_latency_ms', 0):.0f}ms")
        print(f"   Tool calls: {agent.metrics.get('total_tool_calls', 0)}")
        print("   ✓ Metrics retrieved successfully")
        return True
    except Exception as e:
        print(f"   ✗ Failed to get metrics: {e}")
        return False

def main():
    print("="*70)
    print("MEETING SUMMARIZER AGENT - TOOLS INTEGRATION TEST")
    print("="*70)
    
    # Initialize agent
    agent = test_agent_initialization()
    if not agent:
        print("\n❌ FAILED: Could not initialize agent")
        return
    
    # Test core functionality
    summarization_ok = test_meeting_summarization(agent)
    
    # Test tools
    calendar_ok = test_calendar_tools(agent)
    tasks_ok = test_task_tools(agent)
    
    # Test metrics
    metrics_ok = test_metrics(agent)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    results = {
        "Agent Initialization": "✓" if agent else "✗",
        "Meeting Summarization": "✓" if summarization_ok else "✗",
        "Google Calendar Tools": "✓" if calendar_ok else ("⚠️" if calendar_ok is None else "✗"),
        "Google Tasks Tools": "✓" if tasks_ok else ("⚠️" if tasks_ok is None else "✗"),
        "Metrics Tracking": "✓" if metrics_ok else "✗"
    }
    
    for test, result in results.items():
        print(f"  {result} {test}")
    
    # Overall status
    core_tests = [agent, summarization_ok, metrics_ok]
    tool_tests = [calendar_ok, tasks_ok]
    
    if all(core_tests):
        print("\n✅ CORE FUNCTIONALITY: All tests passed")
    else:
        print("\n❌ CORE FUNCTIONALITY: Some tests failed")
    
    if all(t in [True, None] for t in tool_tests):
        if all(t is True for t in tool_tests):
            print("✅ TOOL INTEGRATION: All tests passed")
        else:
            print("⚠️  TOOL INTEGRATION: Tools not configured (optional)")
    else:
        print("❌ TOOL INTEGRATION: Some tests failed")
    
    print("\n" + "="*70)
    
    # Configuration hints
    if calendar_ok is None or tasks_ok is None:
        print("\n💡 To enable Google Calendar/Tasks integration:")
        print("   1. Follow the guide in TOOLS_SETUP.md")
        print("   2. Place credentials in tools-setup/client_secret.json")
        print("   3. Run this test again")
        print("\n   Note: Tools are optional - core functionality works without them")

if __name__ == "__main__":
    main()

