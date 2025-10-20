from datasets import load_dataset
import os
import json


def load_ami_transcripts(num_samples=20):
    print("Loading AMI dataset")
    
    try:
        dataset = load_dataset("knkarthick/AMI", split="train")
        
        print(f"Loaded dataset with {len(dataset)} meetings")
        
        os.makedirs("data/transcripts", exist_ok=True)
        
        transcripts = []
        
        for i, meeting in enumerate(dataset):
            if i >= num_samples:
                break
            
            dialogue = meeting.get('dialogue', '')
            summary = meeting.get('summary', '')
            meeting_id = meeting.get('id', f'meeting_{i}')
            
            if not dialogue:
                continue
            
            filename = f"data/transcripts/meeting_{meeting_id}.txt"
            with open(filename, 'w') as f:
                f.write(dialogue)
            
            transcripts.append({
                "id": meeting_id,
                "file": filename,
                "summary": summary,
                "length": len(dialogue.split())
            })
            
            print(f"✓ Saved meeting {meeting_id} ({len(dialogue.split())} words)")
        
        metadata_file = "data/metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                "dataset": "AMI",
                "total_samples": len(transcripts),
                "transcripts": transcripts
            }, f, indent=2)
        
        print(f"\n✓ Saved {len(transcripts)} transcripts to data/transcripts/")
        print(f"✓ Saved metadata to {metadata_file}")
        
        return transcripts
        
    except Exception as e:
        print(f"Error loading dataset: {str(e)}")
        print("\nCreating sample synthetic transcripts instead...")
    
        return create_sample_transcripts()


def create_sample_transcripts():
    
    os.makedirs("data/transcripts", exist_ok=True)
    
    samples = [
        {
            "id": "sample_001",
            "content": """Speaker A: Good morning everyone. Let's start our Q4 planning meeting.

Speaker B: Thanks. I think we should prioritize the mobile app development. We've had consistent user requests.

Speaker C: I agree. We should also focus on enterprise features like SSO.

Speaker A: Great points. Let's make mobile app our top priority. Speaker B, can you lead this project?

Speaker B: Yes, I can do that. I'll have a detailed spec ready by next Friday.

Speaker A: Perfect. Speaker C, you'll own the SSO implementation. Target completion is November 30th.

Speaker C: Got it. I'll need Speaker D's help on the backend authentication.

Speaker D: Happy to help. One concern - our current auth service is outdated. That's a risk.

Speaker A: Good catch. Speaker D, please audit the auth service this week and report back.

Speaker D: Will do.

Speaker A: Alright, to summarize: Mobile app is priority one with Speaker B leading, SSO is priority two with Speaker C leading, and Speaker D will audit our auth service. Any questions?

Speaker B: When do we want the mobile app beta ready?

Speaker A: Let's target end of December for beta launch."""
        },
        {
            "id": "sample_002",
            "content": """Speaker A: Let's do our sprint retrospective. What went well?

Speaker B: We completed all our story points. The new CI pipeline helped a lot.

Speaker C: Code quality improved. We caught several bugs before production.

Speaker A: Excellent. What could be improved?

Speaker B: Code reviews are taking too long. Some PRs sat for 3 days.

Speaker C: We should set a 24-hour review target.

Speaker A: Good idea. Speaker C, document this in our team handbook by end of week.

Speaker C: Will do.

Speaker A: Any blockers for next sprint?

Speaker B: We need API keys from the vendor. Speaker A, can you follow up?

Speaker A: Yes, I'll email them today.

Speaker C: Also, we need to upgrade our database. It's a risk for performance.

Speaker A: Good point. Speaker C, create a proposal for the database upgrade by Monday.

Speaker C: On it."""
        },
        {
            "id": "sample_003",
            "content": """Speaker A: Morning sync. Let's go around. Speaker B, you're up.

Speaker B: Working on the payment integration. Hit a blocker with webhook validation.

Speaker A: That's a risk for our timeline. Can you schedule a vendor call today?

Speaker B: Yes, doing that right after this meeting.

Speaker C: I finished the authentication module. Ready for review.

Speaker A: Great. I'll review it this afternoon. Speaker D?

Speaker D: Migrating to the new database schema. Should be done tomorrow, but I want to test thoroughly in staging first.

Speaker A: Smart. Don't rush it. Have Speaker C review your migration script.

Speaker D: Will do.

Speaker A: Keep pushing team. Let's ship this feature by Friday."""
        },
        {
            "id": "sample_004",
            "content": """Speaker A: Welcome to our roadmap planning. Let's review customer feedback.

Speaker B: We surveyed 45 enterprise customers. Top requests: SSO, analytics, mobile support.

Speaker C: 78% of enterprise customers want SSO. It's blocking deals.

Speaker A: Clear priority. SSO first. What's the effort?

Speaker D: 6 weeks with two engineers for SAML and OAuth.

Speaker A: Approved. Speaker B, you're product lead. Speaker D, technical lead.

Speaker B: I'll have the spec ready next Friday.

Speaker D: I'll need Speaker E and Speaker F on this.

Speaker A: Make it happen. What about analytics?

Speaker C: Complex feature. I recommend phased approach - basic reporting in Q4, advanced in Q1.

Speaker B: That makes sense. Ship basic first, learn, then iterate.

Speaker A: Good. Speaker C, present three options at next week's meeting.

Speaker C: Will do.

Speaker A: Mobile support?

Speaker D: Native app is expensive. Let's improve mobile web in Q4, defer native to Q1.

Speaker A: Agreed. Speaker F, estimate effort for mobile web improvements.

Speaker F: About 3 weeks. I can handle it.

Speaker A: Perfect. So Q4 priorities: SSO, basic analytics, mobile web. Any risks?

Speaker C: Team might be stretched too thin with only 4 engineers.

Speaker D: If SSO hits blockers, other projects slip.

Speaker A: Valid. Let's add 2-week buffer for SSO. Speaker B, create detailed project plan by Monday.

Speaker B: On it."""
        },
        {
            "id": "sample_005",
            "content": """Speaker A: Design review meeting. Speaker B, walk us through your proposal.

Speaker B: I designed a new navigation system. Three main improvements: clearer hierarchy, better mobile responsiveness, and faster load times.

Speaker C: I like the hierarchy. Why did you choose a sidebar over a top nav?

Speaker B: User research showed 73% prefer sidebar for complex applications. It's also better for accessibility.

Speaker D: What about mobile? Sidebar can be problematic on small screens.

Speaker B: Good point. On mobile, it collapses to a hamburger menu. I have prototypes.

Speaker A: Show us the alternatives you considered.

Speaker B: I considered three approaches: traditional top nav, sidebar, and a hybrid. Top nav limited our scalability. Hybrid was confusing in testing. Sidebar performed best.

Speaker C: What's the implementation effort?

Speaker D: About 2 weeks for front-end work. We'd need to refactor some routing.

Speaker A: Any risks?

Speaker D: Main risk is breaking existing functionality. We need comprehensive testing.

Speaker B: I've documented all edge cases. We can do phased rollout to mitigate risk.

Speaker A: Good thinking. Let's move forward. Speaker D, you own implementation. Target completion is November 15th.

Speaker D: Got it.

Speaker A: Speaker C, work with Speaker B on user testing plan.

Speaker C: Will do. I'll have a plan by Thursday."""
        }
    ]
    
    transcripts = []
    for sample in samples:
        filename = f"data/transcripts/{sample['id']}.txt"
        with open(filename, 'w') as f:
            f.write(sample['content'])
        
        transcripts.append({
            "id": sample['id'],
            "file": filename,
            "length": len(sample['content'].split())
        })
        
        print(f"Created {sample['id']}")
    
    with open("data/metadata.json", 'w') as f:
        json.dump({
            "dataset": "Synthetic",
            "total_samples": len(transcripts),
            "transcripts": transcripts
        }, f, indent=2)
    
    print(f"\nCreated {len(transcripts)} sample transcripts in data/transcripts/")
    
    return transcripts


if __name__ == "__main__":
    print("AMI DATASET LOADER")
    print("=" * 80)
    print()
    
    choice = input("Load from HuggingFace (1) or create samples (2)? [1/2]: ").strip()
    
    if choice == "1":
        transcripts = load_ami_transcripts(num_samples=20)
    else:
        transcripts = create_sample_transcripts()
    
    print("\nData loading complete!")
    print(f"  Total transcripts: {len(transcripts)}")
    print(f"  Location: data/transcripts/")
    print(f"\nRun: python evaluate.py")