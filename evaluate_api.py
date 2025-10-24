#!/usr/bin/env python3
"""
Evaluate the Meeting Summarizer API with multiple users and sessions
This simulates the benchmark evaluation with user/session management
"""
import json
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from client import MeetingSummarizerClient
from typing import Dict, List, Any

def load_transcripts() -> List[Dict[str, Any]]:
    """Load transcripts from metadata"""
    if not os.path.exists("data/metadata.json"):
        print("Error: No data found. Run: python run.py first")
        sys.exit(1)
    
    with open("data/metadata.json", 'r') as f:
        metadata = json.load(f)
    
    transcripts = []
    for t in metadata.get("transcripts", []):
        with open(t['file'], 'r') as f:
            content = f.read()
        transcripts.append({
            "id": t['id'],
            "content": content,
            "length": t.get('length', len(content.split()))
        })
    
    return transcripts

def assign_users_to_transcripts(transcripts: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Assign transcripts to users based on context length
    Users with different workloads (short, medium, long context)
    """
    # Sort by length
    sorted_transcripts = sorted(transcripts, key=lambda x: x['length'])
    
    users = {
        "user_1": [],  # Short context user
        "user_2": [],  # Medium context user  
        "user_3": [],  # Long context user
        "user_4": [],  # Mixed context user
    }
    
    # Distribute transcripts
    total = len(sorted_transcripts)
    
    # User 1: Shortest transcripts (first 25%)
    users["user_1"] = sorted_transcripts[:total//4]
    
    # User 2: Medium short (25-50%)
    users["user_2"] = sorted_transcripts[total//4:total//2]
    
    # User 3: Long context (50-75%)
    users["user_3"] = sorted_transcripts[total//2:(3*total)//4]
    
    # User 4: Mixed (remaining)
    users["user_4"] = sorted_transcripts[(3*total)//4:]
    
    return users

def evaluate_user(
    user_id: str,
    transcripts: List[Dict],
    base_url: str
) -> Dict[str, Any]:
    """
    Evaluate a single user with multiple sessions
    """
    print(f"\n{'='*80}")
    print(f"Evaluating {user_id}")
    print(f"{'='*80}")
    print(f"Transcripts: {len(transcripts)}")
    
    client = MeetingSummarizerClient(base_url)
    
    # Check health
    try:
        health = client.health_check()
        print(f"✓ Connected to {user_id} container: {health['user_id']}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        return {"error": str(e), "results": []}
    
    # Create 2 sessions per user to test session management
    num_sessions = min(2, len(transcripts))
    session_results = []
    
    for session_idx in range(num_sessions):
        print(f"\n--- Session {session_idx + 1} ---")
        
        # Create new session
        session_id = client.create_session(
            metadata={"session_number": session_idx + 1}
        )
        print(f"Created session: {session_id}")
        
        # Assign transcripts to this session
        session_transcripts = transcripts[session_idx::num_sessions]
        
        session_requests = []
        for transcript_info in session_transcripts:
            transcript_id = transcript_info['id']
            transcript = transcript_info['content']
            
            print(f"  Processing {transcript_id} ({transcript_info['length']} words)...", end=' ')
            
            try:
                result = client.summarize(transcript, session_id=session_id)
                
                if result.get('success'):
                    summary = result.get('summary', {})
                    eval_result = {
                        'id': transcript_id,
                        'user_id': user_id,
                        'session_id': session_id,
                        'success': True,
                        'latency_ms': result.get('latency_ms', 0),
                        'context_length': transcript_info['length'],
                        'decisions_count': len(summary.get('decisions', [])),
                        'action_items_count': len(summary.get('action_items', [])),
                        'risks_count': len(summary.get('risks', [])),
                    }
                    print(f"{result.get('latency_ms', 0):.0f}ms ✓")
                else:
                    eval_result = {
                        'id': transcript_id,
                        'user_id': user_id,
                        'session_id': session_id,
                        'success': False,
                        'error': result.get('error'),
                        'context_length': transcript_info['length']
                    }
                    print(f"✗ {result.get('error')}")
                
                session_requests.append(eval_result)
                
            except Exception as e:
                print(f"✗ {str(e)}")
                session_requests.append({
                    'id': transcript_id,
                    'user_id': user_id,
                    'session_id': session_id,
                    'success': False,
                    'error': str(e),
                    'context_length': transcript_info['length']
                })
        
        session_results.append({
            'session_id': session_id,
            'requests': session_requests
        })
    
    # Get final metrics
    try:
        metrics = client.get_metrics()
        print(f"\n{user_id} Metrics:")
        print(f"  Total requests: {metrics.get('total_requests', 0)}")
        print(f"  Avg latency: {metrics.get('avg_latency_ms', 0):.0f}ms")
    except Exception as e:
        print(f"Failed to get metrics: {e}")
        metrics = {}
    
    # Flatten all results
    all_results = []
    for session in session_results:
        all_results.extend(session['requests'])
    
    return {
        'user_id': user_id,
        'sessions': session_results,
        'results': all_results,
        'metrics': metrics
    }

def generate_evaluation_plots(all_results: List[Dict]):
    """Generate evaluation plots"""
    successful = [r for r in all_results if r.get('success')]
    
    if not successful:
        print("No successful results to plot")
        return
    
    os.makedirs("results", exist_ok=True)
    
    # 1. Latency by context length
    plt.figure(figsize=(10, 6))
    context_lengths = [r['context_length'] for r in successful]
    latencies = [r['latency_ms'] for r in successful]
    users = [r['user_id'] for r in successful]
    
    # Color by user
    user_colors = {
        'user_1': '#2E86AB',
        'user_2': '#06A77D', 
        'user_3': '#F77F00',
        'user_4': '#D62828'
    }
    colors = [user_colors.get(u, 'gray') for u in users]
    
    plt.scatter(context_lengths, latencies, c=colors, alpha=0.6, s=100)
    plt.xlabel('Context Length (words)', fontsize=12)
    plt.ylabel('Latency (ms)', fontsize=12)
    plt.title('Latency vs Context Length by User', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=color, label=user) 
                      for user, color in user_colors.items()]
    plt.legend(handles=legend_elements, loc='upper left')
    
    plt.tight_layout()
    plt.savefig('results/latency_vs_context.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved results/latency_vs_context.png")
    plt.close()
    
    # 2. Success rate by user
    plt.figure(figsize=(10, 6))
    user_stats = {}
    for user_id in ['user_1', 'user_2', 'user_3', 'user_4']:
        user_results = [r for r in all_results if r.get('user_id') == user_id]
        if user_results:
            success_rate = sum(1 for r in user_results if r.get('success')) / len(user_results) * 100
            user_stats[user_id] = success_rate
    
    users_list = list(user_stats.keys())
    success_rates = list(user_stats.values())
    colors_list = [user_colors[u] for u in users_list]
    
    bars = plt.bar(users_list, success_rates, color=colors_list, alpha=0.8)
    plt.ylabel('Success Rate (%)', fontsize=12)
    plt.xlabel('User', fontsize=12)
    plt.title('Success Rate by User', fontsize=14, fontweight='bold')
    plt.ylim(0, 105)
    plt.grid(True, axis='y', alpha=0.3)
    
    for bar, value in zip(bars, success_rates):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.1f}%',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('results/success_rate_by_user.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved results/success_rate_by_user.png")
    plt.close()
    
    # 3. Latency CDF by user
    plt.figure(figsize=(10, 6))
    for user_id in ['user_1', 'user_2', 'user_3', 'user_4']:
        user_latencies = [r['latency_ms'] for r in successful if r.get('user_id') == user_id]
        if user_latencies:
            sorted_latencies = np.sort(user_latencies)
            cdf = np.arange(1, len(sorted_latencies) + 1) / len(sorted_latencies)
            plt.plot(sorted_latencies, cdf, linewidth=2, 
                    label=user_id, color=user_colors[user_id])
    
    plt.xlabel('Latency (ms)', fontsize=12)
    plt.ylabel('Cumulative Probability', fontsize=12)
    plt.title('Latency CDF by User', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('results/latency_cdf_by_user.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved results/latency_cdf_by_user.png")
    plt.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python evaluate_api.py <base_url_pattern>")
        print("Example: python evaluate_api.py http://localhost:500")
        print("  This will connect to user_1 at port 5001, user_2 at 5002, etc.")
        sys.exit(1)
    
    base_url_pattern = sys.argv[1].rstrip('/')
    
    print("="*80)
    print("MEETING SUMMARIZER API EVALUATION")
    print("Multi-User, Multi-Session Benchmark")
    print("="*80)
    
    # Load transcripts
    print("\nLoading transcripts...")
    transcripts = load_transcripts()
    print(f"✓ Loaded {len(transcripts)} transcripts")
    
    # Assign to users
    print("\nAssigning transcripts to users...")
    user_assignments = assign_users_to_transcripts(transcripts)
    for user_id, user_transcripts in user_assignments.items():
        if user_transcripts:
            lengths = [t['length'] for t in user_transcripts]
            print(f"  {user_id}: {len(user_transcripts)} transcripts "
                  f"(avg {np.mean(lengths):.0f} words, "
                  f"range {min(lengths)}-{max(lengths)} words)")
    
    # Evaluate each user
    all_user_results = []
    all_results = []
    
    for idx, (user_id, user_transcripts) in enumerate(user_assignments.items(), 1):
        if not user_transcripts:
            continue
        
        # Each user has their own container on different port
        user_port = 5000 + idx
        user_url = f"{base_url_pattern}{user_port}"
        
        user_result = evaluate_user(user_id, user_transcripts, user_url)
        all_user_results.append(user_result)
        all_results.extend(user_result['results'])
    
    # Save results
    print("\n" + "="*80)
    print("SAVING RESULTS")
    print("="*80)
    
    os.makedirs("results", exist_ok=True)
    
    with open("results/api_evaluation.json", 'w') as f:
        json.dump({
            'user_results': all_user_results,
            'all_results': all_results
        }, f, indent=2)
    print("  ✓ Saved results/api_evaluation.json")
    
    # Generate summary statistics
    successful = [r for r in all_results if r.get('success')]
    total = len(all_results)
    
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(f"Total requests: {total}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {total - len(successful)}")
    print(f"Success rate: {len(successful)/total*100:.1f}%")
    
    if successful:
        latencies = [r['latency_ms'] for r in successful]
        print(f"\nLatency statistics:")
        print(f"  Mean: {np.mean(latencies):.0f}ms")
        print(f"  Median: {np.median(latencies):.0f}ms")
        print(f"  P95: {np.percentile(latencies, 95):.0f}ms")
        print(f"  Min: {np.min(latencies):.0f}ms")
        print(f"  Max: {np.max(latencies):.0f}ms")
        
        context_lengths = [r['context_length'] for r in successful]
        print(f"\nContext length statistics:")
        print(f"  Mean: {np.mean(context_lengths):.0f} words")
        print(f"  Median: {np.median(context_lengths):.0f} words")
        print(f"  Min: {np.min(context_lengths):.0f} words")
        print(f"  Max: {np.max(context_lengths):.0f} words")
    
    # Generate plots
    print("\n" + "="*80)
    print("GENERATING PLOTS")
    print("="*80)
    generate_evaluation_plots(all_results)
    
    print("\n" + "="*80)
    print("✓ EVALUATION COMPLETE!")
    print("="*80)
    print("\nResults saved to:")
    print("  - results/api_evaluation.json")
    print("  - results/latency_vs_context.png")
    print("  - results/success_rate_by_user.png")
    print("  - results/latency_cdf_by_user.png")

if __name__ == "__main__":
    main()

