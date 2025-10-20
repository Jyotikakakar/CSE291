import json
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from agent import MeetingAgent


def run_evaluation():
    
    if not os.path.exists("data/metadata.json"):
        print("No data found. Run load_data.py")
        return
    
    with open("data/metadata.json", 'r') as f:
        metadata = json.load(f)
    
    transcripts = metadata.get("transcripts", [])
    print(f"Found {len(transcripts)} transcripts")
    print()
    
    agent = MeetingAgent()
    
    results = []
    
    for i, transcript_info in enumerate(transcripts, 1):
        transcript_id = transcript_info['id']
        transcript_file = transcript_info['file']
        
        print(f"[{i}/{len(transcripts)}] Evaluating {transcript_id}...")
        
        try:
            with open(transcript_file, 'r') as f:
                transcript = f.read()
            
            result = agent.summarize(transcript)
            
            if result['success']:
                summary = result['summary']
                
                eval_result = {
                    'id': transcript_id,
                    'success': True,
                    'latency_ms': result['latency_ms'],
                    'decisions_count': len(summary.get('decisions', [])),
                    'action_items_count': len(summary.get('action_items', [])),
                    'risks_count': len(summary.get('risks', [])),
                    'has_tldr': bool(summary.get('tldr')),
                    'summary': summary
                }
                
                print(f"Success - {result['latency_ms']:.0f}ms")
                print(f"    Decisions: {eval_result['decisions_count']}, Actions: {eval_result['action_items_count']}, Risks: {eval_result['risks_count']}")
            else:
                eval_result = {
                    'id': transcript_id,
                    'success': False,
                    'error': result['error']
                }
                print(f"Failed - {result['error']}")
            
            results.append(eval_result)
            
        except Exception as e:
            print(f"Exception: {str(e)}")
            results.append({
                'id': transcript_id,
                'success': False,
                'error': str(e)
            })
    
    os.makedirs("results", exist_ok=True)
    with open("results/evaluation.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print()
    print("RESULTS SUMMARY")
    print("-" * 80)
    
    successful = [r for r in results if r.get('success')]
    total = len(results)
    
    print(f"Total Requests: {total}")
    print(f"Successful: {len(successful)}")
    print(f"Success Rate: {len(successful)/total*100:.1f}%")
    print()
    
    if successful:
        latencies = [r['latency_ms'] for r in successful]
        print(f"Latency Statistics:")
        print(f"  Mean: {np.mean(latencies):.0f}ms")
        print(f"  Median: {np.median(latencies):.0f}ms")
        print(f"  P95: {np.percentile(latencies, 95):.0f}ms")
        print(f"  Min: {np.min(latencies):.0f}ms")
        print(f"  Max: {np.max(latencies):.0f}ms")
        print()
        
        with_tldr = sum(1 for r in successful if r.get('has_tldr'))
        print(f"Task Completion:")
        print(f"  With TL;DR: {with_tldr}/{len(successful)} ({with_tldr/len(successful)*100:.1f}%)")
        
        avg_decisions = np.mean([r['decisions_count'] for r in successful])
        avg_actions = np.mean([r['action_items_count'] for r in successful])
        avg_risks = np.mean([r['risks_count'] for r in successful])
        
        print(f"  Avg Decisions: {avg_decisions:.1f}")
        print(f"  Avg Action Items: {avg_actions:.1f}")
        print(f"  Avg Risks: {avg_risks:.1f}")
        print()
    
    generate_plots(results)
    
    print("Evaluation complete!")
    print(f"  Results saved to: results/evaluation.json")
    print(f"  Plots saved to: results/")


def generate_plots(results):
    successful = [r for r in results if r.get('success')]
    
    if not successful:
        print("No successful results to plot")
        return
    
    latencies = [r['latency_ms'] for r in successful]
    
    plt.figure(figsize=(10, 6))
    latencies_sorted = np.sort(latencies)
    cdf = np.arange(1, len(latencies_sorted) + 1) / len(latencies_sorted)
    
    plt.plot(latencies_sorted, cdf, linewidth=2, color='#2E86AB')
    plt.xlabel('Latency (ms)', fontsize=12)
    plt.ylabel('Cumulative Probability', fontsize=12)
    plt.title('Latency CDF - Meeting Summarizer', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    for p in [50, 95]:
        value = np.percentile(latencies_sorted, p)
        plt.axvline(value, color='red', linestyle='--', alpha=0.5)
        plt.text(value, 0.5, f'P{p}: {value:.0f}ms', rotation=90, va='center')
    
    plt.tight_layout()
    plt.savefig('results/latency_cdf.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved results/latency_cdf.png")
    plt.close()
    
    decisions = [r['decisions_count'] for r in successful]
    actions = [r['action_items_count'] for r in successful]
    risks = [r['risks_count'] for r in successful]
    
    plt.figure(figsize=(10, 6))
    categories = ['Decisions', 'Action Items', 'Risks']
    averages = [np.mean(decisions), np.mean(actions), np.mean(risks)]
    colors = ['#06A77D', '#F77F00', '#D62828']
    
    bars = plt.bar(categories, averages, color=colors, alpha=0.8)
    plt.ylabel('Average Count', fontsize=12)
    plt.title('Extracted Items per Meeting', fontsize=14, fontweight='bold')
    plt.grid(True, axis='y', alpha=0.3)
    
    for bar, value in zip(bars, averages):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.1f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('results/extraction_counts.png', dpi=300, bbox_inches='tight')
    print("Saved results/extraction_counts.png")
    plt.close()
    
    total = len(results)
    success_count = len(successful)
    failed_count = total - success_count
    
    plt.figure(figsize=(8, 8))
    plt.pie([success_count, failed_count], 
            labels=['Success', 'Failed'],
            colors=['#06A77D', '#D62828'],
            autopct='%1.1f%%',
            startangle=90)
    plt.title('Success Rate', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig('results/success_rate.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved results/success_rate.png")
    plt.close()


def print_sample_summary():
    with open("results/evaluation.json", 'r') as f:
        results = json.load(f)
    
    successful = [r for r in results if r.get('success')]
    
    if not successful:
        return
    
    sample = successful[0]
    summary = sample['summary']
    
    print()
    print(f"SAMPLE SUMMARY - {sample['id']}")
    print("-" * 80)
    print()
    print(f"TL;DR: {summary.get('tldr', 'N/A')}")
    print()
    
    decisions = summary.get('decisions', [])
    if decisions:
        print(f"DECISIONS ({len(decisions)}):")
        for i, d in enumerate(decisions[:3], 1):  # Show first 3
            print(f"  {i}. {d.get('decision', 'N/A')}")
            if d.get('owner'):
                print(f"     Owner: {d['owner']}")
    
    actions = summary.get('action_items', [])
    if actions:
        print(f"\nACTION ITEMS ({len(actions)}):")
        for i, a in enumerate(actions[:3], 1):  # Show first 3
            print(f"  {i}. {a.get('task', 'N/A')}")
            if a.get('owner'):
                print(f"     Owner: {a['owner']}")
    
    print()


if __name__ == "__main__":
    run_evaluation()
    print_sample_summary()