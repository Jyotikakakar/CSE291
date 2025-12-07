#!/usr/bin/env python3
"""
Run Meeting Agent on stored transcripts.
"""
import os
import glob
from meeting_agent import MCPMeetingAgent


def run():
    """Process all meeting transcripts in data/transcripts/"""
    print("\n" + "=" * 80)
    print("MEETING AGENT - Processing Transcripts")
    print("=" * 80)
    
    # Initialize agent
    agent = MCPMeetingAgent(thread_id="meetings", enable_google=True)
    
    # Find all transcript files
    transcript_dir = "data/transcripts"
    transcript_files = sorted(glob.glob(os.path.join(transcript_dir, "*.txt")))
    
    if not transcript_files:
        print(f"\n⚠ No transcript files found in {transcript_dir}/")
        return
    
    print(f"\nFound {len(transcript_files)} transcript(s)")
    
    for i, file_path in enumerate(transcript_files, 1):
        print(f"\n{'='*80}")
        print(f"MEETING {i}: {os.path.basename(file_path)}")
        print(f"{'='*80}")
        
        with open(file_path, 'r') as f:
            transcript = f.read()
        
        print(f"Transcript length: {len(transcript.split())} words")
        
        # Summarize with context (use context only after first meeting)
        result = agent.summarize(
            transcript,
            use_context=(i > 1),
            sync_google=True,
            create_followup=True
        )
        
        if result["success"]:
            summary = result['summary']
            print(f"\n✓ Summarized in {result['latency_ms']:.0f}ms")
            print(f"  Meeting ID: {result['meeting_id']}")
            
            print(f"\nTL;DR:")
            print(f"  {summary['tldr']}")
            
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
            
            if summary.get('risks'):
                print(f"\nRisks ({len(summary['risks'])}):")
                for risk in summary['risks']:
                    print(f"  - {risk}")
        else:
            print(f"\n✗ Error: {result['error']}")
    
    # Summary
    print(f"\n{'='*80}")
    print("COMPLETE")
    print(f"{'='*80}")
    print(f"Processed: {agent.metrics['total_requests']} meetings")
    if agent.metrics['total_requests'] > 0:
        avg_latency = agent.metrics['total_latency_ms'] / agent.metrics['total_requests']
        print(f"Avg latency: {avg_latency:.0f}ms")
    
    agent.cleanup()


if __name__ == "__main__":
    run()

