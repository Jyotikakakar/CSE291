#!/usr/bin/env python3
"""
Run Meeting Agent on stored transcripts.

Usage:
  python run.py              # Extract with Gemini + save to JSON + sync to Google
  python run.py --extract    # Extract with Gemini + save to JSON (no Google sync)
  python run.py --sync       # Sync from saved JSON to Google (no Gemini needed)
                             # Automatically deletes previous sync items first
"""
import os
import sys
import glob
import json
from meeting_agent import MCPMeetingAgent

EXTRACTED_DATA_FILE = "data/extracted_data.json"
SYNC_STATE_FILE = "data/sync_state.json"


def load_extracted_data():
    """Load previously extracted data from JSON file."""
    if os.path.exists(EXTRACTED_DATA_FILE):
        with open(EXTRACTED_DATA_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_extracted_data(data):
    """Save extracted data to JSON file."""
    os.makedirs(os.path.dirname(EXTRACTED_DATA_FILE), exist_ok=True)
    with open(EXTRACTED_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n✓ Saved extracted data to {EXTRACTED_DATA_FILE}")


def load_sync_state():
    """Load sync state (IDs of previously created items)."""
    if os.path.exists(SYNC_STATE_FILE):
        with open(SYNC_STATE_FILE, 'r') as f:
            return json.load(f)
    return {"task_ids": [], "event_ids": []}


def save_sync_state(state):
    """Save sync state to JSON file."""
    os.makedirs(os.path.dirname(SYNC_STATE_FILE), exist_ok=True)
    with open(SYNC_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def print_summary(summary, filename):
    """Print summary details."""
    print(f"\nTL;DR:")
    print(f"  {summary.get('tldr', 'N/A')}")
    
    if summary.get('decisions'):
        print(f"\nDecisions ({len(summary['decisions'])}):")
        for d in summary['decisions']:
            owner = d.get('owner', 'N/A')
            print(f"  - {d.get('decision')} (Owner: {owner})")
    
    if summary.get('action_items'):
        print(f"\nAction Items ({len(summary['action_items'])}):")
        for a in summary['action_items']:
            owner = a.get('owner', 'N/A')
            due = a.get('due_date', 'N/A')
            print(f"  - {a.get('task')} (Owner: {owner}, Due: {due})")
    
    if summary.get('meetings_to_schedule'):
        print(f"\n📅 Meetings Scheduled ({len(summary['meetings_to_schedule'])}):")
        for m in summary['meetings_to_schedule']:
            title = m.get('title', 'Meeting')
            date = m.get('date', 'TBD')
            time = m.get('time', 'TBD')
            duration = m.get('duration_minutes', 60)
            print(f"  - {title}: {date} at {time} ({duration} min)")
    
    if summary.get('risks'):
        print(f"\nRisks ({len(summary['risks'])}):")
        for risk in summary['risks']:
            print(f"  - {risk}")


def discover_users(transcript_dir="data/transcripts"):
    """Discover user folders in transcript directory."""
    users = [d for d in os.listdir(transcript_dir) 
             if os.path.isdir(os.path.join(transcript_dir, d))]
    return sorted(users)


def run_extract(sync_to_google=True, user_filter=None):
    """Extract data from transcripts using Gemini and save to JSON."""
    print("\n" + "=" * 80)
    print("MEETING AGENT - Extract Mode (Cross-User Context)")
    print("=" * 80)
    
    transcript_dir = "data/transcripts"
    users = discover_users(transcript_dir)
    
    if not users:
        print(f"\n⚠ No user folders found in {transcript_dir}/")
        return
    
    if user_filter:
        users = [u for u in users if u == user_filter]
        if not users:
            print(f"\n⚠ User '{user_filter}' not found")
            return
    
    print(f"\nFound {len(users)} user(s): {users}")
    
    extracted_data = load_extracted_data()
    total_meetings = 0
    
    for user in users:
        print(f"\n{'='*80}")
        print(f"PROCESSING USER: {user}")
        print(f"{'='*80}")
        
        agent = MCPMeetingAgent(
            thread_id=user,
            global_thread_id="global",
            enable_google=sync_to_google
        )
        
        user_path = os.path.join(transcript_dir, user)
        transcript_files = sorted(glob.glob(os.path.join(user_path, "*.txt")))
        
        if not transcript_files:
            print(f"  No transcripts found for {user}")
            agent.cleanup()
            continue
        
        for i, file_path in enumerate(transcript_files, 1):
            filename = os.path.basename(file_path)
            print(f"\n  Meeting {i}: {filename}")
            
            with open(file_path, 'r') as f:
                transcript = f.read()
            
            result = agent.summarize(
                transcript,
                use_context=True,
                sync_google=sync_to_google,
                create_followup=False
            )
            
            if result["success"]:
                summary = result['summary']
                print(f"  ✓ Summarized in {result['latency_ms']:.0f}ms")
                extracted_data[f"{user}/{filename}"] = summary
                total_meetings += 1
            else:
                print(f"  ✗ Error: {result['error']}")
        
        agent.cleanup()
    
    save_extracted_data(extracted_data)
    
    print(f"\n{'='*80}")
    print("COMPLETE")
    print(f"{'='*80}")
    print(f"Users processed: {len(users)}")
    print(f"Total meetings: {total_meetings}")


def delete_previous_sync(agent):
    """Delete all items from previous sync."""
    sync_state = load_sync_state()
    
    task_ids = sync_state.get("task_ids", [])
    event_ids = sync_state.get("event_ids", [])
    
    if not task_ids and not event_ids:
        print("No previous sync to clean up.")
        return
    
    print(f"\n🗑️  Cleaning up previous sync...")
    print(f"   Found {len(task_ids)} tasks and {len(event_ids)} calendar events to delete")
    
    deleted_tasks = 0
    deleted_events = 0
    
    # Delete tasks
    if task_ids and agent.google:
        deleted_tasks = agent.google.delete_multiple_tasks(task_ids)
        print(f"   ✓ Deleted {deleted_tasks}/{len(task_ids)} tasks")
    
    # Delete calendar events
    if event_ids and agent.google:
        deleted_events = agent.google.delete_multiple_events(event_ids)
        print(f"   ✓ Deleted {deleted_events}/{len(event_ids)} calendar events")
    
    # Clear sync state
    save_sync_state({"task_ids": [], "event_ids": []})
    print(f"   ✓ Cleared sync state")
    
    return deleted_tasks + deleted_events


def run_sync():
    """Sync from saved JSON to Google Calendar and Tasks (no Gemini needed)."""
    print("\n" + "=" * 80)
    print("MEETING AGENT - Sync Mode (No Gemini API)")
    print("=" * 80)
    
    # Load extracted data
    extracted_data = load_extracted_data()
    
    if not extracted_data:
        print(f"\n⚠ No extracted data found at {EXTRACTED_DATA_FILE}")
        print("Run 'python run.py --extract' first to extract data from transcripts.")
        return
    
    print(f"\nLoaded {len(extracted_data)} meeting(s) from {EXTRACTED_DATA_FILE}")
    
    # Initialize agent with Google only (no Gemini needed for sync)
    agent = MCPMeetingAgent(thread_id="meetings_sync", enable_google=True, require_gemini=False)
    
    # Delete previous sync items first
    delete_previous_sync(agent)
    
    # Track all created IDs
    all_task_ids = []
    all_event_ids = []
    total_synced = 0
    
    for filename, summary in extracted_data.items():
        print(f"\n{'='*80}")
        print(f"SYNCING: {filename}")
        print(f"{'='*80}")
        
        print_summary(summary, filename)
        
        # Sync to Google
        if agent.google:
            result = agent.sync_from_extracted(summary)
            synced = result["synced_count"]
            total_synced += synced
            
            # Collect IDs for tracking
            all_task_ids.extend(result["task_ids"])
            all_event_ids.extend(result["event_ids"])
            
            print(f"\n✓ Synced {synced} items to Google")
        else:
            print("\n⚠ Google integration not available")
    
    # Save sync state for future cleanup
    save_sync_state({
        "task_ids": all_task_ids,
        "event_ids": all_event_ids
    })
    
    # Summary
    print(f"\n{'='*80}")
    print("SYNC COMPLETE")
    print(f"{'='*80}")
    print(f"Meetings processed: {len(extracted_data)}")
    print(f"Total items synced: {total_synced}")
    print(f"  - Tasks: {len(all_task_ids)}")
    print(f"  - Calendar Events: {len(all_event_ids)}")
    print(f"\n✓ Sync state saved to {SYNC_STATE_FILE}")
    print("  (Run --sync again to replace these items)")
    
    agent.cleanup()


def main():
    """Main entry point with argument handling."""
    user_filter = None
    
    # Parse --user argument
    if '--user' in sys.argv:
        idx = sys.argv.index('--user')
        if idx + 1 < len(sys.argv):
            user_filter = sys.argv[idx + 1]
    
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == '--sync':
            run_sync()
        elif arg == '--extract':
            run_extract(sync_to_google=False, user_filter=user_filter)
        elif arg == '--user':
            run_extract(sync_to_google=True, user_filter=user_filter)
        elif arg == '--help' or arg == '-h':
            print(__doc__)
        else:
            print(f"Unknown argument: {arg}")
            print(__doc__)
    else:
        # Default: extract + sync all users
        run_extract(sync_to_google=True, user_filter=user_filter)


if __name__ == "__main__":
    main()
